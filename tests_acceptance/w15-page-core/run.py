"""Official sandboxed Chrome gate: 912d96a page + 8d10844 original core success preview.

Does not modify the existing 503 unavailable-core gate. Screenshots alone do not
prove the core ran; the live POST 200, coreVersion, and on-page result panel do.
"""
from __future__ import annotations

import argparse
from base64 import b64encode
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import select
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

HERE = Path(__file__).resolve().parent
PINS = json.loads((HERE / "pins.json").read_text())
CASE = "SYN-W15-A"
TITLE = "Synthetic source alpha"
HEADERS = {"X-MCIS-Role": "LeadInvestigator", "X-MCIS-Operator": "Synthetic%20W15"}
SDK = "8.0.428"
MODEL = {
    "hazard": "合成危险源 🛳",
    "topEvent": {"id": "TOP", "label": "假设失控事件"},
    "nodes": [
        {"id": "T", "label": "合成 T", "kind": "Threat", "barrierId": None},
        {"id": "P", "label": "合成 P", "kind": "PreventionBarrier", "barrierId": None},
        {"id": "M", "label": "合成 M", "kind": "MitigationBarrier", "barrierId": None},
        {"id": "C", "label": "合成 C", "kind": "Consequence", "barrierId": None},
    ],
    "edges": [{"fromId": a, "toId": b} for a, b in (("T", "P"), ("P", "TOP"), ("TOP", "M"), ("M", "C"))],
}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


OPENER = build_opener(ProxyHandler({}), NoRedirect())


def blob(data):
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def safe_rel(path):
    p = Path(path)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(f"Unsafe pinned path: {path}")
    return p


def environment(work, extra=None):
    env = {k: os.environ[k] for k in ("PATH", "LANG", "LC_ALL", "LD_LIBRARY_PATH") if k in os.environ}
    home = work / "home"
    home.mkdir(exist_ok=True)
    env.update(HOME=str(home), XDG_CACHE_HOME=str(home / "cache"), TMPDIR=str(work),
               PYTHONDONTWRITEBYTECODE="1")
    if extra:
        env.update(extra)
    return env


def read_pin(path, sources, sha):
    rel = safe_rel(path)
    for root in sources:
        src = root / rel
        if src.is_file():
            data = src.read_bytes()
            if blob(data) != sha:
                raise ValueError(f"Git blob mismatch: {rel}")
            return data
    raise FileNotFoundError(f"Missing fixed file: {rel}")


