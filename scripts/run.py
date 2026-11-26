#!/usr/bin/env python3
"""Synthetic-only W4.1 Linux Chrome scoped gate. Never run the historical W4 runner."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import select
import shutil
import socket
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time
from contextlib import contextmanager
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler

PIN = "94d5e38c926fda232bb987b60fa9145e4bcf01a7"
CASES = {"SYN-W41-X-A": (45, 50), "SYN-W41-X-B": (70, 81)}
EPOCH = "2026-01-01T00:00:00Z"
OPENER = build_opener(ProxyHandler({}))


def require(condition, name):
    if not condition:
        raise RuntimeError(name)


def host_entry(assets, data):
    from unittest.mock import patch
    import uvicorn
    from fastapi.staticfiles import StaticFiles
    from mcis_service.config import Settings
    from mcis_service.main import create_app

    cfg = Settings(data_dir=data, db_url=f"sqlite:///{data / 'mcis.db'}", seed_demo=False)
    require(os.environ["MCIS_SEED_DEMO"] == "0", "demo seed not disabled")
    app = create_app(cfg)
    app.mount("/", StaticFiles(directory=assets, html=True))
    def deny(*args, **kwargs):
        raise RuntimeError("outbound networking prohibited")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(128)
        print(f"W41_PORT={sock.getsockname()[1]}", flush=True)
        with patch.object(socket.socket, "connect", deny), patch.object(socket.socket, "connect_ex", deny):
            uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", access_log=False, log_level="warning")).run(sockets=[sock])


def api(origin, path, status, doc=None):
    req = Request(origin + "/api/v1" + path, data=None if doc is None else json.dumps(doc).encode(),
                  headers={"X-MCIS-Role": "LeadInvestigator", "X-MCIS-Operator": "SyntheticW41",
                           "Content-Type": "application/json"})
    with OPENER.open(req, timeout=4) as res:
        require(res.status == status, "unexpected local service status")
        return json.load(res)


def seed(origin):
    for case in CASES:
        api(origin, "/cases", 201,
            {"caseId": case, "title": case, "schemaVersion": "1.0.0", "accidentType": "Collision",
             "incidentTimeUtc": EPOCH, "caseEpochUtc": EPOCH, "incidentLocation": {"latDeg": 0, "lonDeg": 0},
             "displayTimeZoneOffsetMinutes": 0, "isFictionalDemo": True})


def dump(data):
    path = data / "mcis.db"
    require(path.is_file(), "missing SQLite baseline")
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
        return hashlib.sha256("\n".join(db.iterdump()).encode()).hexdigest()


@contextmanager
def service(python, work, assets, data, env, output):
    with output.open("x") as err:
        p = subprocess.Popen([str(python), str(Path(__file__).resolve()), "--host-entry", str(assets), str(data)],
                             cwd=work, env=env, stdout=subprocess.PIPE, stderr=err, text=True)
        try:
            line = p.stdout.readline().strip() if select.select([p.stdout], [], [], 20)[0] else ""
            require(re.fullmatch(r"W41_PORT=[1-9][0-9]{3,4}", line), "loopback service start failed")
            origin = "http://127.0.0.1:" + line.split("=")[1]
            for _ in range(30):
                try:
                    require(api(origin, "/health", 200)["status"] == "ok", "unhealthy service")
                    break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError("loopback service not ready")
            yield origin
        finally:
            p.terminate()
            try:
                p.wait(8)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait(5)
            p.stdout.close()


def flow(browser, origin, width, output, reopened):
    from playwright.sync_api import expect
    context = browser.new_context(viewport={"width": width, "height": 900 if width == 1440 else 844},
                                  service_workers="block")
    blocked, errors, writes = [], [], []
    def route(r):
        url = urlsplit(r.request.url)
        if url.scheme == "http" and url.netloc == urlsplit(origin).netloc:
            r.continue_()
        else:
            blocked.append(True)
            r.abort()
    context.route("**/*", route)
    context.route_web_socket("**/*", lambda ws: (blocked.append(True), ws.close()))
    context.add_init_script("""localStorage.setItem('mcis.role','LeadInvestigator');
                               localStorage.setItem('mcis.operator','SyntheticW41');""")
    page = context.new_page()
    page.on("pageerror", lambda _: errors.append(True))
    page.on("request", lambda r: writes.append((r.method, urlsplit(r.url).path))
            if r.method in {"POST", "PUT", "PATCH", "DELETE"} else None)
    panel = page.locator(".w4-preview")
    result = panel.get_by_role("region", name="临时预览结果")
    csv_fields = panel.locator("textarea.w4-csv")
    calc = panel.get_by_role("button", name="计算临时预览", exact=True)
    def show(case):
        page.goto(f"{origin}/#/evidence?case={case}", timeout=15000)
        disclosure = page.locator(".w4-preview-disclosure")
        expect(disclosure).to_be_visible()
        require(disclosure.get_attribute("open") is None, "disclosure opened automatically")
        disclosure.locator("summary").first.click()
        expect(csv_fields).to_have_count(1)
        expect(csv_fields.first).to_have_value("")
        expect(result).to_have_count(0)
        expect(calc).to_be_disabled()
    def preview(case):
        low, high = CASES[case]
        panel.get_by_role("button", name="添加CSV源").click()
        expect(csv_fields).to_have_count(2)
        for i, val in enumerate((low, high)):
            csv_fields.nth(i).fill(f"time_utc,cog_deg\n{EPOCH},{val}\n2026-01-01T00:01:00Z,{val}\n")
            panel.get_by_label("UTC时间列名", exact=True).nth(i).fill("time_utc")
            panel.get_by_label("值列名", exact=True).nth(i).fill("cog_deg")
            mapping = panel.locator("fieldset").nth(i).get_by_role("combobox")
            expect(mapping).to_have_count(1)
            mapping.select_option(value="CourseOverGround")
            expect(mapping).to_have_value("CourseOverGround")
        panel.get_by_role("checkbox").check()
        path = f"/api/v1/cases/{case}/timeline/align-preview"
        with page.expect_response(lambda r: r.request.method == "POST" and urlsplit(r.url).path == path,
                                  timeout=15000) as match:
            calc.click()
        require(match.value.status == 200, "genuine preview HTTP status not 200")
        expect(result).to_contain_text(case, timeout=15000)
        expect(result).to_contain_text("未入库")
        expect(result).to_contain_text("未全部校准")
        expect(result).to_contain_text(f"{high-low} deg")
        return path
    try:
        a, b = CASES
        allowed = []
        show(a)
        if not reopened:
            allowed.append(("POST", preview(a)))
            show(b)
            allowed.append(("POST", preview(b)))
            show(a)
        # Reopen the service and browser context: no retained preview, CSV or confirmation.
        require(page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "document overflows viewport")
        page.screenshot(path=str(output / f"w41-{width}-{'reopened' if reopened else 'fresh'}.png"))
        if not reopened:
            allowed.append(("POST", preview(a)))
            result.scroll_into_view_if_needed()
            require(page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "preview overflows viewport")
            page.screenshot(path=str(output / f"w41-{width}-unanchored.png"))
        require(writes == allowed, "unexpected browser mutating request")
        require(not blocked and not errors, "external or failed browser event")
        return len(allowed)
    finally:
        context.close()


def main():
    from playwright.sync_api import sync_playwright
    p = argparse.ArgumentParser(description=__doc__)
    for flag in ("source", "node-modules", "chrome", "host-python", "dotnet", "core-dll", "out"):
        p.add_argument("--" + flag, type=Path, required=True)
    p.add_argument("--core-sha256", required=True)
    a = p.parse_args()
    for key, path in vars(a).items():
        if isinstance(path, Path):
            setattr(a, key, path.absolute())
    require(sys.platform.startswith("linux"), "Linux required")
    for path in (a.chrome, a.host_python, a.dotnet):
        require(path.is_file() and os.access(path, os.X_OK), f"missing executable {path}")
    require(a.core_dll.is_file(), "prebuilt real core DLL missing")
    require(hashlib.sha256(a.core_dll.read_bytes()).hexdigest() == a.core_sha256, "core DLL SHA mismatch")
    version = subprocess.check_output([a.chrome, "--version"], text=True, timeout=10).strip()
    require("Chrome" in version or "Chromium" in version, "not an available Chrome binary")
    require(subprocess.check_output(["git", "-C", a.source, "cat-file", "-t", PIN], text=True).strip() == "commit",
            "missing fixed source commit")
    require((a.node_modules / "vite/bin/vite.js").is_file(), "installed Vite required (no install)")
    a.out.mkdir(exist_ok=False)
    rec = {"revision": PIN, "browser": version, "sandboxRequested": True, "cases": list(CASES),
           "coreDllSha256": a.core_sha256, "passed": False,
           "scope": "synthetic unanchored COG preview only; not W4 whole package"}
    try:
        with tempfile.TemporaryDirectory(prefix="w41-synthetic-") as tmp:
            work = Path(tmp)
            tree = work / "source"
            tree.mkdir()
            # Stage only the pinned source plus existing dependencies; no working-tree data.
            with subprocess.Popen(["git", "-C", a.source, "archive", PIN, "web", "service", "contracts", "tests_acceptance/W6/mcis-core-norebuild.sh"],
                                  stdout=subprocess.PIPE) as proc:
                with tarfile.open(fileobj=proc.stdout, mode="r|") as archive:
                    archive.extractall(tree, filter="data")
                require(proc.wait() == 0, "fixed archive failed")
            web = tree / "web"
            (web / "node_modules").symlink_to(a.node_modules, target_is_directory=True)
            assets = work / "dist"
            data = work / "store"
            data.mkdir()
            env = {"PATH": os.environ["PATH"], "HOME": str(work), "LANG": "C.UTF-8",
                   "PYTHONPATH": str(tree / "service"), "PYTHONDONTWRITEBYTECODE": "1",
                   "MCIS_SEED_DEMO": "0", "MCIS_DATA_DIR": str(data),
                   "MCIS_CORE": str(tree / "tests_acceptance/W6/mcis-core-norebuild.sh"),
                   "MCIS_DOTNET": str(a.dotnet), "MCIS_CORE_DLL": str(a.core_dll),
                   "DOTNET_ROOT": str(a.dotnet.resolve().parent), "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
                   "DOTNET_NOLOGO": "1"}
            node = shutil.which("node")
            require(node, "existing node executable required (no install)")
            with (a.out / "build.log").open("x") as log:
                subprocess.run([node, str(web / "node_modules/vite/bin/vite.js"), "build", "--outDir", str(assets)],
                               check=True, cwd=web, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=120)
            with sync_playwright() as pw:
                browser = pw.chromium.launch(executable_path=str(a.chrome), headless=True,
                                              chromium_sandbox=True, timeout=15000)
                try:
                    rec["browserRuntime"] = browser.version
                    with service(a.host_python, work, assets, data, env, a.out / "service-first.log") as origin:
                        seed(origin)
                        original = dump(data)
                        rec["previewPosts"] = {
                            str(width): flow(browser, origin, width, a.out, reopened=False) for width in (1440, 390)
                        }
                        require(dump(data) == original, "SQLite changed after preview workflows")
                    with service(a.host_python, work, assets, data, env, a.out / "service-reopened.log") as origin:
                        require(flow(browser, origin, 390, a.out, reopened=True) == 0, "unexpected reopen POST")
                        require(dump(data) == original, "SQLite changed after service restart")
                        rec["sqliteLogicalSha256"] = original
                finally:
                    browser.close()
            rec["passed"] = True
    finally:
        (a.out / "receipt.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--host-entry":
        host_entry(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        main()
