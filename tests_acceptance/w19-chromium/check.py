"""Opt-in sandboxed real Chromium against two loopback processes, synthetic only."""
import argparse
from hashlib import sha1
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from urllib.parse import urlsplit

PINS = {"src/pages/KnowledgePage.tsx":"3cf927d55d988f8b83558d092498bbb7ab3d0fca",
        "src/knowledge/api.ts":"a5e0248c48e1786d7caecca2a8637572a251c5ee"}
BASE = "/api/v1/knowledge"
TITLE = "W19 真浏览器专用合成卡"
EXCERPT = "合成摘录：应当保留观察来源与限制。"
LOCATOR = "合成段落第 8 段"
LEAD = "LeadInvestigator"
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None

OPENER = build_opener(ProxyHandler({}), NoRedirect())
SAFE_ENV = {k:v for k,v in os.environ.items() if k in ("HOME","PATH","LD_LIBRARY_PATH","LANG","LC_ALL","TMPDIR")}

def endpoint(origin, path, role=LEAD, data=None):
    payload = None if data is None else json.dumps(data, ensure_ascii=False).encode()
    req = Request(origin + path, data=payload, headers={"X-MCIS-Role":role,"X-MCIS-Operator":"W19-synthetic",
                                                       "Content-Type":"application/json"})
    try:
        with OPENER.open(req, timeout=3) as r:
            raw = r.read()
            return r.status, json.loads(raw) if "application/json" in r.headers.get("content-type","") else raw
    except HTTPError as r:
        return r.code, json.loads(r.read())

def port():
    with socket.socket() as s:
        s.bind(("127.0.0.1",0))
        return s.getsockname()[1]

def start(args,cwd,env,root,name):
    with (root/(name+".log")).open("w+") as log:
        return subprocess.Popen(args,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT)

def stop(p):
    if p is not None and p.poll() is None:
        p.terminate()
        try: p.wait(timeout=8)
        except subprocess.TimeoutExpired:
            p.kill(); p.wait()

def ready(origin,path,proc):
    for _ in range(100):
        if proc.poll() is not None:
            raise RuntimeError(f"Loopback process exited {proc.returncode}: {origin}")
        try:
            if endpoint(origin,path)[0] == 200:
                return
        except OSError:
            time.sleep(.1)
    raise RuntimeError(f"Loopback process never ready: {origin}")

def http_only(web, restart):
    assert endpoint(web,"/")[0] == 200
    status, result = endpoint(web,BASE+"/cards?status=Candidate")
    assert status == 200 and result["total"] == 0
    assert endpoint(web,BASE+"/audit") == (200,[])
    sample={"kind":"Method","title":TITLE,"summary":"合成测试","body":EXCERPT,
            "tags":["合成测试"],"applicability":"仅限合成用例",
            "source":{"type":"Synthetic","title":"合成资料","locator":LOCATOR,"excerpt":EXCERPT,"rightsNote":"合成测试允许公开"}}
    status, card = endpoint(web,BASE+"/cards",data=sample)
    assert status==201 and card["status"]=="Candidate"
    detail=BASE+"/cards/"+card["cardId"]
    digest=card["contentDigest"]
    assert endpoint(web,detail,"Public")[0]==404
    request={"decision":"Published","expectedDigest":digest,"note":"HTTP 合成测试",
             "sourceVerified":True,"rightsVerified":True,"releaseApproved":True}
    status, card = endpoint(web,detail+"/review",data=request)
    assert status==200 and card["status"]=="Published"
    restart()
    status, card = endpoint(web,detail)
    assert status==200 and card["contentDigest"]==digest and card["content"]==sample
    status, card = endpoint(web,detail+"/review",data={"decision":"Withdrawn","expectedDigest":digest,"note":"HTTP 合成撤回"})
    assert status==200 and card["status"]=="Withdrawn"
    assert endpoint(web,detail,"Public")[0]==404
    assert endpoint(web,BASE+"/audit:verify")== (200,{"valid":True,"count":3})
    print("HTTP-only preflight PASS: Vite and real FastAPI/SQLite write/restart/readback/review/audit; browser NOT verified")

