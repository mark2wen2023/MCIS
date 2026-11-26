"""Pinned W15.3 negative acceptance: actual UI/service/SQLite, no .NET install."""
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
CASE_A, CASE_B = "SYN-W15-A", "SYN-W15-B"
TITLES = {CASE_A: "Synthetic source alpha", CASE_B: "Synthetic source beta"}
HEADERS = {"X-MCIS-Role": "LeadInvestigator", "X-MCIS-Operator": "Synthetic%20W15"}
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None
OPENER = build_opener(ProxyHandler({}), NoRedirect())

def environment(work):
    home = work / "home"
    home.mkdir(exist_ok=True)
    env = {k: os.environ[k] for k in ("PATH", "LANG", "LC_ALL", "LD_LIBRARY_PATH") if k in os.environ}
    return {**env, "HOME": str(home), "XDG_CACHE_HOME": str(home/"cache"),
            "TMPDIR": str(work), "PYTHONDONTWRITEBYTECODE": "1"}

def prepare(source, work, modules):
    pin = json.loads((HERE/"pins.json").read_text())
    fixed, assets = work/"fixed", work/"assets"
    for path, expected in pin["paths"].items():
        src = source / path
        data = src.read_bytes()
        git_blob = hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()
        assert git_blob == expected, f"Fixed source mismatch: {path}"
        dst = fixed / path
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        if path == "tools/mcis-bowtie/mcis-bowtie.sh": dst.chmod(0o755)
    print(f"W15 pinned {len(pin['paths'])} exact Git blobs at {pin['product']}", flush=True)
    web = fixed/"web"
    (web/"node_modules").symlink_to(modules, target_is_directory=True)
    assets.mkdir()
    subprocess.run([str(modules/".bin/esbuild"),"src/main.tsx","--bundle","--platform=browser",
        "--format=esm","--jsx=automatic",'--define:process.env.NODE_ENV="production"',
        "--loader:.svg=dataurl","--log-level=warning",f"--outfile={assets/'app.js'}"],
        cwd=web, env=environment(work), check=True)
    (assets/"index.html").write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>MCIS W15 acceptance</title><link rel="stylesheet" href="/app.css"><div id="root"></div><script type="module" src="/app.js"></script></html>')
    print(f"Built exact product entry: {(assets/'app.js').stat().st_size} JS bytes", flush=True)
    return fixed, assets

def send(origin, method, path, status, body=None):
    assert urlsplit(origin).hostname == "127.0.0.1" and path.startswith("/api/v1/")
    req = Request(origin+path, method=method, headers={**HEADERS,"Content-Type":"application/json"},
                  data=None if body is None else json.dumps(body).encode())
    try:
        with OPENER.open(req, timeout=8) as reply:
            code, result, headers = reply.status, json.load(reply), reply.headers
    except HTTPError as exc:
        with exc: code, result, headers = exc.code, json.load(exc), exc.headers
    assert code == status, f"Unexpected synthetic response: {method} {path}: {code} expected {status}"
    if "/systemic/" in path: assert headers.get("Cache-Control") == "no-store"
    return result

@contextmanager
def host(python, work, fixed, assets, data, output, suffix):
    with (output/f"host-{suffix}.log").open("w") as stderr:
        proc = subprocess.Popen([str(python),str(HERE/"host.py"),str(assets),str(data)],
              cwd=work,env={**environment(work),"PYTHONPATH":str(fixed/"service")},
              text=True,stdout=subprocess.PIPE,stderr=stderr)
        try:
            line=proc.stdout.readline().strip() if select.select([proc.stdout],[],[],20)[0] else ""
            assert re.fullmatch(r"W15_LOOPBACK_PORT=[1-9][0-9]{3,4}",line), "Local service failed to start"
            origin="http://127.0.0.1:"+line.split("=")[1]
            for _ in range(100):
                try:
                    send(origin,"GET","/api/v1/health",200)
                    break
                except OSError:
                    time.sleep(.1)
            else: raise RuntimeError("Local service not healthy")
            yield origin
        finally:
            proc.terminate()
            try: proc.wait(8)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            proc.stdout.close()

def setup(origin):
    for case,title in TITLES.items():
        send(origin,"POST","/api/v1/cases",201,dict(caseId=case,title=case,schemaVersion="1.0.0",
             accidentType="Collision",incidentTimeUtc="2026-01-01T00:00:00Z",caseEpochUtc="2026-01-01T00:00:00Z",
             incidentLocation={"latDeg":0,"lonDeg":0},displayTimeZoneOffsetMinutes=0,isFictionalDemo=True))
        evidence=send(origin,"POST",f"/api/v1/cases/{case}/evidence",201,
             dict(title=title,source="Synthetic",extractedBy="W15",extractedUtc="2026-01-01T00:00:00Z",
             relativePath="evidence/EV-001/synthetic.txt",category="Document",
             contentBase64=b64encode(title.encode()).decode()))
        assert evidence["evidenceId"]=="EV-001"

