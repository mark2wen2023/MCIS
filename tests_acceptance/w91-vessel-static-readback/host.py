"""W9.1 synthetic static-parameter driver; one temporary SQLite file."""
from base64 import b64encode
from hashlib import sha256, sha1
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

ROOT = Path(os.environ["MCIS_PINNED_SOURCE"])
if not __debug__:
    raise SystemExit("Python assertion checks must be enabled")
for name, expected in json.loads((ROOT / "pins.json").read_text()).items():
    data = (ROOT / name).read_bytes()
    assert sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == expected
sys.path.insert(0, str(ROOT / "service"))
from mcis_service.audit import service as audit
from mcis_service.audit.models import AuditEventRow
from mcis_service.cases.router import router as cases
from mcis_service.db import Base, Database
from mcis_service.cases.models import VesselRow

CASE = "synthetic-vessel-readback"
OTHER = "synthetic-vessel-unrelated"
PREFIX = "/api/v1/cases/"
SUFFIX = "/vessels"
WRITE = PREFIX + CASE + SUFFIX
RECORD = dict(caseId=CASE, vesselId="SYN-W91-01", name="合成登记船 S",
              loaM=87.25, draftForeM=0, draftAftM=3.4,
              parameterSources={
                  "loaM": {"sourceLabel": "合成总布置图第 7 页", "kind": "Direct"},
                  "draftForeM": {"sourceLabel": "合成估算说明第 2 行", "kind": "Estimated"},
                  "draftAftM": {"sourceLabel": "合成测量点换算表第 4 行", "kind": "Derived"},
              })


def emit(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)


def headers(role):
    return {"X-MCIS-Role": role, "X-MCIS-Operator": "synthetic-ui"}


def app(db):
    a = FastAPI()
    a.state.db = db
    a.include_router(cases)
    return a


def case(cid):
    return dict(caseId=cid, schemaVersion="1.0.0", title="合成船舶参数验收",
                accidentType="Collision", caseEpochUtc="2026-01-01T00:00:00Z",
                incidentTimeUtc="2026-01-01T00:00:00Z",
                incidentLocation={"lonDeg": 0, "latDeg": 0},
                displayTimeZoneOffsetMinutes=0, isFictionalDemo=True)


def audit_check(db):
    with db.session() as s:
        rows = list(s.scalars(select(VesselRow)))
        assert len(rows) == 1
        assert rows[0].case_id == CASE and rows[0].key == RECORD["vesselId"]
        assert rows[0].doc == RECORD
        entries = list(s.scalars(select(AuditEventRow).where(
            AuditEventRow.action == "vessel.create")))
        assert len(entries) == 1
        item = entries[0]
        assert item.case_id == CASE and item.entity_type == "vessel"
        assert item.entity_id == RECORD["vesselId"]
        assert item.role == "Investigator" and item.operator == "synthetic-ui"
        assert "SYN-W91-01" in item.after and "87.25" in item.after
        assert json.loads(item.line)["after"] == item.after
        assert audit.verify_chain(audit.all_lines(s, CASE))["valid"] is True


def exercise(db_path):
    db = Database("sqlite:///" + str(db_path))
    a = app(db)
    accepted_ui_writes = 0
    reopened = False
    try:
        Base.metadata.create_all(db.engine)
        with TestClient(a) as c:
            for cid in (CASE, OTHER):
                r = c.post(PREFIX.rstrip("/"), json=case(cid), headers=headers("Investigator"))
                assert r.status_code == 201, r.status_code
            emit({"ready": True})
            for line in sys.stdin:
                q = json.loads(line)
                if q == {"control": "reopen"}:
                    assert not reopened and accepted_ui_writes == 1
                    audit_check(db)
                    db.engine.dispose()
                    db = Database("sqlite:///" + str(db_path))
                    a.state.db = db
                    reopened = True
                    audit_check(db)
                    emit({"reopened": True, "auditRows": 1, "vesselRows": 1})
                    continue
                assert set(q) == {"method", "path", "role", "body"}
                assert q["role"] in ("Investigator", "Public")
                if q["method"] == "POST":
                    assert q["path"] == WRITE and q["role"] == "Investigator"
                    if accepted_ui_writes == 0:
                        assert q["body"] == RECORD and not reopened
                        r = c.post(WRITE, json=q["body"], headers=headers(q["role"]))
                        assert r.status_code == 201 and r.json() == RECORD
                        accepted_ui_writes += 1
                    else:
                        assert not reopened
                        assert q["body"] == {**RECORD, "loaM": 91.5}
                        r = c.post(WRITE, json=q["body"], headers=headers(q["role"]))
                        assert r.status_code == 409 and r.json()["detail"]["code"] == "VESSEL_EXISTS"
                        audit_check(db)
                else:
                    assert q["method"] == "GET" and q["body"] is None
                    assert q["path"] in {PREFIX + cid + suffix for cid in (CASE, OTHER)
                                         for suffix in ("", SUFFIX)}
                    r = c.get(q["path"], headers=headers(q["role"]))
                    assert r.status_code == 200
                    if q["path"] == WRITE:
                        assert r.json() == ([RECORD] if accepted_ui_writes else [])
                    if q["path"] == PREFIX + OTHER + SUFFIX:
                        assert r.json() == []
                emit({"path": q["path"], "method": q["method"], "status": r.status_code,
                      "bodyBase64": b64encode(r.content).decode(), "sha256": sha256(r.content).hexdigest()})
        assert accepted_ui_writes == 1 and reopened
    finally:
        db.engine.dispose()


with TemporaryDirectory(prefix="w91-static-readback-") as directory:
    exercise(Path(directory) / "records.db")
assert not Path(directory).exists()
