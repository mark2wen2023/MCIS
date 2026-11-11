"""W6：COLREG 接口、人工复核审计、海力5 真实案例播种。"""
from __future__ import annotations

import pytest

from mcis_service.common import contracts

from .conftest import C, CASE, H, HAS_DOTNET

HAILI = "CASE-2025-HAILI5-WANA17"
H5 = f"/api/v1/cases/{HAILI}"


def _ok(ref, doc):
    errs = contracts.errors(ref, doc)
    assert not errs, f"{ref}: {errs[:5]}"


def test_lily_mary_colreg_has_w1_fields(client):
    c = client.get(f"{C}/colreg", headers=H()).json()
    _ok("colreg", c)
    assert "仅作" in c["disclaimer"] and "责任认定" in c["disclaimer"]
    assert [b["bandId"] for b in c["bands"]] == ["B1", "B2", "B3", "B4", "B5"]
    assert len(c["checks"]) == 24
    stages = {b["bandId"]: b["dangerStage"] for b in c["bands"]}
    assert stages["B4"] == "ImmediateDanger" and stages["B2"] == "CloseQuarters"
    assert all("doubt" in b and "vesselStatus" in b for b in c["bands"])
    assert all(b["vesselStatus"]["vessel_lily"] == "PowerDriven" for b in c["bands"])
    ev_linked = [ch for ch in c["checks"] if ch.get("evidenceIds")]
    assert ev_linked and all(ch["evidenceIds"] for ch in ev_linked)


def test_review_confirm_reject_modify_writes_audit(client):
    c = client.get(f"{C}/colreg", headers=H()).json()
    a, b, d = c["checks"][0]["checkId"], c["checks"][1]["checkId"], c["checks"][2]["checkId"]
    old_a = c["checks"][0]["verdict"]

    ok = client.patch(f"{C}/colreg/checks/{a}", json={"action": "confirm", "reason": "核对 VDR 后确认"},
                      headers=H(operator="调查员 A"))
    assert ok.status_code == 200 and ok.json()["reviewStatus"] == "Confirmed"

    bad = client.patch(f"{C}/colreg/checks/{b}", json={"action": "dismiss"}, headers=H())
    assert bad.status_code == 422 and bad.json()["code"] == "colreg_review_reason_required"

    rej = client.patch(f"{C}/colreg/checks/{b}", json={"action": "dismiss", "reason": "证据不足以维持原判定"},
                       headers=H(operator="调查员 A"))
    assert rej.status_code == 200 and rej.json()["reviewStatus"] == "Rejected"

    miss = client.patch(f"{C}/colreg/checks/{d}", json={"action": "modify", "reason": "改判"}, headers=H())
    assert miss.status_code == 422 and miss.json()["code"] == "colreg_review_verdict_required"

    mod = client.patch(f"{C}/colreg/checks/{d}",
                       json={"action": "modify", "verdict": "NeedsReview", "reason": "规则允许裁量，改需研判"},
                       headers=H(operator="调查员 A"))
    assert mod.status_code == 200
    assert mod.json()["reviewStatus"] == "Modified" and mod.json()["verdict"] == "NeedsReview"

    evs = client.get(f"{C}/audit", params={"action": "colreg.review", "order": "asc"}, headers=H()).json()
    by_id = {e["entityId"]: e for e in evs}
    assert set(by_id) >= {a, b, d}
    for eid, ev in (("CK 确认", by_id[a]), ("驳回", by_id[b]), ("修改", by_id[d])):
        assert ev["operator"] == "调查员 A" and ev["utc"] and ev["before"] and ev["after"]
        assert "reviewStatus=" in ev["before"] and "reviewStatus=" in ev["after"]
    assert f"verdict={old_a}" in by_id[a]["before"]
    assert "reviewStatus=Confirmed" in by_id[a]["after"] and "reason=核对 VDR 后确认" in by_id[a]["after"]
    assert "reviewStatus=Rejected" in by_id[b]["after"] and "证据不足以维持原判定" in by_id[b]["after"]
    assert "verdict=NeedsReview" in by_id[d]["after"] and "改需研判" in by_id[d]["after"]
    assert by_id[a]["command"].startswith("确认")
    assert by_id[b]["command"].startswith("驳回")
    assert by_id[d]["command"].startswith("修改")


def test_review_unknown_check_and_forbidden(client):
    assert client.patch(f"{C}/colreg/checks/CK-NOPE", json={"action": "confirm"}, headers=H()).status_code == 404
    r = client.patch(f"{C}/colreg/checks/CK-01", json={"action": "confirm"}, headers=H("Public"))
    assert r.status_code in (403, 404)


