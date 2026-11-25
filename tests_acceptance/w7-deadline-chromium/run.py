"""Opt-in sandboxed real Chromium against two loopback processes, synthetic only."""
import argparse
from hashlib import sha1
import json
import os
from pathlib import Path
import socket
import shutil
import subprocess
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
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

CASE="SYN-W7-CHROMIUM-DEADLINE"
API=f"/api/v1/cases/{CASE}"
ROUNDS=API+"/consultation/rounds"
DOC=dict(caseId=CASE,title="Synthetic W7 two-deadline trial",schemaVersion="1.0.0",accidentType="Collision",
         incidentTimeUtc="2026-02-01T12:00:00Z",caseEpochUtc="2026-02-01T12:00:00Z",
         incidentLocation={"latDeg":0,"lonDeg":0},displayTimeZoneOffsetMinutes=0,isFictionalDemo=True)
PINS = {
    "web/src/consultation/RoundLifecycle.tsx":"274e3cea634d473510cac79311505c8fd839cf40",
    "web/src/pages/RecommendationsPage.tsx":"acc6a5f9f6906131c14b04942f718048722e25da",
    "service/mcis_service/recommendations/router.py":"aa39f644a3205f255c1a686295fc06f559282ebf",
}

def http_only(web,restart):
    for n in (1,2):
        data={"draftVersion":"SYN-DEADLINE-"+str(n),"parties":[{"partyId":"SYN-A","name":"虚构相关方"}],
              "draftSha256":"","isAgreedDeadline":n==2}
        if n==2: data["days"]=45
        status,result=endpoint(web,ROUNDS,data=data)
        assert status==201 and result["roundNo"]==n and result["isAgreedDeadline"]==(n==2),(status,result)
        assert endpoint(web,ROUNDS+f"/{n}/replies",data={"partyId":"SYN-A","text":"合成答复","comments":[]})[0]==201
        assert endpoint(web,ROUNDS+f"/{n}:close",data={})[1]["isClosed"]
    restart()
    status,result=endpoint(web,ROUNDS)
    assert status==200 and [(r["roundNo"],r["isAgreedDeadline"],r["isClosed"]) for r in result]==[(1,False,True),(2,True,True)]
    from datetime import datetime
    time_of=datetime.fromisoformat
    assert [(time_of(r["deadlineUtc"])-time_of(r["openedUtc"])).days for r in result]==[30,45]
    status,audit=endpoint(web,API+"/audit?category=Consultation")
    assert status==200 and len(audit)==6
    marks=[e["after"] for e in audit if e["action"]=="consultation.open"]
    assert len(marks)==2 and "默认 30 天" in marks[0] and "标记商定 45 天" in marks[1]
    assert endpoint(web,API+"/audit:verify")[1]["valid"] is True
    print("W7 HTTP-only preflight PASS: reopened loopback FastAPI/SQLite and audited default30/declared45; no Chromium result")

def main():
    if not __debug__: raise RuntimeError("Do not use Python -O")
    p=argparse.ArgumentParser()
    p.add_argument("--web",type=Path,required=True)
    p.add_argument("--service",type=Path,required=True)
    p.add_argument("--service-python",required=True)
    p.add_argument("--browser")
    p.add_argument("--playwright",type=Path,help="absolute entry file in existing Node Playwright installation")
    p.add_argument("--http-only",action="store_true")
    args=p.parse_args()
    if not args.http_only:
        if not args.browser or not args.playwright: p.error("--browser and --playwright must identify existing sandboxed browser and driver")
        r=subprocess.run([args.browser,"--version"],capture_output=True,text=True,env=SAFE_ENV)
        if r.returncode: p.exit(2,"BROWSER_BLOCKED: "+r.stderr.strip()+"\n")
        if not args.playwright.is_file(): p.exit(2,"BROWSER_BLOCKED: Existing Playwright entry missing\n")
    for relative,pin in PINS.items():
        prefix,name=relative.split("/",1)
        data=(getattr(args,prefix)/name).read_bytes()
        assert sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()==pin, relative
    webport,apiport=port(),port()
    assert webport!=apiport
    web,api=f"http://127.0.0.1:{webport}",f"http://127.0.0.1:{apiport}"
    with tempfile.TemporaryDirectory(prefix="w7-deadline-chromium-") as temp:
        root=Path(temp)
        webcopy=root/"web"
        webcopy.mkdir()
        for entry in ("src","public","index.html","package.json","vite.config.ts"):
            src=args.web.absolute()/entry
            if src.is_dir(): shutil.copytree(src,webcopy/entry)
            elif src.is_file(): shutil.copyfile(src,webcopy/entry)
        (webcopy/"node_modules").symlink_to(args.web.absolute()/"node_modules",target_is_directory=True)
        (webcopy/"gate.config.mts").write_text('import config from "./vite.config.ts"; export default {...config,cacheDir:"./isolated-vite-cache",server:{...config.server,hmr:false}};\n')
        ap=vp=bp=None
        try:
            def restart():
                nonlocal ap
                stop(ap)
                ap=start([args.service_python,"-B","-m","mcis_service"],args.service.absolute(),
                         {**SAFE_ENV,"MCIS_SEED_DEMO":"0","MCIS_PORT":str(apiport),"MCIS_DATA_DIR":str(root/"data")},root,"api")
                ready(api,"/openapi.json",ap)
            restart()
            assert endpoint(api,"/api/v1/cases",data=DOC)[0]==201
            vp=start(["node","node_modules/vite/bin/vite.js","--config","gate.config.mts","--configLoader","runner","--host","127.0.0.1",
                      "--port",str(webport),"--strictPort"],webcopy,{**SAFE_ENV,"MCIS_API":api},root,"web")
            ready(web,"/",vp)
            assert endpoint(web,"/src/main.tsx")[0]==200
            if args.http_only:
                http_only(web,restart)
            else:
                bp=subprocess.Popen(["node",str(Path(__file__).with_name("browser.cjs").resolve()),web,args.browser,
                                     str(args.playwright.resolve()),CASE],env=SAFE_ENV,cwd=root,
                                     stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
                try:
                    restarts=0
                    for line in bp.stdout:
                        if line.strip()=="W7_RESTART_SQLITE":
                            restarts+=1
                            assert restarts==1
                            restart()
                            bp.stdin.write("READY\n");bp.stdin.flush()
                        else: print(line.rstrip(),flush=True)
                    assert bp.wait(timeout=30)==0 and restarts==1
                finally: stop(bp)
        except Exception:
            for log in root.glob("*.log"): print(f"{log.name}:\n{log.read_text()[-6000:]}")
            raise
        finally:
            stop(vp);stop(ap)

if __name__=="__main__": main()
