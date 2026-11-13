import pytest

from .conftest import C, H, HAS_DOTNET, CASE


def test_agent_registry_not_connected(client):
    ags = client.get("/api/v1/agents", headers=H()).json()
    assert len(ags) == 6 and all(a["status"] == "not_connected" for a in ags)


def test_agent_draft_requires_citations_and_human_review(client):
    base = {"agent": "timeline", "kind": "timeline_anchor", "targetEntityType": "timelineEvent", "targetEntityId": None,
            "payload": {"timeSec": 610, "title": "拖轮抵达（虚构）", "kind": "Event"}}
    assert client.post(f"{C}/agents/drafts", json={**base, "citations": []}, headers=H("AgentService")).status_code == 422
    r = client.post(f"{C}/agents/drafts", json={**base, "citations": [{"evidenceId": "EV-003", "quote": "AIS"}]},
                    headers=H("AgentService"))
    assert r.status_code == 201 and r.json()["status"] == "PendingReview"
    did = r.json()["draftId"]
    assert client.post(f"{C}/agents/drafts/{did}/review", json={"decision": "Confirmed"}, headers=H("AgentService")).status_code == 403
    ok = client.post(f"{C}/agents/drafts/{did}/review", json={"decision": "Confirmed", "note": "核对 AIS"}, headers=H()).json()
    assert ok["status"] == "Confirmed" and ok["effect"].startswith("新增时间线事件")
    assert client.post(f"{C}/agents/drafts/{did}/review", json={"decision": "Confirmed"}, headers=H()).status_code == 409
    assert any(e["title"] == "拖轮抵达（虚构）" for e in client.get(f"{C}/timeline", headers=H()).json()["events"])


def test_agent_review_preserves_signed_seed_statement(client):
    before = client.get(f"{C}/interviews/IR-03", headers=H("LeadInvestigator")).json()
    r = client.post(f"{C}/agents/drafts/AD-001/review", json={"decision": "Rejected", "note": "证据不足"}, headers=H("LeadInvestigator"))
    assert r.status_code == 409 and r.json()["code"] == "INTERVIEW_SIGNED", r.text
    assert client.get(f"{C}/interviews/IR-03", headers=H("LeadInvestigator")).json() == before
    drafts = client.get(f"{C}/agents/drafts", headers=H("LeadInvestigator")).json()
    assert next(d for d in drafts if d["draftId"] == "AD-001")["status"] == "PendingReview"


def test_colreg_seed_and_evaluate(client):
    c = client.get(f"{C}/colreg", headers=H()).json()
    assert [b["bandId"] for b in c["bands"]] == ["B1", "B2", "B3", "B4", "B5"] and len(c["checks"]) == 24
    r = client.post(f"{C}/colreg:evaluate", json={}, headers=H())
    if not HAS_DOTNET:
        assert r.status_code == 501
        pytest.skip("需要 ~/.dotnet 才能调用 mcis-core colreg")
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["caseId"] == CASE and doc["bands"] and doc["checks"]
    assert all(b["situation"] != "NoCollisionRisk" for b in doc["bands"])
    assert all(ch["verdict"] not in ("Satisfied", "NotSatisfied") for ch in doc["checks"])
    assert all(ch.get("reviewStatus") == "Draft" for ch in doc["checks"])
    stored = client.get(f"{C}/colreg", headers=H()).json()
    assert stored["bands"][0]["bandId"] == doc["bands"][0]["bandId"]
    chk = doc["checks"][0]["checkId"]
    p = client.patch(f"{C}/colreg/checks/{chk}", json={"action": "confirm", "reason": "人工确认"}, headers=H())
    assert p.status_code == 200 and p.json()["reviewStatus"] == "Confirmed"


@pytest.mark.skipif(not HAS_DOTNET, reason="需要 ~/.dotnet")
def test_core_cpa_head_on(client):
    r = client.post("/api/v1/core/cpa", json={"pairs": [{
        "own": {"vesselId": "A", "eastNm": 0, "northNm": 0, "speedKn": 10, "courseDeg": 0},
        "target": {"vesselId": "B", "eastNm": 0, "northNm": 5, "speedKn": 10, "courseDeg": 180}}]}, headers=H()).json()
    res = r["result"]["results"][0]
    assert r["ok"] and res["dcpaNm"] == pytest.approx(0, abs=1e-9) and res["tcpaMin"] == pytest.approx(15)
    assert res["riskLevel"] in ("Safe", "Warning", "Danger")
    assert client.get("/api/v1/core/version", headers=H()).json()["result"]["coreVersion"].startswith("mcis-core/")


@pytest.mark.skipif(not HAS_DOTNET, reason="需要 ~/.dotnet")
def test_case_cpa_series_closes_to_collision(client):
    s = client.get(f"{C}/cpa", params={"stepSec": 60}, headers=H()).json()
    pts = s["results"]
    d = {p["timeSec"]: p["currentDistanceNm"] for p in pts}
    assert d[0] > 2.5 and d[540] < 0.1
    assert all(d[t] >= d[t + 60] for t in range(0, 540, 60))


def test_sim_state_seek_commands(client):
    st = client.put(f"{C}/sim/state", json={"simTimeSec": 120, "playing": True, "rate": 4}, headers=H()).json()
    assert st["utc"] == "2026-05-18T06:17:00Z" and st["source"] == "unity"
    assert client.get(f"{C}/sim/state").json()["simTimeSec"] == 120
    cmd = client.post(f"{C}/sim/seek", json={"simTimeSec": 540, "reason": "碰撞时刻"}, headers=H()).json()
    assert cmd["type"] == "seek" and cmd["seq"] == 1
    client.post(f"{C}/sim/commands", json={"type": "pause"}, headers=H())
    assert [c["type"] for c in client.get(f"{C}/sim/commands", params={"afterSeq": 1}).json()["commands"]] == ["pause"]
    assert client.post(f"{C}/sim/seek", json={"simTimeSec": 99999}, headers=H()).status_code == 422
    assert client.get(f"{C}/audit", params={"action": "sim.seek"}, headers=H()).json()