def source(origin, case):
    found=send(origin,"GET",f"/api/v1/cases/{case}/systemic/bowtie:sources",200)["sources"]
    assert len(found)==1 and found[0]["evidenceId"]=="EV-001" and found[0]["title"]==TITLES[case]
    assert found[0]["sha256"]==hashlib.sha256(TITLES[case].encode()).hexdigest()

def dump(data):
    with sqlite3.connect(data/"acceptance.sqlite") as db:
        return hashlib.sha256("\n".join(db.iterdump()).encode()).hexdigest()

def app_ui(browser, origin, evidence, reopened):
    from playwright.sync_api import expect
    context=browser.new_context(viewport={"width":390 if reopened else 1440,"height":844 if reopened else 900},
        service_workers="block")
    blocked, page_errors, previews = [], [], []
    def route(req):
        if urlsplit(req.request.url).netloc==urlsplit(origin).netloc and req.request.url.startswith("http://"):
            req.continue_()
        else:
            blocked.append("nonlocal request")
            req.abort()
    context.route("**/*",route)
    context.route_web_socket("**/*",lambda ws:(blocked.append("WebSocket"),ws.close()))
    context.add_init_script("""localStorage.setItem('mcis.role','LeadInvestigator');
      localStorage.setItem('mcis.operator','Synthetic W15');""")
    try:
        page=context.new_page()
        # Observe Chrome's own network events without consuming the response.
        cdp = context.new_cdp_session(page)
        preview_ids = set()
        def chrome_request(event):
            request = event.get("request", {})
            url = request.get("url", "")
            if (request.get("method") == "POST" and
                    urlsplit(url).netloc == urlsplit(origin).netloc and
                    urlsplit(url).path.endswith("/systemic/bowtie:preview")):
                preview_ids.add(event["requestId"])
                chrome_lifecycle("requestWillBeSent", event)
        def chrome_lifecycle(kind, event):
            if event.get("requestId") not in preview_ids:
                return
            status = event.get("response", {}).get("status", "-")
            size = event.get("encodedDataLength", "-")
            print(f"W15 CDP t={time.monotonic():.6f} preview {kind} "
                  f"status={status} encodedBytes={size}", file=sys.stderr, flush=True)
        cdp.on("Network.requestWillBeSent", chrome_request)
        cdp.on("Network.responseReceived", lambda e: chrome_lifecycle("responseReceived", e))
        cdp.on("Network.loadingFinished", lambda e: chrome_lifecycle("loadingFinished", e))
        cdp.on("Network.loadingFailed", lambda e: chrome_lifecycle("loadingFailed", e))
        cdp.send("Network.enable")
        # Observe the actual preview only; do not read the body here.
        def net(event, request, status="-"):
            if request.method == "POST" and request.url.endswith("/systemic/bowtie:preview"):
                print(f"W15 BROWSER t={time.monotonic():.6f} preview {event} status={status}",
                      file=sys.stderr, flush=True)
        page.on("request", lambda req: net("request", req))
        page.on("response", lambda res: net("response", res.request, res.status))
        page.on("requestfinished", lambda req: net("requestfinished", req))
        page.on("requestfailed", lambda req: net("requestfailed", req))
        page.on("pageerror",lambda _:page_errors.append("pageerror"))
        page.on("request",lambda q:previews.append(q.method) if q.url.endswith("bowtie:preview") else None)
        def show(case):
            page.goto(origin+f"/#/systemic?case={case}")
            expect(page.get_by_role("heading",name="系统性分析 · Bow-tie 假设草拟")).to_be_visible()
            panel=page.locator("#w153-draft-sources")
            other=CASE_B if case==CASE_A else CASE_A
            expect(panel).to_contain_text(TITLES[case])
            expect(panel).not_to_contain_text(TITLES[other])
            expect(panel.locator("input")).not_to_be_checked()
            expect(page.get_by_label("危险源（背景条件，不等于事故结果）",exact=True)).to_have_value("")
            expect(page.locator(".w153-result")).to_have_count(0)
            return panel
        panel=show(CASE_A)
        if reopened:
            page.screenshot(path=str(evidence/"03-restart-390.png"),full_page=True)
            assert not previews
        else:
            panel.locator("input").check()
            page.get_by_label("危险源（背景条件，不等于事故结果）",exact=True).fill("Synthetic hazard")
            page.get_by_label("顶事件 ID",exact=True).fill("TOP")
            page.get_by_label("顶事件描述",exact=True).fill("Synthetic top event")
            with page.expect_response(lambda r:r.url.endswith("/systemic/bowtie:preview") and r.request.method=="POST") as matched:
                page.get_by_role("button",name="运行结构核查（不保存）",exact=True).click()
            result=matched.value
            assert result.status==503 and result.header_value("cache-control")=="no-store"
            assert result.json()["code"]=="BOWTIE_CORE_UNAVAILABLE"
            assert result.request.post_data_json["sourceEvidenceIds"]==["EV-001"]
            note=page.get_by_role("alert").filter(has_text="计算核心暂不可用")
            expect(note).to_be_visible()
            expect(note).to_contain_text("不会用示例结果代替真实计算")
            expect(page.locator(".w153-result")).to_have_count(0)
            expect(page.get_by_text("定位草稿端点",exact=False)).to_have_count(0)
            page.screenshot(path=str(evidence/"01-core-unavailable-1440.png"),full_page=True)
            show(CASE_B)
            page.screenshot(path=str(evidence/"02-case-switch-1440.png"),full_page=True)
            show(CASE_A)
            assert previews==["POST"]
        assert not blocked and not page_errors
    finally:
        context.close()