def stage(work, web_source, core_source):
    fixed = work / "fixed"
    for path, sha in PINS["paths"].items():
        data = read_pin(path, [web_source], sha)
        dst = fixed / safe_rel(path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        if path.endswith("mcis-bowtie.sh"):
            dst.chmod(0o755)
    for path, (sha, mode) in PINS["core"].items():
        data = read_pin(path, [core_source, web_source], sha)
        dst = fixed / safe_rel(path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            assert blob(dst.read_bytes()) == sha, path
        else:
            dst.write_bytes(data)
        dst.chmod(int(mode, 8) & 0o777)
        assert blob(dst.read_bytes()) == sha
    assert PINS["web_candidate"] == "912d96a39f1a68e98008a7317a211f5e29ed3845"
    assert PINS["core_pack"] == "8d108442f94901bee862ba5f53dd6343350b2718"
    print(f"W15 pinned {len(PINS['paths'])} web-candidate blobs at {PINS['web_candidate'][:7]} "
          f"and {len(PINS['core'])} original-core files at {PINS['core_pack'][:7]} "
          f"(product base {PINS['product_base'][:7]})", flush=True)
    return fixed


def build_assets(fixed, work, modules):
    web = fixed / "web"
    (web / "node_modules").symlink_to(modules, target_is_directory=True)
    assets = work / "assets"
    assets.mkdir()
    subprocess.run(
        [str(modules / ".bin/esbuild"), "src/main.tsx", "--bundle", "--platform=browser",
         "--format=esm", "--jsx=automatic", '--define:process.env.NODE_ENV="production"',
         "--loader:.svg=dataurl", "--log-level=warning", f"--outfile={assets / 'app.js'}"],
        cwd=web, env=environment(work), check=True)
    (assets / "index.html").write_text(
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>MCIS W15 acceptance</title><link rel="stylesheet" href="/app.css">'
        '<div id="root"></div><script type="module" src="/app.js"></script></html>')
    print(f"Built exact 912d96a product entry: {(assets / 'app.js').stat().st_size} JS bytes", flush=True)
    return assets


def build_core(fixed, work, dotnet, evidence):
    interfaces = {s.split(":", 1)[0].strip()
                  for s in Path("/proc/net/dev").read_text().splitlines()[2:] if ":" in s}
    feed = work / "empty-feed"
    feed.mkdir(exist_ok=True)
    packages = work / "packages"
    packages.mkdir(exist_ok=True)
    extra = dict(MCIS_DOTNET=str(dotnet), DOTNET_ROOT=str(dotnet.parent),
                 DOTNET_CLI_TELEMETRY_OPTOUT="1", DOTNET_NOLOGO="1", NuGetAudit="false",
                 RestoreSources=str(feed), RestoreFallbackFolders="",
                 NUGET_PACKAGES=str(packages))
    env = environment(work, extra)
    # Keep the operator's initialized HOME for SDK preflight; do not forge first-use state.
    if "HOME" in os.environ:
        env["HOME"] = os.environ["HOME"]
    cmd = ["unshare", "-r", "-n", "env",
           *[f"{k}={v}" for k, v in extra.items()],
           "HOME=" + env["HOME"],
           "PATH=" + env.get("PATH", "/usr/bin:/bin"),
           "PYTHONDONTWRITEBYTECODE=1",
           sys.executable, "-B", str(fixed / "tools/mcis-bowtie/build.py")]
    log = evidence / "core-build.log"
    with log.open("w") as fh:
        fh.write("interfaces_before_unshare=" + ",".join(sorted(interfaces)) + "\n")
        fh.write("cmd=" + " ".join(cmd) + "\n")
        fh.flush()
        proc = subprocess.run(cmd, cwd=fixed, stdout=fh, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Original core build failed in offline namespace, exit {proc.returncode}; see {log}")
    manifest = json.loads((fixed / "tools/mcis-bowtie/out/build-manifest.json").read_text())
    assert manifest["contract"] == "mcis-bowtie-build/1" and manifest["sdk"] == SDK
    (evidence / "build-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"Original core built; sdk={manifest['sdk']}; artifacts={sorted(manifest['artifacts'])}", flush=True)
    return extra


def send(origin, method, path, status, body=None):
    assert urlsplit(origin).hostname == "127.0.0.1" and path.startswith("/api/v1/")
    req = Request(origin + path, method=method, headers={**HEADERS, "Content-Type": "application/json"},
                  data=None if body is None else json.dumps(body).encode())
    try:
        with OPENER.open(req, timeout=30) as reply:
            code, result, headers = reply.status, json.load(reply), reply.headers
    except HTTPError as exc:
        with exc:
            code, result, headers = exc.code, json.load(exc), exc.headers
    assert code == status, f"Unexpected synthetic response: {method} {path}: {code} expected {status}"
    if "/systemic/" in path:
        assert headers.get("Cache-Control") == "no-store"
    return result


@contextmanager
def host(python, work, fixed, assets, data, output, extra, suffix):
    env = environment(work, extra)
    env["PYTHONPATH"] = str(fixed / "service")
    # CLI may no-op-build; keep the operator HOME already used for the offline build.
    if "HOME" in os.environ:
        env["HOME"] = os.environ["HOME"]
    with (output / f"host-{suffix}.log").open("w") as stderr:
        proc = subprocess.Popen([str(python), str(HERE / "host.py"), str(assets), str(data)],
                                cwd=fixed, env=env, text=True, stdout=subprocess.PIPE, stderr=stderr)
        try:
            line = proc.stdout.readline().strip() if select.select([proc.stdout], [], [], 30)[0] else ""
            assert re.fullmatch(r"W15_LOOPBACK_PORT=[1-9][0-9]{3,4}", line), "Local service failed to start"
            origin = "http://127.0.0.1:" + line.split("=")[1]
            for _ in range(100):
                try:
                    send(origin, "GET", "/api/v1/health", 200)
                    break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError("Local service not healthy")
            yield origin
        finally:
            if proc.poll() is None:
                proc.terminate()
            try:
                proc.wait(8)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            proc.stdout.close()


def setup(origin):
    send(origin, "POST", "/api/v1/cases", 201, dict(
        caseId=CASE, title=CASE, schemaVersion="1.0.0", accidentType="Collision",
        incidentTimeUtc="2026-01-01T00:00:00Z", caseEpochUtc="2026-01-01T00:00:00Z",
        incidentLocation={"latDeg": 0, "lonDeg": 0}, displayTimeZoneOffsetMinutes=0,
        isFictionalDemo=True))
    evidence = send(origin, "POST", f"/api/v1/cases/{CASE}/evidence", 201, dict(
        title=TITLE, source="Synthetic", extractedBy="W15", extractedUtc="2026-01-01T00:00:00Z",
        relativePath="evidence/EV-001/synthetic.txt", category="Document",
        contentBase64=b64encode(TITLE.encode()).decode()))
    assert evidence["evidenceId"] == "EV-001"


def source(origin):
    found = send(origin, "GET", f"/api/v1/cases/{CASE}/systemic/bowtie:sources", 200)["sources"]
    assert len(found) == 1 and found[0]["evidenceId"] == "EV-001" and found[0]["title"] == TITLE


def dump(data):
    with sqlite3.connect(data / "acceptance.sqlite") as db:
        return hashlib.sha256("\n".join(db.iterdump()).encode()).hexdigest()


def fill_official_form(page):
    page.get_by_label("危险源（背景条件，不等于事故结果）", exact=True).fill(MODEL["hazard"])
    page.get_by_label("顶事件 ID", exact=True).fill(MODEL["topEvent"]["id"])
    page.get_by_label("顶事件描述", exact=True).fill(MODEL["topEvent"]["label"])
    for i, node in enumerate(MODEL["nodes"], 1):
        page.get_by_role("button", name="添加节点", exact=True).click()
        page.get_by_label(f"节点 ID {i}", exact=True).fill(node["id"])
        page.get_by_label(f"节点名称 {i}", exact=True).fill(node["label"])
        page.get_by_label(f"节点类型 {i}", exact=True).select_option(node["kind"])
    for i, edge in enumerate(MODEL["edges"], 1):
        page.get_by_role("button", name="添加连线", exact=True).click()
        page.get_by_label(f"起点 ID {i}", exact=True).fill(edge["fromId"])
        page.get_by_label(f"终点 ID {i}", exact=True).fill(edge["toId"])
    page.get_by_role("checkbox", name="EV-001").check()


def run_browser(origin, browser_path, evidence, first):
    from playwright.sync_api import expect, sync_playwright

    page_errors, blocked, preview_events = [], [], []
    rec = {}
    with sync_playwright() as pw, tempfile.TemporaryDirectory(prefix="w15-page-core-chrome-") as tmp:
        launch_args = []
        browser = pw.chromium.launch(
            executable_path=str(browser_path),
            headless=True,
            chromium_sandbox=True,
            args=launch_args,
            env={**os.environ, "HOME": tmp, "XDG_CONFIG_HOME": f"{tmp}/config"},
        )
        rec["browserVersion"] = browser.version
        rec["chromiumSandbox"] = True
        rec["noSandboxArg"] = any(a == "--no-sandbox" or a.startswith("--no-sandbox=") for a in launch_args)
        assert rec["noSandboxArg"] is False
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        context.add_init_script(
            "localStorage.setItem('mcis.role','LeadInvestigator');\n"
            "localStorage.setItem('mcis.operator','Synthetic W15');")

        def route(req):
            if urlsplit(req.request.url).netloc == urlsplit(origin).netloc and req.request.url.startswith("http://"):
                req.continue_()
            else:
                blocked.append(req.request.url)
                req.abort()

        context.route("**/*", route)
        context.route_web_socket("**/*", lambda ws: (blocked.append("WebSocket"), ws.close()))
        page = context.new_page()
        page.set_default_timeout(20000)
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))

        def net(event, request, status="-"):
            if request.method == "POST" and request.url.endswith("/systemic/bowtie:preview"):
                preview_events.append({"event": event, "status": status, "url": request.url})
                print(f"W15 BROWSER t={time.monotonic():.6f} preview {event} status={status}",
                      file=sys.stderr, flush=True)

        page.on("request", lambda req: net("request", req))
        page.on("response", lambda res: net("response", res.request, res.status))
        page.on("requestfinished", lambda req: net("requestfinished", req))
        page.on("requestfailed", lambda req: net("requestfailed", req))
        page.goto(origin + f"/#/systemic?case={CASE}")
        expect(page.get_by_role("heading", name="系统性分析 · Bow-tie 假设草拟")).to_be_visible()
        expect(page.locator("#w153-draft-sources")).to_contain_text("EV-001")
        expect(page.locator("#w153-draft-sources")).to_contain_text(TITLE)
        expect(page.get_by_label("危险源（背景条件，不等于事故结果）", exact=True)).to_have_value("")
        expect(page.locator(".w153-result")).to_have_count(0)
        if first:
            page.screenshot(path=str(evidence / "01-official-page-before-submit.png"), full_page=True)
            fill_official_form(page)
            with page.expect_response(
                    lambda r: r.url.endswith("/systemic/bowtie:preview") and r.request.method == "POST",
                    timeout=30000) as matched:
                page.get_by_role("button", name="运行结构核查（不保存）", exact=True).click()
            result = matched.value
            assert result.status == 200, f"preview HTTP {result.status}"
            assert result.header_value("cache-control") == "no-store"
            body = result.json()
            posted = result.request.post_data_json
            assert posted["sourceEvidenceIds"] == ["EV-001"]
            assert posted["model"] == MODEL
            assert body["persisted"] is False
            assert body["assessment"] == "hypothesis-structure-only"
            assert body["sourceBinding"] == "registered-metadata-only"
            assert body["caseId"] == CASE
            assert body["result"]["coreVersion"] == "mcis-bowtie/1"
            assert body["result"]["mode"] == "hypothesis-structure-only"
            assert body["result"]["structureValid"] is True
            assert (body["result"]["nodeCount"], body["result"]["edgeCount"]) == (5, 4)
            assert not body["result"]["constructionErrors"] and not body["result"]["validationIssues"]
            assert body["sources"][0]["evidenceId"] == "EV-001"
            assert body["sources"][0]["title"] == TITLE
            expect(page.get_by_role("heading", name="核心结构核查结果 · 非事实确认", exact=True)).to_be_visible()
            panel = page.locator(".w153-result")
            expect(panel).to_contain_text("未发现本切片结构错误，不代表安全或因果成立。")
            expect(panel).to_contain_text("临时接收节点 5 / 连线 4")
            expect(panel).to_contain_text(body["inputSha256"])
            expect(panel).not_to_contain_text("节点级")
            (evidence / "preview-200.json").write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n")
            (evidence / "preview-request.json").write_text(json.dumps(posted, ensure_ascii=False, indent=2) + "\n")
            panel.scroll_into_view_if_needed()
            page.screenshot(path=str(evidence / "02-core-panel-after-post-200.png"), full_page=True)
            rec["preview"] = {
                "status": 200,
                "coreVersion": body["result"]["coreVersion"],
                "nodeCount": 5,
                "edgeCount": 4,
                "structureValid": True,
                "persisted": False,
                "inputSha256": body["inputSha256"],
            }
        else:
            expect(page.get_by_role("checkbox", name="EV-001")).not_to_be_checked()
            expect(page.locator(".w153-result")).to_have_count(0)
            page.screenshot(path=str(evidence / "03-reopen-same-db.png"), full_page=True)
            rec["reopenPreviewPosts"] = [e for e in preview_events if e["event"] == "request"]
            assert rec["reopenPreviewPosts"] == []
        assert not blocked, blocked
        assert not page_errors, page_errors
        context.close()
        browser.close()
    rec["previewEvents"] = preview_events
    return rec


def main():
    assert __debug__
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--web-source", type=Path, required=True, help="912d96a web-candidate checkout")
    parser.add_argument("--core-source", type=Path, required=True, help="8d10844 original-core pack checkout")
    parser.add_argument("--node-modules", type=Path, required=True)
    parser.add_argument("--host-python", type=Path, required=True)
    parser.add_argument("--dotnet", type=Path, required=True)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    arg = parser.parse_args()
    arg.web_source = arg.web_source.absolute()
    arg.core_source = arg.core_source.absolute()
    arg.node_modules = arg.node_modules.absolute()
    # Keep the venv entry path; resolve() would follow bin/python to /usr/bin/python3.
    arg.host_python = arg.host_python.absolute()
    arg.dotnet = arg.dotnet.absolute()
    arg.browser = arg.browser.absolute()
    arg.evidence = arg.evidence.absolute()
    arg.evidence.mkdir(parents=True, exist_ok=True)
    assert arg.dotnet.is_file(), arg.dotnet
    version = subprocess.check_output([str(arg.dotnet), "--version"], text=True).strip()
    assert version == SDK, version
    with tempfile.TemporaryDirectory(prefix="mcis-w15-page-core-") as tmp:
        work = Path(tmp)
        fixed = stage(work, arg.web_source, arg.core_source)
        assets = build_assets(fixed, work, arg.node_modules)
        extra = build_core(fixed, work, arg.dotnet, arg.evidence)
        data = work / "store"
        data.mkdir()
        with host(arg.host_python, work, fixed, assets, data, arg.evidence, extra, "first") as origin:
            setup(origin)
            source(origin)
            baseline = dump(data)
            (arg.evidence / "00-env.txt").write_text(
                "\n".join([
                    f"web_candidate={PINS['web_candidate']}",
                    f"core_pack={PINS['core_pack']}",
                    f"product_base={PINS['product_base']}",
                    f"dotnet={arg.dotnet} {version}",
                    f"origin={origin}",
                    f"sqlite={data / 'acceptance.sqlite'}",
                    f"baseline={baseline}",
                ]) + "\n")
            first = run_browser(origin, arg.browser, arg.evidence, first=True)
            after = dump(data)
            assert after == baseline, "preview must not write the official database"
        with host(arg.host_python, work, fixed, assets, data, arg.evidence, extra, "reopened") as origin:
            source(origin)
            assert dump(data) == baseline
            reopen = run_browser(origin, arg.browser, arg.evidence, first=False)
            assert dump(data) == baseline
        receipt = {
            "webCandidate": PINS["web_candidate"],
            "corePack": PINS["core_pack"],
            "productBase": PINS["product_base"],
            "sdk": version,
            "browser": first,
            "reopen": reopen,
            "sqliteUnchanged": True,
            "passed": True,
        }
        (arg.evidence / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        print("PASS official sandboxed Chrome: 912d96a page called original 8d10844 core; "
              "POST 200 coreVersion=mcis-bowtie/1; panel 5 nodes / 4 edges, structure passed, "
              "input summary matched return; EV-001 registered metadata only; sketch not persisted; "
              "same SQLite reopen kept sources and empty result panel.", flush=True)


if __name__ == "__main__":
    main()