def test_haili5_case_seeded_and_colreg_sourced(client):
    cases = client.get("/api/v1/cases", headers=H()).json()
    ids = {c["caseId"] for c in cases}
    assert CASE in ids and HAILI in ids
    meta = next(c for c in cases if c["caseId"] == HAILI)
    assert meta["isFictionalDemo"] is False

    case = client.get(H5, headers=H()).json()
    _ok("case", case)
    assert case["isFictionalDemo"] is False
    assert case["incidentTimeUtc"] == "2025-10-25T11:54:32Z"
    assert "公开报告" in case["summaryNotes"] or "reports/haili5" in case["summaryNotes"]

    vs = client.get(f"{H5}/vessels", headers=H()).json()
    assert {v["vesselId"] for v in vs} == {"vessel_haili5", "vessel_wanhai_a17"}
    for v in vs:
        _ok("vessel", v)

    tracks = client.get(f"{H5}/tracks", headers=H()).json()["tracks"]
    by = {t["vesselId"]: t["points"] for t in tracks}
    assert len(by["vessel_haili5"]) == 5 and len(by["vessel_wanhai_a17"]) == 2
    for pts in by.values():
        for p in pts:
            _ok("track-point", p)
            assert "【直接】" in p["source"] and ("p" in p["source"] or "图" in p["source"])

    ev = client.get(f"{H5}/evidence", headers=H()).json()
    eids = {e["evidenceId"] for e in ev}
    assert {"EV-101", "EV-102", "EV-103", "EV-104", "EV-105", "EV-106"} <= eids
    for e in ev:
        _ok("evidence-item", e)
        assert "报告" in (e.get("source") or "") or "报告" in (e.get("note") or "") or "reports/haili5" in (e.get("note") or "")

    doc = client.get(f"{H5}/colreg", headers=H()).json()
    _ok("colreg", doc)
    assert "责任认定" in doc["disclaimer"]
    assert [b["bandId"] for b in doc["bands"]] == ["HL-B1", "HL-B2", "HL-B3", "HL-B4"]
    b2 = next(b for b in doc["bands"] if b["bandId"] == "HL-B2")
    assert b2["doubt"] is True and b2["dangerStage"] == "CloseQuarters"
    assert b2["vesselStatus"]["vessel_haili5"] == "NotUnderCommand"
    assert b2["giveWayVesselId"] == "vessel_wanhai_a17"
    b3 = next(b for b in doc["bands"] if b["bandId"] == "HL-B3")
    assert b3["situation"] == "ImmediateDanger" and b3["dangerStage"] == "ImmediateDanger"

    verdicts = {ch["checkId"]: ch for ch in doc["checks"]}
    assert verdicts["HL-CK-01"]["verdict"] == "NotComplied"  # A17 R5
    assert verdicts["HL-CK-02"]["verdict"] == "NotComplied"  # A17 R8
    assert verdicts["HL-CK-03"]["verdict"] == "NotAssessable"
    assert verdicts["HL-CK-04"]["verdict"] == "NeedsReview"
    assert all(ch["evidenceIds"] for ch in doc["checks"])
    assert all(ch["source"] == "Seed" and ch["reviewStatus"] == "Draft" for ch in doc["checks"])
    # 每条核查都能链到已登记证据
    ev_set = {e["evidenceId"] for e in ev}
    for ch in doc["checks"]:
        assert set(ch["evidenceIds"]) <= ev_set


def test_haili5_review_audit_roundtrip(client):
    chk = "HL-CK-04"
    r = client.patch(f"{H5}/colreg/checks/{chk}",
                     json={"action": "modify", "verdict": "NotComplied",
                           "reason": "按 R18(a)(ii) 认定 A17 未及时让路"},
                     headers=H(operator="调查员 A"))
    assert r.status_code == 200 and r.json()["verdict"] == "NotComplied"
    evs = client.get(f"{H5}/audit", params={"action": "colreg.review", "entityId": chk}, headers=H()).json()
    assert evs and evs[-1]["operator"] == "调查员 A"
    assert "NeedsReview" in evs[-1]["before"] and "NotComplied" in evs[-1]["after"]
    assert "R18(a)(ii)" in evs[-1]["after"]
    stored = client.get(f"{H5}/colreg", headers=H()).json()
    item = next(c for c in stored["checks"] if c["checkId"] == chk)
    assert item["reviewStatus"] == "Modified" and item["verdict"] == "NotComplied"


@pytest.mark.skipif(not HAS_DOTNET, reason="需要 ~/.dotnet 才能调用 mcis-core colreg")
def test_evaluate_still_returns_draft(client):
    r = client.post(f"{C}/colreg:evaluate", json={}, headers=H())
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc.pop("runId")          # W6.2：响应带本次新建版本 id
    _ok("colreg", doc)
    assert all(ch.get("reviewStatus") == "Draft" for ch in doc["checks"])
    assert all(b.get("dangerStage") in ("None", "CloseQuarters", "ImmediateDanger") for b in doc["bands"])
