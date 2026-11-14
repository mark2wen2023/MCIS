import json

import pytest
from sqlalchemy import text

from mcis_service.common.csjson import ZERO_HASH, sha256_hex

from .conftest import C, H


def test_chain_valid_and_format(client):
    verified = client.get(f"{C}/audit:verify", headers=H())
    assert verified.status_code == 200, verified.text
    v = verified.json()
    assert v["valid"] and v["count"] > 40
    # Seed audit includes protected recommendation/consultation originals.
    # Synthetic role headers exercise policy only; they are not authenticated SSO.
    response = client.get(f"{C}/audit", params={"limit": 2000},
                          headers=H("LeadInvestigator"))
    assert response.status_code == 200, response.text
    ev = response.json()
    assert [e["seq"] for e in ev] == list(range(1, len(ev) + 1))
    assert ev[0]["prevHash"] == ZERO_HASH
    for a, b in zip(ev, ev[1:]):
        assert b["prevHash"] == sha256_hex(a["line"].encode("utf-8"))
        assert a["utc"] <= b["utc"], (a["seq"], a["utc"], b["utc"])
    keys = list(json.loads(ev[0]["line"]))
    assert keys[:7] == ["utc", "operator", "action", "category", "command", "before", "after"]
    assert keys[-1] == "prev"


def test_every_write_is_audited(client):
    n0 = client.get(f"{C}/audit:verify", headers=H()).json()["count"]
    client.patch(f"{C}/conflicts/C-02", json={"note": "补充"}, headers=H())
    client.post(f"{C}/sim/seek", json={"simTimeSec": 300}, headers=H())
    client.post(f"{C}/timeline/events", json={"timeSec": 1, "title": "t", "kind": "Event"}, headers=H())
    n1 = client.get(f"{C}/audit:verify", headers=H()).json()["count"]
    assert n1 == n0 + 3


@pytest.mark.parametrize("sql", ["UPDATE audit_events SET operator='x' WHERE seq=1",
                                 "DELETE FROM audit_events WHERE seq=1",
                                 "UPDATE custody_events SET detail='x' WHERE seq=1",
                                 "DELETE FROM custody_events"])
def test_append_only_triggers(app, client, sql):
    with app.state.db.engine.begin() as conn:
        with pytest.raises(Exception, match="append-only"):
            conn.execute(text(sql))


def test_tamper_detected_by_verify():
    from mcis_service.audit.service import verify_chain
    lines = ['{"utc":"2026-01-01T00:00:00Z","seq":1,"prev":"' + ZERO_HASH + '"}']
    lines.append('{"utc":"2026-01-01T00:00:01Z","seq":2,"prev":"' + sha256_hex(lines[0].encode()) + '"}')
    assert verify_chain(lines)["valid"]
    bad = [lines[0].replace("00:00:00", "00:00:09"), lines[1]]
    r = verify_chain(bad)
    assert not r["valid"] and r["brokenAt"] == 2


def test_external_cannot_read_audit(client):
    assert client.get(f"{C}/audit", headers=H("ExternalExpert")).status_code == 403


def test_investigator_can_verify_but_not_read_protected_seed_audit(client):
    before = client.get(f"{C}/audit:verify", headers=H())
    assert before.status_code == 200, before.text
    assert before.json()["valid"]
    denied = client.get(f"{C}/audit", params={"limit": 2000}, headers=H())
    assert denied.status_code == 403, denied.text
    assert denied.json()["code"] == "FORBIDDEN"
    assert "no-store" in denied.headers["cache-control"]
    assert "line" not in denied.json() and "events" not in denied.json()
    after = client.get(f"{C}/audit:verify", headers=H())
    assert after.status_code == 200, after.text
    assert after.json() == before.json()
