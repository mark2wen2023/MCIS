"""W7 synthetic positive business receipt: registered handlers, local SQLite, no ASGI app."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import quote

CASE_ID = "SYN-W7-AGREED-001"
OPERATOR = "合成首席调查员"
START = datetime(2026, 2, 1, 8, tzinfo=timezone.utc)
OPENED = "2026-02-01T08:00:00Z"
DEADLINE = "2026-03-18T08:00:00Z"
ROUTE_PATH = "/api/v1/cases/{case_id}/consultation/rounds"
SOURCE_MANIFEST = Path(__file__).with_name("agreed_deadline_sources.sha1")


def verify_source(root):
    """Import only from the exact source/schema closure, not a live checkout or app."""
    if root.is_symlink() or not root.is_dir():
        raise SystemExit("Use the plain isolated source directory described in the README.")
    expected = {name: sha for sha, name in (line.split() for line in SOURCE_MANIFEST.read_text().splitlines())}
    entries = list(root.rglob("*"))
    if any(entry.is_symlink() or not (entry.is_dir() or entry.is_file()) for entry in entries):
        raise SystemExit("Isolated source closure contains an unexpected file type.")
    if {str(p.relative_to(root)) for p in entries if p.is_file()} != expected.keys():
        raise SystemExit("Isolated source closure does not match the manifest.")
    for relative, expected_sha in expected.items():
        raw = (root / relative).read_bytes()
        header = f"blob {len(raw)}\0".encode("ascii")
        if hashlib.sha1(header + raw).hexdigest() != expected_sha:
            raise SystemExit(f"Pinned source blob differs: {relative}")
    if any(name == "mcis_service" or name.startswith("mcis_service.") for name in sys.modules):
        raise SystemExit("Unexpected MCIS import before source isolation.")
    sys.path.insert(0, str(root / "service"))


def run():
    from starlette.requests import Request

    from mcis_service.audit import service as audit
    from mcis_service.audit.models import AuditEventRow
    from mcis_service.cases.models import CaseRow
    from mcis_service.common import contracts
    from mcis_service.common.context import get_ctx
    from mcis_service.db import Base, Database, put_doc
    from mcis_service.recommendations import router as consultation
    from mcis_service.recommendations.models import ConsultationRoundRow
    from mcis_service.redaction.models import AccessPolicyRow

    post, = [r for r in consultation.router.routes if r.path == ROUTE_PATH and r.methods == {"POST"}]
    get, = [r for r in consultation.router.routes if r.path == ROUTE_PATH and r.methods == {"GET"}]
    assert post.status_code == 201 and post.endpoint is consultation.open_round
    assert get.endpoint is consultation.list_rounds

    def context(db):
        scope = {
            "type": "http", "headers": [
                (b"x-mcis-role", b"LeadInvestigator"),
                (b"x-mcis-operator", quote(OPERATOR).encode("ascii")),
            ],
            "app": SimpleNamespace(state=SimpleNamespace(db=db)),
        }
        return get_ctx(Request(scope))

    expected_fields = {
        "roundNo": 1, "caseId": CASE_ID, "draftVersion": "synth-v1", "openedUtc": OPENED,
        "deadlineUtc": DEADLINE, "isAgreedDeadline": True, "draftSha256": "",
        "isClosed": False, "closedUtc": None, "parties": [{"partyId": "F1", "name": "虚构方"}],
        "replies": [], "waivers": [], "comments": [], "allReplied": False,
    }

    with tempfile.TemporaryDirectory(prefix="mcis-w7-agreed-db-") as tmp:
        path = Path(tmp) / "synthetic.sqlite3"
        assert not path.exists()
        url = f"sqlite:///{path}"
        db = Database(url)
        try:
            # Use the real model definitions and DB sessions, not create_app or a seed hook.
            Base.metadata.create_all(db.engine, tables=[
                CaseRow.__table__, AccessPolicyRow.__table__,
                ConsultationRoundRow.__table__, AuditEventRow.__table__,
            ])
            doc = {
                "caseId": CASE_ID, "schemaVersion": "1.0.0", "title": "仅合成征求意见案",
                "accidentType": "Collision", "incidentTimeUtc": "2026-01-15T00:00:00Z",
                "caseEpochUtc": "2026-01-15T00:00:00Z", "displayTimeZoneOffsetMinutes": 480,
                "incidentLocation": {"lonDeg": 0, "latDeg": 0}, "isFictionalDemo": True,
            }
            contracts.validate("case", doc)
            with db.session() as s:
                put_doc(s, CaseRow, CASE_ID, CASE_ID, doc)
            ctx = context(db)
            with patch.object(consultation, "now_utc", return_value=START), patch.object(audit, "now_utc", return_value=START):
                assert get.endpoint(CASE_ID, ctx) == []
                with db.session() as s:
                    assert audit.list_events(s, CASE_ID) == []
                body = consultation.RoundIn.model_validate({
                    "draftVersion": "synth-v1", "parties": [{"partyId": "F1", "name": "虚构方"}],
                    "draftSha256": "", "days": 45, "isAgreedDeadline": True,
                })
                written = post.endpoint(CASE_ID, body, ctx)
                assert {key: written[key] for key in expected_fields} == expected_fields
                assert written["daysRemaining"] == 45
                assert [party["status"] for party in written["partyStatus"]] == ["Pending"]
        finally:
            db.engine.dispose()
        assert path.is_file() and path.stat().st_size > 0

        # Reopen the same persisted SQLite file with a new engine and fresh request context.
        reopened = Database(url)
        try:
            with patch.object(consultation, "now_utc", return_value=START + timedelta(days=2)):
                recovered, = get.endpoint(CASE_ID, context(reopened))
            assert {key: recovered[key] for key in expected_fields} == expected_fields
            assert recovered["daysRemaining"] == 43
            assert recovered["partyStatus"] == written["partyStatus"]
            with reopened.session() as s:
                event, = audit.list_events(s, CASE_ID)
                lines = audit.all_lines(s, CASE_ID)
                assert s.query(AccessPolicyRow).count() == 0, "test must use unchanged default policy"
            assert (event["caseId"], event["category"], event["action"], event["entityType"],
                    event["entityId"], event["seq"], event["operator"], event["role"], event["utc"]) == (
                CASE_ID, "Consultation", "consultation.open", "consultationRound", "1", 1, OPERATOR,
                "LeadInvestigator", OPENED,
            )
            assert f"期限={DEADLINE}" in event["after"]
            assert "（商定）" in event["after"] and "默认 30 天" not in event["after"]
            assert lines == [event["line"]] and event["prevHash"] == "0" * 64
            chain = audit.verify_chain(lines)
            assert chain["valid"] and chain["count"] == 1
            result = {
                "caseId": CASE_ID, "days": 45, "isAgreedDeadline": recovered["isAgreedDeadline"],
                "openedUtc": OPENED, "deadlineUtc": DEADLINE, "daysRemainingAfterReopen": 43,
                "persistedRounds": 1, "auditEvents": 1, "auditChainValid": True,
                "httpStarted": False, "externalDelivery": False,
            }
        finally:
            reopened.engine.dispose()
    assert not path.exists()
    assert "mcis_service.main" not in sys.modules and "mcis_service.models_registry" not in sys.modules
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    if not __debug__ or not sys.flags.isolated or not sys.dont_write_bytecode:
        raise SystemExit("Run with Python -I -B and without -O.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    verify_source(parser.parse_args().source_root.absolute())
    run()
