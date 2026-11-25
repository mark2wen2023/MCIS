"""Replay requests captured from the product UI in a fresh synthetic service."""
import json
import socket
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient
from mcis_service.main import create_app
from tests.conftest import H, make_settings

case = "SYN-W7-CREATE-BODY"
writes = json.loads(Path(sys.argv[1]).read_text())
assert len(writes) == 2
doc = dict(caseId=case, title="Synthetic W7 create", schemaVersion="1.0.0", accidentType="Collision",
           incidentTimeUtc="2026-01-01T00:00:00Z", caseEpochUtc="2026-01-01T00:00:00Z",
           incidentLocation={"latDeg": 0, "lonDeg": 0}, displayTimeZoneOffsetMinutes=0, isFictionalDemo=True)
lead = H("LeadInvestigator", "Synthetic reviewer")
def forbidden(*args, **kwargs):
    raise AssertionError("Outbound network disabled")
with TemporaryDirectory(prefix="w7-create-") as tmp, patch.object(socket.socket,"connect",forbidden), patch.object(socket.socket,"connect_ex",forbidden), patch.object(socket,"getaddrinfo",forbidden):
    mount = lambda: create_app(make_settings(Path(tmp), seed=False))
    app = mount()
    created = []
    with TestClient(app) as client:
        response = client.post("/api/v1/cases", json=doc, headers=lead)
        assert response.status_code == 201, response.text
        for record in writes:
            assert record["method"] == "POST" and record["path"] == f"/api/v1/cases/{case}/recommendations"
            response = client.post(record["path"], json=record["data"], headers=lead)
            assert response.status_code == 201, response.text
            d = response.json()
            assert d["status"] == "Draft" and d["body"] == record["data"]["body"]
            created.append(d["id"])
    app.state.db.engine.dispose()
    restored = mount()
    with TestClient(restored) as client:
        for rid, sent in zip(created, writes, strict=True):
            url = f"/api/v1/cases/{case}/recommendations/{rid}"
            r = client.get(url, headers=lead)
            assert r.status_code == 200 and r.json()["body"] == sent["data"]["body"]
            r = client.get(url + "/history", headers=lead)
            assert r.status_code == 200 and [event["action"] for event in r.json()] == ["safetyrec.create"]
    restored.state.db.engine.dispose()
print("PASS actual FastAPI + fresh SQLite: two DOM-captured requests stored verbatim as Draft; reopened body and exact create audit")
