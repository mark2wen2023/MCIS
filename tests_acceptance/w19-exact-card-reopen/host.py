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
SAMPLE = {
    "kind": "Method", "title": "合成重开候选卡", "summary": "只用于软件测试，不是真实调查。",
    "body": "保留原始观察与不确定性。", "tags": ["合成重开"],
    "applicability": "仅供合成验收。",
    "source": {"type": "Synthetic", "title": "合成来源样本", "locator": "第 3 段",
               "excerpt": "原文摘录始终保留。", "rightsNote": "合成数据，明确用于测试。"},
}

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

def exercise(path):
    db = Database("sqlite:///" + str(path))
    app = test_app(db)
    approved = False
    withdrawn = False
    try:
        Base.metadata.create_all(db.engine)
        with TestClient(app) as client:
            r = client.post(BASE + "/cards", json=SAMPLE, headers=headers("Investigator"))
            assert r.status_code == 201
            card = r.json()
            cid, digest = card["cardId"], card["contentDigest"]
            record_path = BASE + "/cards/" + cid
            unknown_path = BASE + "/cards/KC-" + "0" * 32
            assert client.get(record_path, headers=headers("Public")).status_code == 404
            output({"ready": True, "id": cid, "digest": digest})
            for line in sys.stdin:
                req = json.loads(line)
                if req == {"control": "reopen"}:
                    assert approved and not withdrawn
                    db.engine.dispose()
                    db = Database("sqlite:///" + str(path))
                    app.state.db = db
                    output({"reopened": True})
                    continue
                if req == {"control": "withdraw"}:
                    assert approved and not withdrawn
                    r = client.post(record_path + "/review", json={"decision": "Withdrawn",
                                    "expectedDigest": digest, "note": "合成撤回"}, headers=headers(ROLE))
                    assert r.status_code == 200
                    assert client.get(record_path, headers=headers("Public")).status_code == 404
                    withdrawn = True
                    output({"withdrawn": True})
                    continue
                assert set(req) == {"path", "method", "role", "body"}
                assert req["role"] in (ROLE, "Public")
                if req["method"] == "POST":
                    assert not approved and req["role"] == ROLE and req["path"] == record_path + "/review"
                    assert req["body"] == {"decision": "Published", "expectedDigest": digest,
                                           "note": "合成明确审核备注", "sourceVerified": True,
                                           "rightsVerified": True, "releaseApproved": True}
                    r = client.post(req["path"], json=req["body"], headers=headers(ROLE))
                    assert r.status_code == 200 and r.json()["status"] == "Published"
                    approved = True
                else:
                    assert req["method"] == "GET" and req["body"] is None
                    assert req["path"] in (record_path, unknown_path) or re.fullmatch(
                        BASE + r"/cards\?status=(Candidate|Published)&limit=20&offset=0", req["path"])
                    r = client.get(req["path"], headers=headers(req["role"]))
                    if req["path"] == record_path and r.status_code == 200:
                        data = r.json()
                        assert data["contentDigest"] == digest and data["content"] == SAMPLE
                output({"status": r.status_code, "digest": sha256(r.content).hexdigest(),
                        "bodyBase64": b64encode(r.content).decode()})
            assert approved and withdrawn
            audit = client.get(BASE + "/audit", headers=headers(ROLE)).json()
            assert [a["action"] for a in audit] == ["knowledge.create", "knowledge.published", "knowledge.withdrawn"]
            assert client.get(BASE + "/audit:verify", headers=headers(ROLE)).json() == {"valid": True, "count": 3}
            with db.session() as s:
                assert s.scalar(select(func.count()).select_from(KnowledgeCardRow)) == 1
                assert s.scalar(select(func.count()).select_from(KnowledgeAuditRow)) == 3
    finally:
        db.engine.dispose()

with TemporaryDirectory(prefix="w19-card-reopen-") as folder:
    exercise(Path(folder) / "records.db")
assert not Path(folder).exists()
