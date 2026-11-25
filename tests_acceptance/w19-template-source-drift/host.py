"""Real W19 router only, synthetic case-free knowledge cards, temporary DB."""
from base64 import b64encode
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy import func, select

root = Path(os.environ["MCIS_HOST_SERVICE"])
sys.path.insert(0, str(root))
from mcis_service.db import Base, Database
from mcis_service.knowledge.models import KnowledgeAuditRow, KnowledgeCardRow
from mcis_service.knowledge.router import router
from mcis_service.knowledge_archive import models as _archive_models  # register tables

BASE = "/api/v1/knowledge"
ROLE = "LeadInvestigator"
OP = "w19-synthetic-reviewer"
def output(data):
    print(json.dumps(data, ensure_ascii=False), flush=True)

def headers(role):
    return {"X-MCIS-Role": role, "X-MCIS-Operator": OP}

def test_app(db):
    app = FastAPI()
    app.state.db = db
    @app.exception_handler(HTTPException)
    async def handled(_req, exc):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    app.include_router(router)
    return app

def main():
    import socket
    from unittest.mock import patch
    critical=["connect","connect_ex"]
    def fail(*_a,**_kw): raise AssertionError("unexpected network")
    with TemporaryDirectory() as folder, patch.dict(os.environ,{"MCIS_KNOWLEDGE_SUGGESTION_PROVIDER":"template-stub-v1"}), patch.object(socket.socket,critical[0],fail), patch.object(socket.socket,critical[1],fail), patch.object(socket,"getaddrinfo",fail):
        path=Path(folder)/"records.db"
        db=Database("sqlite:///"+str(path))
        Base.metadata.create_all(db.engine)
        app=test_app(db)
        with TestClient(app) as client:
            output({"ready":True})
            for line in sys.stdin:
                req=json.loads(line)
                if req=={"control":"reopen"}:
                    db.engine.dispose()
                    db=Database("sqlite:///"+str(path));app.state.db=db
                    output({"reopened":True})
                    continue
                assert req["role"] in (ROLE,"Public")
                if req["method"]=="POST":
                    assert req["role"]==ROLE and req["path"] in (BASE+"/suggestions",BASE+"/cards")
                else:
                    assert req["method"]=="GET" and req["body"] is None and req["path"].startswith(BASE+"/")
                r=client.request(req["method"],req["path"],json=req["body"],headers=headers(req["role"]))
                output({"status":r.status_code,"digest":sha256(r.content).hexdigest(),"bodyBase64":b64encode(r.content).decode()})
            audit=client.get(BASE+"/audit",headers=headers(ROLE)).json()
            assert [a["action"] for a in audit]==["knowledge.create"]
            assert client.get(BASE+"/audit:verify",headers=headers(ROLE)).json()=={"valid":True,"count":1}
            pending=client.get(BASE+"/cards?status=Candidate",headers=headers(ROLE)).json()
            assert pending["total"]==1
            item=pending["items"][0]
            assert item["content"]["body"]==item["content"]["source"]["excerpt"]=="全新的合成来源摘录，非真实材料。"
            assert client.get(BASE+"/cards/"+item["cardId"],headers=headers("Public")).status_code==404
        db.engine.dispose()

main()