def browser_run(args, web, restart):
    from playwright.sync_api import sync_playwright, expect
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=args.browser, headless=True, chromium_sandbox=True, env=SAFE_ENV, args=["--no-proxy-server"])
        try:
            context = browser.new_context(service_workers="block")
            blocked = []
            def route(r):
                target=urlsplit(r.request.url)
                if (target.scheme, target.netloc) == ("http",urlsplit(web).netloc):
                    r.continue_()
                else:
                    blocked.append(r.request.url)
                    r.abort()
            context.route("**/*",route)
            def websocket(ws):
                target=urlsplit(ws.url)
                if (target.scheme,target.netloc)==("ws",urlsplit(web).netloc): ws.connect_to_server()
                else: blocked.append(ws.url); ws.close()
            context.route_web_socket("**/*", websocket)
            page = context.new_page()
            page.set_default_timeout(12000)
            writes=[]
            page.on("request",lambda r: writes.append(urlsplit(r.url).path) if r.method=="POST" else None)
            page.goto(web+"/#/knowledge")
            role=page.locator("select.role-select")
            role.select_option(LEAD)
            page.get_by_text("人工创建候选（不会自动公开）",exact=True).click()
            page.get_by_role("button",name="在表单中填入合成示例（不保存）").click()
            page.get_by_label("标题",exact=True).fill(TITLE)
            page.get_by_label("原文摘录",exact=True).fill(EXCERPT)
            page.get_by_label("页码/章节/段落定位",exact=True).fill(LOCATOR)
            assert writes == []
            page.get_by_role("button",name="保存为内部待审候选").click()
            candidate=page.locator(".w19-card").filter(has=page.get_by_role("heading",name=TITLE,exact=True))
            expect(candidate).to_be_visible()
            status,queue=endpoint(web,BASE+"/cards?status=Candidate")
            assert status==200 and queue["total"]==1
            entry=queue["items"][0]
            cid,digest=entry["cardId"],entry["contentDigest"]
            detail=BASE+"/cards/"+cid
            assert len(digest)==64 and endpoint(web,detail,"Public")[0]==404
            assert endpoint(web,BASE+"/cards","Public")[1]["total"]==0

            def read_back(expected_label):
                reader=page.get_by_role("region",name="按编号重开已保存知识卡")
                reader.get_by_label("已保存知识卡编号").fill(cid)
                reader.get_by_role("button",name="按编号重新读取").click()
                expect(reader.get_by_role("heading",name="按编号读回："+expected_label)).to_be_visible()
                reader.locator("article details > summary").click()
                for exact in (cid,digest,EXCERPT,entry["content"]["source"]["title"]+" · "+LOCATOR):
                    expect(reader.get_by_text(exact,exact=True)).to_be_visible()
                assert reader.get_by_role("button",name="批准发布到公开资料库").count()==0
                return reader

            read_back("待人工审批")
            role.select_option("Public")
            expect(page.get_by_text("只读已发布公开/合成知识卡",exact=False)).to_be_visible()
            expect(page.get_by_role("region",name="按编号重开已保存知识卡")).to_have_count(0)
            expect(page.get_by_role("heading",name=TITLE,exact=True)).to_have_count(0)
            role.select_option(LEAD)
            page.get_by_label("资料状态").select_option("Candidate")
            candidate.get_by_label("审核理由").fill("合成核验：明确批准该虚构资料。")
            approve=candidate.get_by_role("button",name="批准发布到公开资料库")
            expect(approve).to_be_disabled()
            checks=candidate.get_by_role("checkbox")
            assert checks.count()==3
            for i in range(3):
                checks.nth(i).check()
                if i<2: expect(approve).to_be_disabled()
            with page.expect_response(lambda r: urlsplit(r.url).path==detail+"/review" and r.request.method=="POST") as resp:
                approve.click()
            assert resp.value.status==200 and resp.value.json()["status"]=="Published"
            assert writes==[BASE+"/cards",detail+"/review"]
            restart()
            page.reload()
            role.select_option(LEAD)
            read_back("已人工批准发布")
            status,found=endpoint(web,detail)
            assert status==200 and found["contentDigest"]==digest
            assert found["content"]["source"]["excerpt"]==EXCERPT and found["content"]["source"]["locator"]==LOCATOR
            assert found["reviewNote"]=="合成核验：明确批准该虚构资料。"
            # Exact reader and normal list can both display this card; only the list has review controls.
            listing = candidate.filter(has=page.get_by_role("button",name="撤回并移出公开检索"))
            listing.get_by_label("审核理由").fill("合成测试撤回")
            with page.expect_response(lambda r: urlsplit(r.url).path==detail+"/review" and r.request.method=="POST") as resp:
                listing.get_by_role("button",name="撤回并移出公开检索").click()
            assert resp.value.status==200 and resp.value.json()["status"]=="Withdrawn"
            page.reload()
            role.select_option(LEAD)
            read_back("已撤回")
            role.select_option("Public")
            expect(page.get_by_role("region",name="按编号重开已保存知识卡")).to_have_count(0)
            expect(page.get_by_role("heading",name=TITLE,exact=True)).to_have_count(0)
            assert endpoint(web,detail,"Public")[0]==404
            assert endpoint(web,BASE+"/cards","Public")[1]["total"]==0
            assert writes==[BASE+"/cards",detail+"/review",detail+"/review"]
            assert [a["action"] for a in endpoint(web,BASE+"/audit")[1]]==["knowledge.create","knowledge.published","knowledge.withdrawn"]
            assert endpoint(web,BASE+"/audit:verify")== (200,{"valid":True,"count":3})
            assert not blocked, blocked
        finally:
            browser.close()
    print("Sandboxed Chromium + Vite + FastAPI/SQLite PASS (W19 synthetic internal candidate → explicit review → service reopen → withdrawn / Public denied)")

