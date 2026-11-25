"""Existing genuine sandboxed Chromium, no install or bypass."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit
from urllib.request import ProxyHandler,build_opener

here=Path(__file__).resolve().parent
py,fixture,workspace,browser,out=sys.argv[1:]
workspace=Path(workspace)
out=Path(out)
version=subprocess.run([browser,"--version"],capture_output=True,text=True)
if version.returncode:
    print("BROWSER_BLOCKED:",version.stderr.strip(),file=sys.stderr)
    raise SystemExit(2)
print("Browser:",version.stdout.strip(),"; chromium_sandbox=True",flush=True)
try:
    from playwright.sync_api import expect,sync_playwright
except ImportError:
    print("BROWSER_BLOCKED: existing Playwright missing",file=sys.stderr)
    raise SystemExit(2)

def run():
    with sync_playwright() as p:
        engine=p.chromium.launch(executable_path=browser,headless=True,chromium_sandbox=True,args=["--no-proxy-server"])
        try:
            for mode in ("revised","revoke"):
                store=workspace/("browser-"+mode)
                store.mkdir()
                def rpc(op):
                    return json.loads(subprocess.check_output([py,str(here/"host.py"),op,str(store),fixture],text=True))
                rpc("setup")
                with socket.socket() as listener:
                    listener.bind(("127.0.0.1",0))
                    port=listener.getsockname()[1]
                origin=f"http://127.0.0.1:{port}"
                urlpath="/__local_synthetic_w11/SYN-XREPO-001/edge-excerpt"
                server=subprocess.Popen([py,str(here/"browser_host.py"),str(store),str(workspace/"app.js"),str(port)])
                try:
                    opener=build_opener(ProxyHandler({}))
                    for _ in range(80):
                        if server.poll() is not None: raise RuntimeError("synthetic service exited")
                        try:
                            with opener.open(origin,timeout=.2) as response:
                                if response.status==200: break
                        except OSError: time.sleep(.1)
                    else: raise RuntimeError("localhost service did not become ready")
                    context=engine.new_context(service_workers="block")
                    off=[]
                    excerpt_posts=[]
                    def http(route):
                        u=urlsplit(route.request.url)
                        if (u.scheme,u.netloc)==("http",urlsplit(origin).netloc):
                            if u.path==urlpath and route.request.method=="POST":
                                excerpt_posts.append(u.path)
                            route.continue_()
                        else:
                            off.append(route.request.url);route.abort()
                    context.route("**/*",http)
                    def ws(route):
                        off.append(route.url);route.close()
                    context.route_web_socket("**/*",ws)
                    page=context.new_page()
                    page.set_default_timeout(9000)
                    page.goto(origin)
                    edge=page.get_by_role("button").filter(has_text="E01")
                    read=page.get_by_role("button",name="查看该连线关联出处",exact=True)
                    edge.click()
                    assert rpc("logs")["custody"]==["Register"]
                    assert excerpt_posts==[], (mode,"selection must not request excerpt",excerpt_posts)
                    with page.expect_response(lambda r:urlsplit(r.url).path==urlpath and r.request.method=="POST") as response:
                        read.click()
                    assert response.value.status==200 and response.value.headers["cache-control"]=="no-store"
                    assert excerpt_posts==[urlpath], (mode,"explicit read must be the first request",excerpt_posts)
                    expect(page.get_by_text("原始记录 UTC（非事件时刻）",exact=True)).to_be_visible()
                    expect(page.get_by_text("2026-02-01T12:01:49.000Z",exact=True).first).to_be_visible()
                    page.screenshot(path=str(out/(mode+"-read.png")),full_page=True)
                    rpc(mode)
                    if mode=="revised":
                        page.reload()
                        edge.click()
                    assert excerpt_posts==[urlpath], (mode,"change or selection must not request excerpt",excerpt_posts)
                    with page.expect_response(lambda r:urlsplit(r.url).path==urlpath and r.request.method=="POST") as response:
                        read.click()
                    assert response.value.status==404
                    expect(page.get_by_text("出处不可用；未显示旧内容。",exact=True)).to_be_visible()
                    expect(page.get_by_text("2026-02-01T12:01:49.000Z",exact=True)).to_have_count(0)
                    page.screenshot(path=str(out/(mode+"-denied.png")),full_page=True)
                    assert rpc("logs")=={"custody":["Register","Access"],"valid":True,"commands":[]}
                    assert not off,off
                    assert excerpt_posts==[urlpath,urlpath], (mode,"exactly two explicit excerpt requests",excerpt_posts)
                    print(f"{mode}: excerpt POST checkpoints 0/1/2; no automatic read",flush=True)
                    context.close()
                finally:
                    server.terminate()
                    try: server.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        server.kill();server.wait()
        finally: engine.close()
    print("W11 actual sandboxed Chromium + loopback service: reread after revision/revocation PASS")

run()
