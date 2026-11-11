"""W6 独立验收：service colreg（GET / evaluate / PATCH 复核 / colreg.review 审计）。

依据：contracts/openapi.yaml（/cases/{caseId}/colreg、:evaluate、/colreg/checks/{checkId}）、
contracts/schemas/colreg.schema.json、audit-event.schema.json、common.schema.json#/$defs/problem。
测试数据只用虚构 Lily/Mary 与合成值；海力5 只做结构性只读检查，不跑 evaluate。
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import pytest

from conftest import HAILI, HAS_CORE, LILY, H
from schema_check import check as schema

L = f"/api/v1/cases/{LILY}"
H5 = f"/api/v1/cases/{HAILI}"
OP = "验收员·合成甲"
needs_core = pytest.mark.skipif(not HAS_CORE, reason="需要真实 dotnet 与预构建 mcis-core.dll（支持 MCIS_DOTNET/MCIS_CORE_DLL）")


def _ok(ref, doc):
    errs = schema(ref, doc)
    assert not errs, f"{ref}: {errs[:8]}"


def _colreg(client, base=L):
    r = client.get(f"{base}/colreg", headers=H())
    assert r.status_code == 200, r.text
    return r.json()


def _check(doc, cid):
    return next(c for c in doc["checks"] if c["checkId"] == cid)


def _reviews(client, cid=None, base=L):
    p = {"action": "colreg.review", "order": "asc", "limit": 500}
    if cid:
        p["entityId"] = cid
    r = client.get(f"{base}/audit", params=p, headers=H())
    assert r.status_code == 200, r.text
    return r.json()


def _patch(client, cid, body, role="Investigator", op=OP, base=L):
    return client.patch(f"{base}/colreg/checks/{cid}", json=body, headers=H(role, op))


# ---------------- 1. 复核：理由必填、错误体 ----------------

REASON_MISSING = [
    ("Rejected", None), ("Rejected", ""), ("Rejected", "   "), ("Rejected", "\t\n"), ("Rejected", "\u3000\u3000"),
    ("Modified", None), ("Modified", ""), ("Modified", "   "), ("Modified", "\t\n"), ("Modified", "\u3000"),
]


@pytest.mark.parametrize("status,note", REASON_MISSING)
def test_A1_reject_modify_without_reason_is_422(client, status, note):
    before = _check(_colreg(client), "CK-05")
    body = {"action": {"Confirmed": "confirm", "Rejected": "dismiss", "Modified": "modify"}[status]}
    if status == "Modified":
        body["verdict"] = "NeedsReview"
    if note is not None:
        body["reason"] = note
    r = _patch(client, "CK-05", body)
    assert r.status_code == 422, r.text
    err = r.json()
    _ok("common#/$defs/problem", err)
    assert err["code"] == "colreg_review_reason_required"
    # 被拒时不得改数据、不得写审计
    assert _check(_colreg(client), "CK-05") == before
    assert _reviews(client, "CK-05") == []


@pytest.mark.parametrize("note", [None, "", "核对合成 VDR 后确认"])
def test_A2_confirm_reason_optional(client, note):
    body = {"action": "confirm"}
    if note is not None:
        body["reason"] = note
    r = _patch(client, "CK-03", body)
    assert r.status_code == 200, r.text
    assert r.json()["reviewStatus"] == "Confirmed"
    assert len(_reviews(client, "CK-03")) == 1


def test_A3_modify_requires_verdict(client):
    r = _patch(client, "CK-05", {"action": "modify", "reason": "合成理由"})
    assert r.status_code == 422
    _ok("common#/$defs/problem", r.json())
    assert r.json()["code"] == "colreg_review_verdict_required"
    assert _reviews(client, "CK-05") == []


@pytest.mark.parametrize("body", [
    {"action": "draft", "reason": "x"},
    {"action": "approved", "reason": "x"},
    {"action": "modify", "verdict": "Bogus", "reason": "x"},
    {},
])
def test_A4_bad_body_is_422_problem(client, body):
    r = _patch(client, "CK-05", body)
    assert r.status_code == 422
    _ok("common#/$defs/problem", r.json())


def test_A5_unknown_check_404_problem(client):
    r = _patch(client, "CK-NOPE-999", {"action": "confirm"})
    assert r.status_code == 404
    _ok("common#/$defs/problem", r.json())


@pytest.mark.parametrize("role", ["ExternalExpert", "InterestedState", "AgentService", "Public"])
def test_A6_readonly_roles_cannot_review(client, role):
    r = _patch(client, "CK-05", {"action": "dismiss", "reason": "合成理由"}, role=role)
    assert r.status_code == 403, r.text
    assert _check(_colreg(client), "CK-05")["reviewStatus"] == "Draft"


def test_A7_confirm_must_not_change_verdict(client):
    """确认=接受原判定。带 verdict 应 422 colreg_review_verdict_not_allowed，不得改数据。"""
    before = _check(_colreg(client), "CK-05")
    r = _patch(client, "CK-05", {"action": "confirm", "verdict": "NotComplied"})
    assert r.status_code == 422, r.text
    _ok("common#/$defs/problem", r.json())
    assert r.json()["code"] == "colreg_review_verdict_not_allowed"
    assert _check(_colreg(client), "CK-05") == before
    assert _reviews(client, "CK-05") == []


def test_A8_reject_must_not_change_verdict(client):
    """驳回带 verdict 应 422 colreg_review_verdict_not_allowed，不得改判定。"""
    before = _check(_colreg(client), "CK-05")
    r = _patch(client, "CK-05", {"action": "dismiss", "verdict": "NotComplied", "reason": "合成理由"})
    assert r.status_code == 422, r.text
    _ok("common#/$defs/problem", r.json())
    assert r.json()["code"] == "colreg_review_verdict_not_allowed"
    assert _check(_colreg(client), "CK-05") == before
    assert _reviews(client, "CK-05") == []


# ---------------- 1b. 审计：操作人、时间、原值、新值、理由 ----------------

@pytest.mark.parametrize("status,verdict,reason", [
    ("Confirmed", None, "合成确认理由-α"),
    ("Rejected", None, "合成驳回理由-β"),
    ("Modified", "NeedsReview", "合成修改理由-γ"),
    ("Modified", "NotAssessable", "合成修改理由-δ"),
])
def test_B1_audit_has_who_when_before_after_reason(client, status, verdict, reason):
    cid = "CK-07"
    old = _check(_colreg(client), cid)
    t0 = datetime.now(timezone.utc) - timedelta(seconds=5)
    body = {"action": {"Confirmed": "confirm", "Rejected": "dismiss", "Modified": "modify"}[status], "reason": reason}
    if verdict:
        body["verdict"] = verdict
    r = _patch(client, cid, body)
    assert r.status_code == 200, r.text
    _ok("colreg#/$defs/check", r.json())
    evs = _reviews(client, cid)
    assert len(evs) == 1
    e = evs[0]
    _ok("audit-event", e)
    assert e["action"] == "colreg.review" and e["category"] == "Colreg"
    assert e["entityId"] == cid
    assert e["operator"] == OP
    ts = datetime.fromisoformat(e["utc"].replace("Z", "+00:00"))
    assert t0 <= ts <= datetime.now(timezone.utc) + timedelta(seconds=5)
    assert old["verdict"] in e["before"] and (old.get("reviewStatus") or "Draft") in e["before"]
    assert status in e["after"]
    if verdict:
        assert verdict in e["after"]
    assert reason in e["after"], "审计未记录理由"


def test_B2_long_reason_kept_whole_in_audit(client):
    """21:34 裁定：审计 after 摘要允许截断；落盘行 reason 键与复核历史保存全文（逐字相等）。"""
    import json
    reason = "合成理由" + "甲乙丙丁戊己庚辛壬癸" * 39
    r = _patch(client, "CK-08", {"action": "dismiss", "reason": reason})
    assert r.status_code == 200, r.text
    e = _reviews(client, "CK-08")[-1]
    assert len(e["after"]) <= 400  # 摘要允许截断
    line = json.loads(e["line"])
    assert line.get("reason") == reason, "落盘行 reason 未与理由全文逐字相等"
    hist = client.get(f"{L}/colreg/checks/CK-08/reviews", headers=H()).json()
    assert hist["history"][-1]["reason"] == reason, "复核历史未保存理由全文"


def test_B3_default_operator_when_header_missing(client):
    r = client.patch(f"{L}/colreg/checks/CK-09", json={"action": "confirm"}, headers={"X-MCIS-Role": "Investigator"})
    assert r.status_code == 200
    e = _reviews(client, "CK-09")[-1]
    assert e["operator"].strip(), "操作人为空"


def test_B4_sequential_reviews_chain_and_before_after_link(client):
    cid = "CK-10"
    steps = [({"action": "confirm"}, ), ({"action": "modify", "verdict": "Partial", "reason": "合成①"}, ),
             ({"action": "dismiss", "reason": "合成②"}, )]
    for (b,) in steps:
        assert _patch(client, cid, b).status_code == 200
    evs = _reviews(client, cid)
    assert len(evs) == 3
    assert "Confirmed" in evs[0]["after"] and "Confirmed" in evs[1]["before"]
    assert "verdict=Partial" in evs[1]["after"] and "verdict=Partial" in evs[2]["before"]
    allv = client.get(f"{L}/audit", params={"order": "asc", "limit": 500}, headers=H()).json()
    for e in allv:
        assert re.fullmatch(r"[0-9a-f]{64}", e["prevHash"])
    seqs = [e["seq"] for e in allv]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)


def test_B5_review_persisted_and_doc_valid(client):
    assert _patch(client, "CK-11", {"action": "modify", "verdict": "NeedsReview", "reason": "合成"}).status_code == 200
    doc = _colreg(client)
    _ok("colreg", doc)
    c = _check(doc, "CK-11")
    assert c["reviewStatus"] == "Modified" and c["verdict"] == "NeedsReview"


# ---------------- 2/4/8. GET colreg：字段、证据、合同 ----------------

@pytest.mark.parametrize("case", [LILY, HAILI])
def test_C1_get_colreg_contract_valid(client, case):
    doc = _colreg(client, f"/api/v1/cases/{case}")
    _ok("colreg", doc)
    assert doc["caseId"] == case
    assert "不作责任认定" in doc["disclaimer"]


@pytest.mark.parametrize("case", [LILY, HAILI])
def test_C2_bands_have_stage_doubt_status(client, case):
    doc = _colreg(client, f"/api/v1/cases/{case}")
    vids = {v["vesselId"] for v in client.get(f"/api/v1/cases/{case}/vessels", headers=H()).json()}
    assert doc["bands"]
    for b in doc["bands"]:
        assert b["dangerStage"] in ("None", "CloseQuarters", "ImmediateDanger")
        assert isinstance(b["doubt"], bool)
        assert set(b["vesselStatus"]) == vids, f"{b['bandId']} vesselStatus 未覆盖全部船舶"
        if b["doubt"]:
            assert (b.get("doubtReason") or "").strip(), f"{b['bandId']} 存疑但无理由"
        assert b["startTimeSec"] < b["endTimeSec"]


@pytest.mark.parametrize("case", [LILY, HAILI])
def test_C3_every_check_links_registered_evidence(client, case):
    base = f"/api/v1/cases/{case}"
    doc = _colreg(client, base)
    ev = {e["evidenceId"] for e in client.get(f"{base}/evidence", headers=H()).json()}
    for c in doc["checks"]:
        if c["verdict"] == "NotApplicable":
            continue
        assert c.get("evidenceIds"), f"{c['checkId']} 无证据链接"
        missing = set(c["evidenceIds"]) - ev
        assert not missing, f"{c['checkId']} 链到未登记证据 {missing}"


def test_C4_get_colreg_forbidden_for_public(client):
    r = client.get(f"{L}/colreg", headers=H("Public"))
    assert r.status_code in (403, 404)
    _ok("common#/$defs/problem", r.json())


# ---------------- 6. 海力5 种子：结构性只读检查（不抄原文） ----------------

TAG = re.compile(r"【(直接|推算)")


def test_D1_haili5_is_public_report_case(client):
    meta = next(c for c in client.get("/api/v1/cases", headers=H()).json() if c["caseId"] == HAILI)
    assert meta["isFictionalDemo"] is False
    lily = next(c for c in client.get("/api/v1/cases", headers=H()).json() if c["caseId"] == LILY)
    assert lily["isFictionalDemo"] is True


def test_D2_haili5_bands_tagged(client):
    for b in _colreg(client, H5)["bands"]:
        assert TAG.search(b.get("basis") or ""), f"{b['bandId']} basis 无【直接】/【推算】"


def test_D3_haili5_checks_tagged_and_sourced(client):
    for c in _colreg(client, H5)["checks"]:
        txt = (c.get("requiredAction") or "") + (c.get("actualAction") or "")
        assert TAG.search(txt), f"{c['checkId']} 无【直接】/【推算】"
        assert c.get("source") == "Seed" and c.get("evidenceIds")


def test_D4_haili5_tracks_tagged(client):
    tracks = client.get(f"{H5}/tracks", headers=H()).json()["tracks"]
    pts = [p for t in tracks for p in t["points"]]
    assert pts
    for p in pts:
        assert TAG.search(p.get("source") or ""), f"航迹点 {p['vesselId']}@{p['timeSec']} 无标注"


def test_D5_haili5_evidence_tagged(client):
    for e in client.get(f"{H5}/evidence", headers=H()).json():
        assert (e.get("source") or "").strip(), f"{e['evidenceId']} 无来源"
        assert TAG.search((e.get("note") or "") + (e.get("source") or "")), f"{e['evidenceId']} 无【直接】/【推算】"


# ---------------- 7. 只监听 127.0.0.1（静态） ----------------

def test_E1_entrypoint_binds_loopback_only():
    from conftest import ROOT
    main = (ROOT / "service/mcis_service/__main__.py").read_text(encoding="utf-8")
    assert re.search(r'host\s*=\s*"127\.0\.0\.1"', main)
    assert "0.0.0.0" not in main and '"::"' not in main
    vite = (ROOT / "web/vite.config.ts").read_text(encoding="utf-8")
    assert vite.count("host: '127.0.0.1'") >= 2 and "0.0.0.0" not in vite


# ---------------- evaluate（只对虚构 Lily/Mary，临时库） ----------------

@needs_core
@pytest.mark.parametrize("mode", ["nobody", "empty", "fields"])
def test_F1_evaluate_optional_body(client, mode):
    kw = {}
    if mode == "empty":
        kw["json"] = {}
    elif mode == "fields":
        kw["json"] = {"ownVesselId": "vessel_lily", "targetVesselId": "vessel_mary", "visibilityNm": 0.4,
                      "vesselsInSight": False, "inNarrowChannel": True}
    r = client.post(f"{L}/colreg:evaluate", headers=H(), **kw)
    assert r.status_code == 200, r.text
    doc = r.json()
    _ok("colreg", doc)
    assert doc["caseId"] == LILY and "不作责任认定" in doc["disclaimer"]
    assert doc["checks"] and all(c["reviewStatus"] == "Draft" and c["source"] == "RuleEngine" for c in doc["checks"])
    assert doc.get("runId"), "W6.2 evaluate must identify the new run"
    assert _colreg(client) == {k: v for k, v in doc.items() if k != "runId"}
    ev = client.get(f"{L}/audit", params={"action": "colreg.evaluate"}, headers=H()).json()
    assert ev and ev[-1]["category"] == "Colreg"


@needs_core
def test_F2_evaluate_vessel_status_object_form_per_openapi(client):
    """openapi：vesselStatus 为 object（按船 id 的状态序列 [{fromUtc,status}]）。"""
    body = {"vesselStatus": {"vessel_mary": [{"fromUtc": "2026-05-18T06:15:00Z", "status": "PowerDriven"},
                                             {"fromUtc": "2026-05-18T06:20:00Z", "status": "NotUnderCommand"}],
                             "vessel_lily": [{"fromUtc": "2026-05-18T06:15:00Z", "status": "PowerDriven"}]}}
    r = client.post(f"{L}/colreg:evaluate", json=body, headers=H())
    assert r.status_code == 200, f"按 openapi 形态提交被拒：{r.status_code} {r.text[:300]}"
    doc = r.json()
    _ok("colreg", doc)
    late = [b for b in doc["bands"] if b["startTimeSec"] >= 300]
    assert late and any(b["vesselStatus"].get("vessel_mary") == "NotUnderCommand" for b in late)


@needs_core
def test_F3_evaluate_checks_link_evidence(client):
    r = client.post(f"{L}/colreg:evaluate", json={"evidenceIds": ["EV-001"]}, headers=H())
    assert r.status_code == 200, r.text
    for c in r.json()["checks"]:
        if c["verdict"] != "NotApplicable":
            assert c.get("evidenceIds"), f"{c['checkId']} 规则引擎结论无证据链接"


@needs_core
def test_F4_evaluate_then_review_roundtrip(client):
    doc = client.post(f"{L}/colreg:evaluate", json={}, headers=H()).json()
    cid = doc["checks"][0]["checkId"]
    r = _patch(client, cid, {"action": "dismiss", "reason": "合成驳回"})
    assert r.status_code == 200 and r.json()["reviewStatus"] == "Rejected"
    _ok("colreg", _colreg(client))


@pytest.mark.parametrize("role", ["ExternalExpert", "Public"])
def test_F5_evaluate_forbidden_for_readonly(client, role):
    r = client.post(f"{L}/colreg:evaluate", json={}, headers=H(role))
    assert r.status_code in (403, 404)
    _ok("common#/$defs/problem", r.json())


def test_F6_evaluate_bad_body_422_problem(client):
    r = client.post(f"{L}/colreg:evaluate", json={"visibilityNm": "far"}, headers=H())
    assert r.status_code == 422
    _ok("common#/$defs/problem", r.json())


@needs_core
def test_F7_evaluate_vessel_status_list_form_impl(client):
    """21:34 裁定：旧列表格式按裁定 1 返回 422（不再接受 list[{vesselId,timeSec,status}]）。"""
    body = {"vesselStatus": [{"vesselId": "vessel_mary", "timeSec": 0, "status": "PowerDriven"},
                             {"vesselId": "vessel_mary", "timeSec": 300, "status": "NotUnderCommand"},
                             {"vesselId": "vessel_lily", "timeSec": 0, "status": "PowerDriven"}]}
    r = client.post(f"{L}/colreg:evaluate", json=body, headers=H())
    assert r.status_code == 422, r.text
    _ok("common#/$defs/problem", r.json())
    assert r.json()["code"] == "VALIDATION_ERROR"
