"""App-level W9 synthetic write/reopen driver; one temporary SQLite file."""
from ast import literal_eval
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
from mcis_service.environment.models import EnvironmentObservationRow
from mcis_service.environment.router import router as environment

CASE = "synthetic-env-write-reopen"
OTHER = "synthetic-env-unrelated"
PREFIX = "/api/v1/cases/"
SUFFIX = "/environment-observations"
WRITE = PREFIX + CASE + SUFFIX
NOTE = " 合成原文，未估算来流。 "
RECORD = dict(caseId=CASE, observationId="SYN-W9-01", observedAtUtc=None,
              locationDescription=" 合成河段 S ", description=NOTE,
              sourceLabel=" 合成来源第 7 页 ", valueOrigin="Direct", currentSpeedKn=0)


def emit(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)


def headers(role):
    return {"X-MCIS-Role": role, "X-MCIS-Operator": "synthetic-ui"}


def app(db):
    a = FastAPI()
    a.state.db = db
    a.include_router(cases)
    a.include_router(environment)
    return a


def case(cid):
    return dict(caseId=cid, schemaVersion="1.0.0", title="合成环境记录验收",
                accidentType="Collision", caseEpochUtc="2026-01-01T00:00:00Z",
                incidentTimeUtc="2026-01-01T00:00:00Z",
                incidentLocation={"lonDeg": 0, "latDeg": 0},
                displayTimeZoneOffsetMinutes=0, isFictionalDemo=True)


def audit_check(db):
    with db.session() as s:
        rows = list(s.scalars(select(EnvironmentObservationRow)))
        assert len(rows) == 1
        assert rows[0].case_id == CASE and rows[0].key == RECORD["observationId"]
        assert rows[0].doc == RECORD
        entries = list(s.scalars(select(AuditEventRow).where(
            AuditEventRow.action == "environment.observation.create")))
        assert len(entries) == 1
        item = entries[0]
        assert item.case_id == CASE and item.entity_type == "environmentObservation"
        assert item.entity_id == RECORD["observationId"]
        assert item.role == "Investigator" and item.operator == "synthetic-ui"
        assert literal_eval(item.after) == RECORD
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
                    emit({"reopened": True, "auditRows": 1, "observationRows": 1})
                    continue
                if q == {"control": "negative-controls"}:
                    assert reopened
                    edited = {**RECORD, "description": "重号的不同说明，不可覆盖"}
                    duplicate = c.post(WRITE, json=edited, headers=headers("Investigator"))
                    public = c.post(WRITE, json={**RECORD, "observationId": "DENIED"}, headers=headers("Public"))
                    cross_case = c.post(PREFIX + OTHER + SUFFIX, json=RECORD, headers=headers("Investigator"))
                    assert duplicate.status_code == 409 and duplicate.json()["detail"]["code"] == "OBSERVATION_EXISTS"
                    assert public.status_code == 403
                    assert cross_case.status_code == 422 and cross_case.json()["detail"]["code"] == "CASE_MISMATCH"
                    audit_check(db)
                    emit({"duplicatesRejected": 409, "publicRejected": 403, "mixedCaseRejected": 422})
                    continue
                assert set(q) == {"method", "path", "role", "body"}
                assert q["role"] in ("Investigator", "Public")
                if q["method"] == "POST":
                    assert q["path"] == WRITE and q["role"] == "Investigator"
                    assert accepted_ui_writes == 0 and not reopened
                    assert q["body"] == RECORD, "Form must preserve text and explicit zero"
                    r = c.post(WRITE, json=q["body"], headers=headers(q["role"]))
                    assert r.status_code == 201 and r.json() == RECORD
                    accepted_ui_writes += 1
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


with TemporaryDirectory(prefix="w92-create-reopen-") as directory:
    exercise(Path(directory) / "records.db")
assert not Path(directory).exists()