def main():
    if not __debug__: raise RuntimeError("Run without Python -O so acceptance assertions remain active")
    p=argparse.ArgumentParser()
    p.add_argument("--web",required=True,type=Path)
    p.add_argument("--service",required=True,type=Path)
    p.add_argument("--service-python",required=True)
    p.add_argument("--browser")
    p.add_argument("--http-only",action="store_true")
    args=p.parse_args()
    if not args.http_only:
        if not args.browser: p.error("--browser must name existing sandboxed Chromium")
        result=subprocess.run([args.browser,"--version"],capture_output=True,text=True)
        if result.returncode: p.exit(2,"BROWSER_BLOCKED: "+result.stderr.strip()+"\n")
        try: import playwright.sync_api
        except ImportError: p.exit(2,"BROWSER_BLOCKED: Playwright is not installed\n")
    for relative,pin in PINS.items():
        data=(args.web/relative).read_bytes()
        assert sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()==pin, relative
    webport,apiport=port(),port()
    assert webport!=apiport
    web,api=f"http://127.0.0.1:{webport}",f"http://127.0.0.1:{apiport}"
    # Do not forward credentials, model settings, database, or proxy configuration.
    env=SAFE_ENV
    args.web=args.web.absolute()
    args.service=args.service.absolute()
    with tempfile.TemporaryDirectory(prefix="mcis-w19-chromium-") as temp:
        root=Path(temp)
        ap=vp=None
        try:
            def restart():
                nonlocal ap
                stop(ap)
                ap=start([args.service_python,"-B","-m","mcis_service"],args.service,{**env,"MCIS_SEED_DEMO":"0",
                         "MCIS_PORT":str(apiport),"MCIS_DATA_DIR":str(root/"data")},root,"api")
                ready(api,BASE+"/cards",ap)
            restart()
            vp=start(["node","node_modules/vite/bin/vite.js","--host","127.0.0.1","--port",str(webport),"--strictPort"],
                     args.web,{**env,"MCIS_API":api},root,"web")
            ready(web,"/",vp)
            if args.http_only: http_only(web,restart)
            else: browser_run(args,web,restart)
        except Exception:
            for log in root.glob("*.log"): print(f"{log.name}:\n{log.read_text()[-7000:]}")
            raise
        finally:
            stop(vp);stop(ap)

if __name__=="__main__": main()