def main():
    assert __debug__
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--node-modules",type=Path,required=True)
    parser.add_argument("--host-python",type=Path)
    parser.add_argument("--browser",type=Path)
    parser.add_argument("--evidence",type=Path)
    group=parser.add_mutually_exclusive_group()
    group.add_argument("--build-only",action="store_true")
    group.add_argument("--http-only",action="store_true")
    arg=parser.parse_args()
    if not arg.build_only:
        if not arg.host_python or not arg.evidence or (not arg.http_only and not arg.browser):
            parser.error("service mode requires --host-python and --evidence; Chrome mode also requires --browser")
        arg.host_python=arg.host_python.absolute()
        arg.evidence=arg.evidence.absolute()
        arg.evidence.mkdir()
    rec={"httpOnly":arg.http_only,"browserVerified":False,"passed":False}
    try:
        with tempfile.TemporaryDirectory(prefix="mcis-w15-synthetic-") as tmp:
            work=Path(tmp)
            fixed,assets=prepare(arg.source.resolve(),work,arg.node_modules.resolve())
            if arg.build_only: return
            data=work/"store"
            data.mkdir()
            if arg.http_only:
                with host(arg.host_python,work,fixed,assets,data,arg.evidence,"first") as origin:
                    setup(origin)
                    baseline=dump(data)
                    for case in TITLES: source(origin,case)
                    result=send(origin,"POST",f"/api/v1/cases/{CASE_A}/systemic/bowtie:preview",503,
                        {"model":{"hazard":"Synthetic hazard","topEvent":{"id":"TOP","label":"Synthetic top event"},"nodes":[],"edges":[]},"sourceEvidenceIds":["EV-001"]})
                    assert result["code"]=="BOWTIE_CORE_UNAVAILABLE"
                    assert "result" not in result
                with host(arg.host_python,work,fixed,assets,data,arg.evidence,"reopened") as origin:
                    for case in TITLES: source(origin,case)
                assert dump(data)==baseline
                print("W15 loopback HTTP and real SQLite restart PASS; no mutation, no browser or .NET execution")
            else:
                browser_path=arg.browser.absolute()
                try:
                    rec["browserVersion"]=subprocess.check_output([str(browser_path),"--version"],stderr=subprocess.STDOUT,
                        text=True,timeout=10,env=environment(work)).strip()
                except subprocess.CalledProcessError as exc:
                    print(f"Chrome executable check exited {exc.returncode}: {exc.output.strip()}",flush=True)
                    raise
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    browser=p.chromium.launch(executable_path=str(browser_path),headless=True,chromium_sandbox=True,
                         env=environment(work),args=["--no-proxy-server"])
                    try:
                        with host(arg.host_python,work,fixed,assets,data,arg.evidence,"first") as origin:
                            setup(origin)
                            baseline=dump(data)
                            app_ui(browser,origin,arg.evidence,False)
                        with host(arg.host_python,work,fixed,assets,data,arg.evidence,"reopened") as origin:
                            for case in TITLES: source(origin,case)
                            app_ui(browser,origin,arg.evidence,True)
                    finally:
                        browser.close()
                assert dump(data)==baseline
                rec["browserVerified"]=True
                rec["sandboxRequested"]=True
                print("W15 exact page: normal-sandbox Chromium + genuine service + SQLite restart PASS; negative gate only")
            rec["passed"]=True
    finally:
        if arg.evidence is not None:
            (arg.evidence/"receipt.json").write_text(json.dumps(rec,indent=2)+"\n")

if __name__=="__main__":
    main()
