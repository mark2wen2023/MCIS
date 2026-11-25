"""Read-only W11 pilot acceptance for a fixed synthetic association; fixture core only."""
import base64
from pathlib import Path
from types import SimpleNamespace
import socket
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import text
from mcis_service.config import Settings
from mcis_service.ecfc_drafts import router as ec
from mcis_service.main import create_app
from pilot import CASE, EDGE, SOURCE_SHA, UTC, read_excerpt

LEAD={"X-MCIS-Role":"LeadInvestigator","X-MCIS-Operator":"LocalSyntheticLead"}
API=f"/api/v1/cases/{CASE}"
CUSTODY=API+"/evidence/EV-001/custody"
DOC=dict(caseId=CASE,title="Synth-only graph source",schemaVersion="1.0.0",accidentType="Collision",
         incidentTimeUtc="2026-02-01T12:00:00Z",caseEpochUtc="2026-02-01T12:00:00Z",
         incidentLocation={"latDeg":0,"lonDeg":0},displayTimeZoneOffsetMinutes=0,isFictionalDemo=True)

DDL="""CREATE TABLE pilot_single_source(
 singleton INTEGER PRIMARY KEY CHECK(singleton=1), case_id TEXT NOT NULL,
 revision INTEGER NOT NULL, graph_digest TEXT NOT NULL,
 edge_id TEXT NOT NULL, from_id TEXT NOT NULL, to_id TEXT NOT NULL,
 evidence_id TEXT NOT NULL, intake_digest TEXT NOT NULL, source_sha TEXT NOT NULL,
 start_byte INTEGER NOT NULL, end_byte INTEGER NOT NULL,
 revoked INTEGER NOT NULL CHECK(revoked IN (0,1)))"""
# The only supported state transition is 0→1, with all identifying values unchanged.
TRIGGER="""CREATE TRIGGER pilot_revoke_only BEFORE UPDATE ON pilot_single_source
WHEN OLD.revoked<>0 OR NEW.revoked<>1 OR NEW.singleton<>OLD.singleton OR NEW.case_id<>OLD.case_id
 OR NEW.revision<>OLD.revision OR NEW.graph_digest<>OLD.graph_digest OR NEW.edge_id<>OLD.edge_id
 OR NEW.from_id<>OLD.from_id OR NEW.to_id<>OLD.to_id OR NEW.evidence_id<>OLD.evidence_id
 OR NEW.intake_digest<>OLD.intake_digest OR NEW.source_sha<>OLD.source_sha
 OR NEW.start_byte<>OLD.start_byte OR NEW.end_byte<>OLD.end_byte
BEGIN SELECT RAISE(ABORT,'pilot association is fixed'); END"""

def no_net(*_a,**_k): raise AssertionError("Network unavailable in synthetic fixture")

def req(c, method, path, status=200, body=None):
    r=c.request(method,path,headers=LEAD,**({"json":body} if body is not None else {}))
    assert r.status_code==status,(method,path,r.status_code,r.text[:180])
    return r.json()

def seed(c, raw):
    req(c,"POST","/api/v1/cases",201,DOC)
    body=dict(profile="mcis-evidence-intake-v1",fileName="communication.txt",title="Synthetic communication",
              source="Handmade synthetic fixture",extractedBy="Synthetic author",extractedUtc="2026-02-01T00:00:00Z",
              category="Document",confidentiality="Restricted",note="No real record",
              contentBase64=base64.b64encode(raw).decode())
    draft=req(c,"POST",API+"/evidence-intakes:preview",body=body)
    receipt=req(c,"POST",API+"/evidence-intakes:commit",body={**body,"confirmed":True,"requestDigest":draft["requestDigest"]})
    assert receipt["sourceSha256"]==SOURCE_SHA and receipt["evidenceId"]=="EV-001"
    return receipt

def fixture_core(payload):
    draft=payload["draft"]
    result={"coreVersion":"mcis-ecfc-draft/1","nodes":[{**n,"isPresumptive":True} for n in draft["nodes"]],
            "edges":[{**e,"kind":"Influence","bold":False} for e in draft["edges"]],"issues":[]}
    return ec.validate_result(result,draft,ec.integrity)

