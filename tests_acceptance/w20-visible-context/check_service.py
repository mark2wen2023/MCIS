"""Synthetic true FastAPI/SQLite source drift guard; no real model or network."""
import json
import os
import socket
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from fastapi.testclient import TestClient
from mcis_service.agents import model_client
from mcis_service.config import Settings
from mcis_service.main import create_app

CASE = "SYN-W20-CURRENT-CONTEXT"
RECORD = "IR-90"
ROOT = f"/api/v1/cases/{CASE}"
INTERVIEWS = ROOT + "/interviews"
DRAFTS = ROOT + "/agents/drafts"
LEAD = {"X-MCIS-Role": "LeadInvestigator", "X-MCIS-Operator": "SyntheticReviewer"}
QUOTE = "right rudder requested"
ITEM = {"kind": "Operation", "subject": "synthetic.rudder", "summary": "Synthetic request only", "claim": {"valueType":"Occurrence", "occurred": True}, "round":1, "field":"Answer", "quote": QUOTE}
DOC = {"caseId":CASE, "title":"Synthetic W20 citation only", "schemaVersion":"1.0.0", "accidentType":"Collision",
       "incidentTimeUtc":"2026-01-01T00:00:00Z", "caseEpochUtc":"2026-01-01T00:00:00Z",
       "incidentLocation":{"latDeg":0,"lonDeg":0}, "displayTimeZoneOffsetMinutes":0,"isFictionalDemo":True}

def no_net(*_a, **_kw):
    raise AssertionError("No network model is allowed")

def expected(client, method, path, status, data=None):
    kwargs = {} if data is None else {"json":data}
    result = client.request(method, path, headers=LEAD, **kwargs)
    assert result.status_code == status, (method,path,result.status_code,result.text)
    return result.json()

def main():
    with TemporaryDirectory() as tmp, patch.dict(os.environ, {"MCIS_AGENT_BASE_URL":"http://127.0.0.1:12345/v1", "MCIS_AGENT_MODEL":"controlled-fake-not-real-model"}), \
        patch.object(model_client, "complete", return_value=json.dumps({"statements":[ITEM]})) as fake, \
        patch.object(socket.socket,"connect", no_net), patch.object(socket.socket,"connect_ex",no_net), patch.object(socket,"getaddrinfo",no_net):
        cfg = Settings()
        cfg.data_dir = Path(tmp)
        cfg.db_url = f"sqlite:///{tmp}/acceptance.sqlite"
        cfg.seed_demo = False
        app = create_app(cfg)
        with TestClient(app) as client:
            expected(client,"POST","/api/v1/cases",201,DOC)
            expected(client,"POST",INTERVIEWS,201,{"recordId":RECORD,"interviewee":{"intervieweeId":"SYN-P","name":"Synthetic Person","role":"Synthetic Position","affiliation":"Synthetic organization"},"startUtc":"2026-01-01T00:00:00Z","statements":[]})
            path = f"{INTERVIEWS}/{RECORD}"
            expected(client,"POST",path+"/turns",201,{"question":"What was requested?","answer":QUOTE})
            draft = expected(client,"POST",f"{ROOT}/agents/people_ops/interviews/{RECORD}:extract",201)
            assert draft["status"] == "PendingReview" and not expected(client,"GET",path,200)["statements"]
            assert draft["citations"] == [{"recordId":RECORD,"round":1,"quote":QUOTE}]
            expected(client,"POST",path+"/turns",201,{"question":"Any confirmation?","answer":"Synthetic addition; execution not stated."})
            assert expected(client,"POST",f"{DRAFTS}/{draft['draftId']}/review",409,{"decision":"Confirmed"})["code"] == "SOURCE_CHANGED"
        with TestClient(create_app(cfg)) as client:
            assert not expected(client,"GET",path,200)["statements"]
            assert expected(client,"GET",DRAFTS,200)[0]["status"] == "PendingReview"
            assert fake.call_count == 1
        print("W20 true FastAPI/SQLite: PendingReview -> source added -> 409 SOURCE_CHANGED -> reopened still pending, zero written statements; controlled fake model")

if __name__ == "__main__":
    main()
