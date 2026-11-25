"""W9.2 exact product browser gate; temporary synthetic service exclusively on loopback."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import select
import shutil
import subprocess
from tempfile import TemporaryDirectory
import time
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

HERE = Path(__file__).resolve().parent
BASE = "26dd466fcbdeb8422fcb54a5985d93df2103f4cc"
CASE = "synthetic-env-write-reopen"
OTHER = "synthetic-env-unrelated"
PREFIX = "/api/v1/cases"
OBSERVATIONS = "/environment-observations"
WRITE = f"{PREFIX}/{CASE}{OBSERVATIONS}"
OTHER_OBSERVATIONS = f"{PREFIX}/{OTHER}{OBSERVATIONS}"
RECORD = dict(caseId=CASE, observationId="SYN-W9-01", observedAtUtc=None,
              locationDescription=" 合成河段 S ", description=" 合成原文，未估算来流。 ",
              sourceLabel=" 合成来源第 7 页 ", valueOrigin="Direct", currentSpeedKn=0)
HTML = """<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>W9.2 合成环境观测验收</title><link rel="icon" href="/assets/favicon.svg"><link rel="stylesheet" href="/assets/entry.css"><main id="root"></main><script type="module" src="/assets/entry.js"></script></html>"""

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None

OPENER = build_opener(ProxyHandler({}), NoRedirect())
ENV = {k: v for k, v in os.environ.items() if k in ("PATH", "LANG", "LC_ALL", "LD_LIBRARY_PATH")}

def digest(content):
    return hashlib.sha256(content).hexdigest()

def stage(src, fixed):
    manifest = json.loads((HERE / "pins.json").read_text())
    assert len(manifest) == 73
    for name, expected in manifest.items():
        assert re.fullmatch(r"(?:service|web|contracts)/[a-zA-Z0-9_./-]+", name) and ".." not in Path(name).parts
        content = (src / name).read_bytes()
        assert hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest() == expected, name
        target = fixed / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    print(f"W9.2 pinned {len(manifest)} exact product blobs at {BASE}", flush=True)

def build(fixed, deps, work, env):
    assets = work / "assets"
    assets.mkdir()
    shutil.copyfile(HERE / "entry.tsx", fixed / "entry.tsx")
    (fixed / "node_modules").symlink_to(deps, target_is_directory=True)
    subprocess.run([str(deps / ".bin/esbuild"), "entry.tsx", "--bundle", "--format=esm",
                    "--platform=browser", "--jsx=automatic", '--define:process.env.NODE_ENV="production"',
                    "--log-level=warning", f"--outfile={assets / 'entry.js'}"],
                   check=True, cwd=fixed, env=env, timeout=35)
    (assets / "index.html").write_text(HTML, encoding="utf-8")
    (assets / "favicon.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"/>')
    assert (assets / "entry.css").is_file()
    print(f"W9.2 exact EnvironmentPage shell built: JS {(assets/'entry.js').stat().st_size} bytes", flush=True)
    return assets

def request(origin, path, expected, method="GET", body=None, role="Public"):
    assert urlsplit(origin).hostname == "127.0.0.1"
    assert path in {"/environment", "/assets/entry.js", "/assets/entry.css", PREFIX, WRITE,
                    f"{PREFIX}/{CASE}", f"{PREFIX}/{OTHER}", OTHER_OBSERVATIONS}
    raw = None if body is None else json.dumps(body).encode()
    op = Request(origin+path, method=method, data=raw,
                 headers={"X-MCIS-Role": role, "X-MCIS-Operator":"synthetic-ui", "Content-Type":"application/json"})
    with OPENER.open(op, timeout=5) as resp:
        assert resp.status == expected
        return resp.read()

def seed(origin):
    for cid in (CASE, OTHER):
        value = dict(caseId=cid, schemaVersion="1.0.0", title="合成环境记录验收",
                     accidentType="Collision", caseEpochUtc="2026-01-01T00:00:00Z",
                     incidentTimeUtc="2026-01-01T00:00:00Z", incidentLocation={"lonDeg":0,"latDeg":0},
                     displayTimeZoneOffsetMinutes=0, isFictionalDemo=True)
        assert json.loads(request(origin, PREFIX, 201, "POST", value, "Investigator"))["caseId"] == cid
    assert json.loads(request(origin, WRITE, 200)) == []

@contextmanager
def host(command, evidence, phase, work, env):
    with (evidence / f"{phase}.stderr").open("w") as stderr:
        proc = subprocess.Popen(command, env=env, cwd=work,
                                stdout=subprocess.PIPE, stderr=stderr, text=True)
        try:
            assert proc.stdout is not None
            line = proc.stdout.readline().strip() if select.select([proc.stdout], [], [], 15)[0] else ""
            port = re.fullmatch(r"W92_PORT=([1-9][0-9]{3,4})", line)
            assert port is not None, "Fixture server did not bind"
            origin = f"http://127.0.0.1:{port.group(1)}"
            for _ in range(100):
                try:
                    shell = request(origin, "/environment", 200)
                    assert "W9.2 合成环境观测验收" in shell.decode()
                    break
                except OSError:
                    time.sleep(.08)
            else:
                raise RuntimeError("Fixture server did not become ready")
            yield origin
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            if proc.stdout:
                proc.stdout.close()

def check_store(command, work, env):
    result = subprocess.run([*command, "--audit-only"], env=env, cwd=work, timeout=15,
                            check=True, capture_output=True, text=True)
    expected = {"observationRows":1, "observationWriteAuditRows":1, "auditChainValid":True}
    assert json.loads(result.stdout) == expected
    return expected

def readback(origin, confirmed):
    same = request(origin, WRITE, 200)
    assert json.loads(same) == [RECORD] and digest(same) == confirmed
    assert json.loads(request(origin, OTHER_OBSERVATIONS, 200)) == []

@contextmanager
def context(browser, origin, viewport, role, drop=False):
    ctx = browser.new_context(viewport=viewport, service_workers="block")
    role_script = (
        f"if (location.origin === {json.dumps(origin)}) {{"
        f"localStorage.setItem('mcis.role', {json.dumps(role)});"
        "localStorage.setItem('mcis.operator','synthetic-ui'); }")
    ctx.add_init_script(role_script)
    posted, reads, blocked, page_errors, console_errors = [], [], [], [], []
    allowed = {"/environment","/assets/entry.css","/assets/entry.js","/assets/favicon.svg",
               f"{PREFIX}/{CASE}",f"{PREFIX}/{OTHER}",WRITE,OTHER_OBSERVATIONS}
    def handle(route):
        target = urlsplit(route.request.url)
        if f"{target.scheme}://{target.netloc}" != origin or target.path not in allowed:
            blocked.append("non-loopback or unexpected path")
            route.abort()
            return
        if route.request.method == "GET":
            route.continue_()
            return
        if route.request.method != "POST" or target.path != WRITE or not drop or posted:
            blocked.append("unexpected write")
            route.abort()
            return
        assert route.request.post_data_json == RECORD
        # Only the fixture endpoint. Forward it once and wait for real SQLite commit
        # (201); do not send a fabricated response or retry it.
        upstream = route.fetch(max_redirects=0, max_retries=0)
        try:
            assert upstream.status == 201 and upstream.json() == RECORD
            posted.append({"upstreamStatus":upstream.status, "responseSha256":digest(upstream.body())})
        finally:
            upstream.dispose()
            route.abort("failed")
    def websocket(route):
        blocked.append("unexpected websocket")
        route.close()
    ctx.route("**/*", handle)
    ctx.route_web_socket("**/*", websocket)
    page = ctx.new_page()
    page.on("pageerror", lambda _: page_errors.append("page exception"))
    def console(m):
        # A deliberately aborted fixture POST can produce a known Chromium
        # resource-load message; any other actual console error fails.
        if m.type == "error":
            location = m.location.get("url", "")
            console_errors.append((m.text, location))
    page.on("console", console)
    page.on("request", lambda req: reads.append(urlsplit(req.url).path)
            if req.method == "GET" and urlsplit(req.url).path in (WRITE, OTHER_OBSERVATIONS) else None)
    try:
        yield page, posted, reads
        assert not page_errors and not blocked
        for message, location in console_errors:
            assert drop and posted and location == origin+WRITE and "net::ERR_FAILED" in message, message
    finally:
        ctx.close()

def url(origin, cid):
    return origin + "/environment?case=" + cid

def rendered(page, origin, cid):
    from playwright.sync_api import expect
    page.goto(url(origin, cid))
    expect(page).to_have_url(url(origin, cid))
    expect(page).to_have_title("W9.2 合成环境观测验收")
    expect(page.get_by_role("heading",name="气象水文 · 观测记录")).to_be_visible()
    expect(page.get_by_text(cid,exact=True)).to_be_visible()
    expect(page.locator("vite-error-overlay")).to_have_count(0)

def desktop(browser, origin, evidence):
    from playwright.sync_api import expect
    with context(browser, origin, {"width":1440,"height":900}, "Investigator", drop=True) as (page, posted, reads):
        rendered(page, origin, CASE)
        expect(page.get_by_text("本案尚无环境观测记录。",exact=False)).to_be_visible()
        card = page.locator("article.w92-record")
        expect(card).to_have_count(0)
        assert reads.count(WRITE) == 1
        page.get_by_role("button",name="＋ 新增环境记录",exact=True).click()
        for label, key in (("观测编号","observationId"),("观测地点","locationDescription"),
                           ("资料来源","sourceLabel"),("原文与说明","description")):
            page.get_by_label(re.compile("^"+label)).fill(RECORD[key])
        page.get_by_label(re.compile("^整条记录的来源口径")).select_option("Direct")
        page.get_by_label(re.compile("^流速")).fill("0")
        page.get_by_role("button",name="保存环境记录",exact=True).click()
        expect(page.get_by_role("alert")).to_contain_text("保存结果尚未确认")
        expect(page.get_by_role("button",name="保存环境记录",exact=True)).to_have_count(0)
        expect(card).to_have_count(0)
        assert len(posted) == 1 and reads.count(WRITE) == 1
        page.screenshot(path=str(evidence/"01-uncertain-desktop.png"),full_page=True)
        with page.expect_response(lambda r: r.url == origin+WRITE and r.request.method == "GET") as info:
            page.get_by_role("button",name="核查保存结果（只读）",exact=True).click()
        verified = info.value
        assert verified.status == 200 and verified.json() == [RECORD]
        expect(page.get_by_role("heading",name="环境记录已保存",exact=True)).to_be_visible()
        expect(card).to_have_count(1)
        expect(card.get_by_role("heading",name=RECORD["observationId"],exact=True)).to_be_visible()
        assert len(posted) == 1 and reads.count(WRITE) == 2
        page.screenshot(path=str(evidence/"02-confirmed-desktop.png"),full_page=True)
        return digest(verified.body()), posted[0]

def narrow(browser, origin, confirmed, evidence):
    from playwright.sync_api import expect
    with context(browser,origin,{"width":390,"height":844},"Public") as (page,posted,reads):
        with page.expect_response(lambda r: r.url == origin+WRITE and r.request.method == "GET") as info:
            rendered(page, origin, CASE)
        response = info.value
        assert response.status == 200 and response.json() == [RECORD]
        assert digest(response.body()) == confirmed
        card = page.locator("article.w92-record")
        expect(card).to_have_count(1)
        expect(card.get_by_role("heading",name=RECORD["observationId"],exact=True)).to_be_visible()
        expect(card).to_contain_text("合成来源第 7 页")
        expect(card).to_contain_text("合成河段 S")
        assert card.locator(".w92-original").text_content() == RECORD["description"]
        expect(card.get_by_text("0 kn",exact=True)).to_be_visible()
        utc = card.locator("dl > div").filter(has=page.get_by_text("观测时刻（UTC）",exact=True))
        expect(utc.locator("dd")).to_have_text("未知")
        expect(page.get_by_text("不送入动力学计算",exact=False)).to_be_visible()
        expect(page.get_by_role("button",name="＋ 新增环境记录",exact=True)).to_have_count(0)
        page.screenshot(path=str(evidence/"03-reopened-narrow.png"),full_page=True)
        rendered(page, origin, OTHER)
        expect(page.get_by_text("本案尚无环境观测记录。",exact=False)).to_be_visible()
        expect(card).to_have_count(0)
        assert posted == [] and reads == [WRITE,OTHER_OBSERVATIONS]
        page.screenshot(path=str(evidence/"04-separate-case-narrow.png"),full_page=True)

def main():
    if not __debug__:
        raise SystemExit("Assertions must be enabled")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--node-modules", type=Path, required=True)
    p.add_argument("--host-python", type=Path)
    p.add_argument("--browser", type=Path)
    p.add_argument("--evidence", type=Path)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--build-only", action="store_true")
    g.add_argument("--http-only", action="store_true")
    a = p.parse_args()
    if not a.build_only:
        if not a.host_python or not a.evidence or (not a.http_only and not a.browser):
            p.error("--host-python and --evidence are required; browser mode requires --browser")
        if any(not x.is_absolute() for x in [a.host_python,a.evidence,*([a.browser] if a.browser else [])]):
            p.error("Use absolute host Python, Chrome and evidence paths")
        a.evidence.mkdir()
    receipt = {"product":BASE,"synthetic":True,"mode":"build" if a.build_only else "http" if a.http_only else "chrome",
               "result":"failed","trueBrowser":False}
    try:
        with TemporaryDirectory(prefix="mcis-w92-test-") as path:
            work = Path(path)
            home = work / "home"
            home.mkdir()
            env = {**ENV,"HOME":str(home),"TMPDIR":str(work),"PYTHONDONTWRITEBYTECODE":"1","XDG_CACHE_HOME":str(home/"cache")}
            fixed = work / "fixed"
            stage(a.source.resolve(),fixed)
            assets = build(fixed,a.node_modules.resolve(),work,env)
            if a.build_only:
                receipt["result"] = "passed"
                return
            fixture = work / "expected.json"
            fixture.write_text(json.dumps(RECORD),encoding="utf-8")
            command = [str(a.host_python), "-I", "-B", str(HERE/"host.py"), str(fixed),
                       str(assets), str(work/"db.sqlite"), str(fixture)]
            if a.http_only:
                with host(command,a.evidence,"initial",work,env) as origin:
                    assert request(origin,"/assets/entry.js",200) == (assets/"entry.js").read_bytes()
                    seed(origin)
                    created = request(origin,WRITE,201,"POST",RECORD,"Investigator")
                    assert json.loads(created) == RECORD
                    source = request(origin,WRITE,200)
                    assert json.loads(source) == [RECORD]
                    confirmed = digest(source)
                assert check_store(command,work,env)["observationRows"] == 1
                with host(command,a.evidence,"reopened",work,env) as origin:
                    readback(origin,confirmed)
                receipt.update(check_store(command,work,env))
                receipt["confirmedReadSha256"] = confirmed
                print("W9.2 actual HTTP/SQLite, byte-identical reopen and separate case PASS; browser not run")
            else:
                launch = subprocess.run([str(a.browser),"--version"],capture_output=True,text=True,env=env,timeout=10)
                if launch.returncode:
                    print(launch.stderr.strip(), flush=True)
                launch.check_returncode()
                from playwright.sync_api import sync_playwright
                receipt["browserVersion"] = launch.stdout.strip()
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(executable_path=str(a.browser),headless=True,
                                                chromium_sandbox=True,env=env,args=["--no-proxy-server"])
                    try:
                        with host(command,a.evidence,"initial",work,env) as origin:
                            seed(origin)
                            confirmed, sent = desktop(browser,origin,a.evidence)
                        check_store(command,work,env)
                        with host(command,a.evidence,"reopened",work,env) as origin:
                            narrow(browser,origin,confirmed,a.evidence)
                        receipt.update(check_store(command,work,env))
                    finally:
                        browser.close()
                receipt.update(trueBrowser=True,chromiumSandbox=True,browserFixturePostCount=1,
                               confirmedReadSha256=confirmed, committedPost=sent, viewport=[[1440,900],[390,844]])
                print("W9.2 normal sandbox Chrome source, loopback response loss, read-only reconciliation, SQLite reopen PASS")
            receipt["result"] = "passed"
    finally:
        if a.evidence:
            (a.evidence/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")

if __name__ == "__main__":
    main()
