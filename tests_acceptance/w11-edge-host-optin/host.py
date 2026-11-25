"""In-process synthetic acceptance application. Never imported by production."""
import json
from pathlib import Path
import re
import socket
import sys
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy import text

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"w11-excerpt-binding-local"))
from check import DDL, TRIGGER, graph, seed, LEAD, CUSTODY, API, no_net
from pilot import CASE, EDGE, SOURCE_SHA, read_excerpt
from mcis_service.common.context import get_ctx
from mcis_service.config import Settings
from mcis_service.ecfc_drafts import router as ec
from mcis_service.main import create_app

PATH=f"/__local_synthetic_w11/{CASE}/edge-excerpt"

def setup(app):
    # The only route of this disposable trial. Production app itself is unchanged.
    @app.post(PATH,include_in_schema=False)
    async def edge_read(request:Request,ctx=Depends(get_ctx)):
        result=None
        if request.headers.get("X-MCIS-Role") and request.headers.get("X-MCIS-Operator"):
            data=bytearray()
            async for chunk in request.stream():
                if len(data)+len(chunk)>1024: break
                data.extend(chunk)
            else:
                from starlette.concurrency import run_in_threadpool
                try:
                    args=ec.strict_json(bytes(data))
                except ec.PreviewError:
                    args=None
                if (isinstance(args,dict) and set(args)=={"caseId","revision","digest","edgeId","from","to"}
                    and type(args["revision"]) is int and args["revision"]>=1
                    and isinstance(args["digest"],str) and re.fullmatch(r"[0-9a-f]{64}",args["digest"])):
                    result=await run_in_threadpool(read_excerpt,ctx,args["caseId"],args["revision"],args["digest"],(args["edgeId"],args["from"],args["to"]))
        if result is None:
            return JSONResponse({"code":"SOURCE_UNAVAILABLE"},status_code=404,headers={"Cache-Control":"no-store"})
        return JSONResponse({"context":args,"locator":"/sourceBytes/97/121","sourceUtc":result["sourceRecordedUtc"],
                             "excerpt":result["excerpt"]},headers={"Cache-Control":"no-store"})

def host(mode,directory,fixture):
    root=Path(directory)
    cfg=Settings(data_dir=root,db_url=f"sqlite:///{root/'w11.sqlite'}",seed_demo=False)
    app=create_app(cfg)
    with TestClient(app) as default:
        assert default.post(PATH,json={},headers=LEAD).status_code==404
    setup(app)
    ctx=SimpleNamespace(settings=cfg,db=app.state.db,role=LEAD["X-MCIS-Role"],operator=LEAD["X-MCIS-Operator"])
    with TestClient(app) as c:
        if mode=="setup":
            from hashlib import sha256
            source=Path(fixture).read_bytes()
            assert sha256(source).hexdigest()==SOURCE_SHA
            receipt=seed(c,source)
            g=graph(ctx,receipt)
            with ctx.db.session() as s:
                s.execute(text(DDL));s.execute(text(TRIGGER))
                s.execute(text("CREATE TRIGGER pilot_no_delete BEFORE DELETE ON pilot_single_source BEGIN SELECT RAISE(ABORT,'fixed'); END"))
                s.execute(text("""INSERT INTO pilot_single_source VALUES(1,:case,:rev,:digest,:edge,:src,:target,
                   'EV-001',:intake,:sha,97,121,0)"""),
                   dict(case=CASE,rev=g["revision"],digest=g["digest"],edge=EDGE[0],src=EDGE[1],target=EDGE[2],intake=receipt["requestDigest"],sha=SOURCE_SHA))
            return json.loads(ec.get_draft(CASE,ctx).body)
        if mode=="revoke":
            from mcis_service.db import WRITE_LOCK
            with WRITE_LOCK,ctx.db.session() as s:
                ec.begin(s,write=True)
                assert s.execute(text("UPDATE pilot_single_source SET revoked=1 WHERE singleton=1 AND revoked=0")).rowcount==1
            return {"revoked":True}
        if mode=="revised":
            old=json.loads(ec.get_draft(CASE,ctx).body)["document"]
            meta=old["sources"][0]
            graph(ctx,{"metadata":meta},old)
            return json.loads(ec.get_draft(CASE,ctx).body)
        if mode in ("read","denied"):
            args=json.load(sys.stdin)
            headers=LEAD if mode=="read" else {"X-MCIS-Role":"Public","X-MCIS-Operator":"SyntheticBlocked"}
            r=c.post(PATH,json=args,headers=headers)
            assert r.headers["Cache-Control"]=="no-store"
            return {"status":r.status_code,"body":r.json()}
        if mode=="logs":
            r=c.get(CUSTODY,headers=LEAD);assert r.status_code==200
            audit=c.get(API+"/audit:verify",headers=LEAD);assert audit.status_code==200
            cmds=c.get(API+"/sim/commands",headers=LEAD);assert cmds.status_code==200
            return {"custody":[x["kind"] for x in r.json()],"valid":audit.json()["valid"],"commands":cmds.json()["commands"]}
        raise ValueError(mode)

if __name__=="__main__":
    with patch.object(socket.socket,"connect",no_net), patch.object(socket.socket,"connect_ex",no_net), patch.object(socket,"getaddrinfo",no_net):
        print(json.dumps(host(*sys.argv[1:]),ensure_ascii=False))