def graph(ctx, receipt, previous=None):
    a,b=EDGE[1:]
    def node(key,kind,source):
        return {"id":key,"kind":kind,"text":"Synthetic condition" if source else "Synthetic unknown event",
                "timeSeconds":None,"lane":0,"isPrimaryIncident":False,"evidenceIds":["EV-001"] if source else []}
    draft={"scope":"Synthetic edge, no finding" if previous is None else "Synthetic graph revision",
           "nodes":[node(a,"Condition",True),node(b,"Event",False)],
           "edges":[dict(zip(("id","from","to"),EDGE,strict=True))]}
    body={"requestId":"6bff10c5-3381-4fcc-8c53-a1120bba0cee" if previous is None else "6bff10c5-3381-4fcc-8c53-a1120bba0cef",
          "expectedDigest":previous["digest"] if previous else None,"draft":draft,"acknowledgeArchiveLimitation":True,
          "expectedSources":[{"evidenceId":"EV-001","title":receipt["metadata"]["title"],"sha256":SOURCE_SHA}]}
    validated,sources=ec.validate_body(body)
    # The .NET process is unavailable locally; only its output is replaced explicitly.
    with patch.object(ec,"run_core",fixture_core):
        doc=ec.save_sync(ctx,CASE,validated,sources)["document"]
    assert doc["status"]=="Draft" and doc["strength"]=="ToBeVerified"
    return doc

def open_store(cfg):
    app=create_app(cfg)
    # Private no-route test host (no app API mount). The product's save/get helpers
    # operate on their own validated storage classes and real Database sessions.
    ctx=SimpleNamespace(db=app.state.db,settings=cfg,role=LEAD["X-MCIS-Role"],operator=LEAD["X-MCIS-Operator"])
    return app,ctx

def scenario(raw, action):
    with TemporaryDirectory() as directory:
        root=Path(directory)
        cfg=Settings(data_dir=root,db_url=f"sqlite:///{root/'pilot.sqlite'}",seed_demo=False)
        app,ctx=open_store(cfg)
        with TestClient(app) as c:
            receipt=seed(c,raw)
            assert read_excerpt(ctx,CASE,1,"x",EDGE) is None
            g=graph(ctx,receipt)
            assert ec.get_draft(CASE,ctx).status_code==200
            with ctx.db.session() as s:
                s.execute(text(DDL));s.execute(text(TRIGGER));s.execute(text("""CREATE TRIGGER pilot_no_delete BEFORE DELETE ON pilot_single_source BEGIN SELECT RAISE(ABORT,'pilot association is fixed'); END"""))
                s.execute(text("""INSERT INTO pilot_single_source VALUES (1,:case,:rev,:graph,:edge,:from_,:to_,
                    'EV-001',:request,:sha,97,121,0)"""),dict(case=CASE,rev=g["revision"],graph=g["digest"],edge=EDGE[0],
                    from_=EDGE[1],to_=EDGE[2],request=receipt["requestDigest"],sha=SOURCE_SHA))
            assert read_excerpt(ctx,CASE,1,g["digest"],("E01","C01","WRONG")) is None
            assert read_excerpt(SimpleNamespace(**{**vars(ctx),"role":"Public"}),CASE,1,g["digest"],EDGE) is None
            assert read_excerpt(ctx,"SYN-WRONG",1,g["digest"],EDGE) is None
            assert [a["kind"] for a in req(c,"GET",CUSTODY)]==["Register"]
        app.state.db.engine.dispose()
        app,ctx=open_store(cfg)
        with TestClient(app) as c:
            out=read_excerpt(ctx,CASE,1,g["digest"],EDGE)
            assert out=={"excerpt":UTC,"sourceRecordedUtc":UTC,"seekAvailable":False,"status":"Draft","strength":"ToBeVerified"}
            if action=="revoked":
                with ctx.db.session() as s: s.execute(text("UPDATE pilot_single_source SET revoked=1 WHERE singleton=1"))
            else:
                new=graph(ctx,receipt,g)
                assert new["revision"]==2 and new["digest"]!=g["digest"]
                assert read_excerpt(ctx,CASE,2,new["digest"],EDGE) is None
            assert read_excerpt(ctx,CASE,1,g["digest"],EDGE) is None
            assert [a["kind"] for a in req(c,"GET",CUSTODY)]==["Register","Access"]
        app.state.db.engine.dispose()
        app,ctx=open_store(cfg)
        with TestClient(app) as c:
            assert read_excerpt(ctx,CASE,1,g["digest"],EDGE) is None
            assert [a["kind"] for a in req(c,"GET",CUSTODY)]==["Register","Access"]
            assert req(c,"GET",API+"/audit:verify")["valid"]
            assert req(c,"GET",API+"/sim/commands")["commands"]==[]
        app.state.db.engine.dispose()

if __name__=="__main__":
    if not __debug__: raise RuntimeError("Do not use Python -O")
    from hashlib import sha256
    source=Path(sys.argv[1]).read_bytes()
    assert sha256(source).hexdigest()==SOURCE_SHA
    with patch.object(socket.socket,"connect",no_net),patch.object(socket.socket,"connect_ex",no_net),patch.object(socket,"getaddrinfo",no_net):
        for action in ("revoked","revised"): scenario(source,action)
    print("W11 saved-graph local adapter: exact excerpt after reopen; separate revocation and revision trials fail closed; one Access each; zero seek. Explicit synthetic core fixture, NOT real .NET.")
