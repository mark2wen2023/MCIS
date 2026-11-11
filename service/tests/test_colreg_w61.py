"""W6.1：按 DEFECTS/W6.md 文末 12 条裁定逐条测试（只用临时库；非虚构案例用合成数据模拟，不对海力5 跑 evaluate）。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mcis_service.cases.models import CaseRow
from mcis_service.colreg import router as colreg_router
from mcis_service.colreg.models import ColregAnalysisRow
from mcis_service.common import contracts
from mcis_service.db import get_doc, put_doc
from mcis_service.main import create_app

from .conftest import C, CASE, H, HAS_DOTNET, make_settings

HAILI = "CASE-2025-HAILI5-WANA17"
H5 = f"/api/v1/cases/{HAILI}"
FAKE_CORE = str(Path(__file__).with_name("fake_core_colreg.py"))
TAG = ("【直接】", "【推算】", "【估计】")


def _ok(ref, doc):
    errs = contracts.errors(ref, doc)
    assert not errs, f"{ref}: {errs[:5]}"


@pytest.fixture()
def fapp(tmp_path):
    st = make_settings(tmp_path)
    st.core_cmd = FAKE_CORE
    return create_app(st)


@pytest.fixture()
def fc(fapp):
    with TestClient(fapp) as c:
        yield c


def _make_nonfictional(app, case_id=CASE):
    """合成“非虚构”案例：把临时库里的 Lily/Mary 标成 isFictionalDemo=false（不碰海力5）。"""
    with app.state.db.session() as s:
        doc = get_doc(s, CaseRow, case_id, case_id)
        doc["isFictionalDemo"] = False
        put_doc(s, CaseRow, case_id, case_id, doc)


def _check(doc, cid):
    return next(c for c in doc["checks"] if c["checkId"] == cid)


def _reviews_audit(client, cid, base=C):
    return client.get(f"{base}/audit", params={"action": "colreg.review", "entityId": cid, "order": "asc"}, headers=H()).json()


# ------------------------------------------------ 裁定 1：vesselStatus 对象形态

def test_r1_vessel_status_object_converted_to_core_time(fc):
    body = {"vesselStatus": {"vessel_mary": [{"fromUtc": "2026-05-18T06:15:00Z", "status": "PowerDriven"},
                                             {"fromUtc": "2026-05-18T06:20:00Z", "status": "NotUnderCommand"}],
                             "vessel_lily": [{"fromUtc": "2026-05-18T06:15:00+00:00", "status": "PowerDriven"}]}}
    r = fc.post(f"{C}/colreg:evaluate", json=body, headers=H())
    assert r.status_code == 200, r.text
    doc = r.json()
    _ok("colreg", doc)
    late = next(b for b in doc["bands"] if b["startTimeSec"] >= 300)
    assert late["vesselStatus"]["vessel_mary"] == "NotUnderCommand"
    assert late["vesselStatus"]["vessel_lily"] == "PowerDriven"


@pytest.mark.parametrize("vs,code", [
    ([{"vesselId": "vessel_mary", "timeSec": 0, "status": "PowerDriven"}], "VALIDATION_ERROR"),       # 旧 list 形态
    ({"vessel_mary": [{"timeSec": 0, "status": "PowerDriven"}]}, "VALIDATION_ERROR"),                 # 用 timeSec
    ({"vessel_mary": [{"fromUtc": "2026-05-18T14:15:00+08:00", "status": "PowerDriven"}]}, "VALIDATION_ERROR"),  # 非 UTC
    ({"vessel_mary": [{"fromUtc": "2026-05-18T06:15:00Z", "status": "Drifting"}]}, "VALIDATION_ERROR"),
    ({"vessel_nobody": [{"fromUtc": "2026-05-18T06:15:00Z", "status": "PowerDriven"}]}, "VALIDATION_ERROR"),
])
def test_r1_vessel_status_bad_shapes_422(fc, vs, code):
    n_before = len(fc.get(f"{C}/colreg/runs", headers=H()).json()["runs"])
    r = fc.post(f"{C}/colreg:evaluate", json={"vesselStatus": vs}, headers=H())
    assert r.status_code == 422 and r.json()["code"] == code, r.text
    _ok("common#/$defs/problem", r.json())
    assert len(fc.get(f"{C}/colreg/runs", headers=H()).json()["runs"]) == n_before


def test_r1_haili5_stored_inputs_use_contract_shape(client, app):
    with app.state.db.session() as s:
        inputs = get_doc(s, ColregAnalysisRow, HAILI, "inputs")
    vs = inputs["vesselStatus"]
    assert isinstance(vs, dict) and vs["vessel_haili5"][-1] == {"fromUtc": "2025-10-25T11:51:15Z", "status": "NotUnderCommand"}


@pytest.mark.skipif(not HAS_DOTNET, reason="需要 mcis-core")
def test_r1_real_core_object_form(client):
    body = {"vesselStatus": {"vessel_mary": [{"fromUtc": "2026-05-18T06:15:00Z", "status": "PowerDriven"},
                                             {"fromUtc": "2026-05-18T06:20:00Z", "status": "NotUnderCommand"}],
                             "vessel_lily": [{"fromUtc": "2026-05-18T06:15:00Z", "status": "PowerDriven"}]}}
    r = client.post(f"{C}/colreg:evaluate", json=body, headers=H())
    assert r.status_code == 200, r.text
    late = [b for b in r.json()["bands"] if b["startTimeSec"] >= 300]
    assert late and any(b["vesselStatus"].get("vessel_mary") == "NotUnderCommand" for b in late)


# ------------------------------------------------ 裁定 2：理由全文、单独字段

def test_r2_long_reason_kept_whole(client):
    reason = "合成理由" + "甲乙丙丁戊己庚辛壬癸" * 60  # 604 字
    r = client.patch(f"{C}/colreg/checks/CK-08", json={"action": "dismiss", "reason": reason}, headers=H(operator="调查员 A"))
    assert r.status_code == 200, r.text
    ev = _reviews_audit(client, "CK-08")[-1]
    _ok("audit-event", ev)
    line = json.loads(ev["line"])
    assert line["reason"] == reason                       # 审计行扩展键：全文，进哈希链
    assert len(ev["after"]) <= 400                        # 显示摘要可以截断
    hist = client.get(f"{C}/colreg/checks/CK-08/reviews", headers=H()).json()
    assert hist["history"][-1]["reason"] == reason       # 复核历史：全文
    run = client.get(f"{C}/colreg/runs/active", headers=H()).json()
    assert run["annotations"]["checks"]["CK-08"]["reason"] == reason
    assert client.get(f"{C}/audit:verify", headers=H()).json()["valid"] is True


@pytest.mark.parametrize("body", [
    {"reviewStatus": "Rejected", "note": "旧字段名理由"},
    {"reviewStatus": "Confirmed"},
    {"action": "dismiss", "note": "旧字段名理由"},
    {"action": "dismiss", "reason": "a", "note": "a"},
    {"action": "confirm", "reviewStatus": "Confirmed"},
    {"action": "confirm", "comment": "合同外字段"},
])
def test_w62_legacy_and_unknown_fields_rejected(client, body):
    """W6.2：PATCH 只接受合同字段 action/verdict/reason/evidenceIds；旧名 reviewStatus/note 与其他字段 422，不改数据不写审计。"""
    before = _check(client.get(f"{C}/colreg", headers=H()).json(), "CK-09")
    r = client.patch(f"{C}/colreg/checks/CK-09", json=body, headers=H())
    assert r.status_code == 422 and r.json()["code"] == "VALIDATION_ERROR", r.text
    if "reviewStatus" in body or "note" in body:
        assert "旧字段名" in json.dumps(r.json(), ensure_ascii=False)
    assert "Deprecation" not in r.headers
    assert _check(client.get(f"{C}/colreg", headers=H()).json(), "CK-09") == before
    assert _reviews_audit(client, "CK-09") == []


def test_w62_contract_fields_still_work(client):
    r = client.patch(f"{C}/colreg/checks/CK-09", json={"action": "dismiss", "reason": "合同字段理由"}, headers=H())
    assert r.status_code == 200 and r.json()["reviewStatus"] == "Rejected"
    assert "Deprecation" not in r.headers
    assert json.loads(_reviews_audit(client, "CK-09")[-1]["line"])["reason"] == "合同字段理由"


# ------------------------------------------------ 裁定 3：confirm/dismiss 带 verdict → 422

@pytest.mark.parametrize("body", [
    {"action": "confirm", "verdict": "NotComplied"},
    {"action": "dismiss", "verdict": "NotComplied", "reason": "合成"},
])
def test_r3_verdict_not_allowed_on_confirm_dismiss(client, body):
    before = _check(client.get(f"{C}/colreg", headers=H()).json(), "CK-05")
    r = client.patch(f"{C}/colreg/checks/CK-05", json=body, headers=H())
    assert r.status_code == 422 and r.json()["code"] == "colreg_review_verdict_not_allowed", r.text
    _ok("common#/$defs/problem", r.json())
    assert _check(client.get(f"{C}/colreg", headers=H()).json(), "CK-05") == before
    assert _reviews_audit(client, "CK-05") == []


# ------------------------------------------------ 裁定 4：modify 规则

def test_r4_modify_to_undetermined_needs_reason(client):
    r = client.patch(f"{C}/colreg/checks/CK-06", json={"action": "modify", "verdict": "Undetermined"}, headers=H())
    assert r.status_code == 422 and r.json()["code"] == "colreg_review_reason_required"
    r = client.patch(f"{C}/colreg/checks/CK-06", json={"action": "modify", "verdict": "Undetermined", "reason": "证据冲突，暂不判定"},
                     headers=H())
    assert r.status_code == 200 and r.json()["verdict"] == "Undetermined"


def test_r4_modify_same_verdict_is_no_change(client):
    cur = _check(client.get(f"{C}/colreg", headers=H()).json(), "CK-07")["verdict"]
    r = client.patch(f"{C}/colreg/checks/CK-07", json={"action": "modify", "verdict": cur, "reason": "合成"}, headers=H())
    assert r.status_code == 422 and r.json()["code"] == "colreg_review_no_change"
    assert _reviews_audit(client, "CK-07") == []
    r = client.patch(f"{C}/colreg/checks/CK-07", json={"action": "modify", "reason": "合成"}, headers=H())
    assert r.status_code == 422 and r.json()["code"] == "colreg_review_verdict_required"


# ------------------------------------------------ 裁定 5：证据编号登记校验

@pytest.mark.parametrize("ids", [["EV-999"], ["EV-001", "EV-998"], ["bad-id"]])
def test_r5_unregistered_evidence_422_on_review(client, ids):
    before = _check(client.get(f"{C}/colreg", headers=H()).json(), "CK-11")
    r = client.patch(f"{C}/colreg/checks/CK-11", json={"action": "modify", "verdict": "NeedsReview", "reason": "合成",
                                                       "evidenceIds": ids}, headers=H())
    assert r.status_code == 422 and r.json()["code"] == "evidence_not_registered", r.text
    _ok("common#/$defs/problem", r.json())
    assert _check(client.get(f"{C}/colreg", headers=H()).json(), "CK-11") == before
    assert _reviews_audit(client, "CK-11") == []


def test_r5_registered_evidence_replaces_on_modify(client):
    r = client.patch(f"{C}/colreg/checks/CK-11", json={"action": "modify", "verdict": "NeedsReview", "reason": "补证据",
                                                       "evidenceIds": ["EV-004", "EV-004", "EV-005"]}, headers=H())
    assert r.status_code == 200 and r.json()["evidenceIds"] == ["EV-004", "EV-005"]


def test_r5_unregistered_evidence_422_on_evaluate(fc):
    r = fc.post(f"{C}/colreg:evaluate", json={"evidenceIds": ["EV-777"]}, headers=H())
    assert r.status_code == 422 and r.json()["code"] == "evidence_not_registered"


def test_r5_run_view_flags_dangling_links(fapp, fc):
    # 合成：直接在临时库里放一条链到未登记证据的核查项，接口要标 registered=false
    fc.get(f"{C}/colreg", headers=H())
    with fapp.state.db.session() as s:
        idx = get_doc(s, ColregAnalysisRow, CASE, "runs")
        run = get_doc(s, ColregAnalysisRow, CASE, f"run:{idx['activeRunId']}")
        run["analysis"]["checks"][0]["evidenceIds"] = ["EV-001", "EV-999"]
        put_doc(s, ColregAnalysisRow, CASE, f"run:{idx['activeRunId']}", run)
    v = fc.get(f"{C}/colreg/runs/active", headers=H()).json()
    links = v["annotations"]["checks"]["CK-01"]["links"]
    assert links == [{"evidenceId": "EV-001", "registered": True}, {"evidenceId": "EV-999", "registered": False}]


# ------------------------------------------------ 裁定 6：时间带证据

def test_r6_seed_bands_link_evidence(client):
    for base in (C, H5):
        v = client.get(f"{base}/colreg/runs/active", headers=H()).json()
        ev = {e["evidenceId"] for e in client.get(f"{base}/evidence", headers=H()).json()}
        assert v["kind"] == "Seed"
        for b in v["analysis"]["bands"]:
            a = v["annotations"]["bands"][b["bandId"]]
            assert a["evidenceIds"] and set(a["evidenceIds"]) <= ev and a["missingEvidence"] is False
        _ok("colreg", client.get(f"{base}/colreg", headers=H()).json())   # 主文档仍符合 schema（band 不带 evidenceIds）


def test_r6_engine_bands_evidence_or_missing(fc):
    a = fc.post(f"{C}/colreg:evaluate", json={}, headers=H())
    assert a.status_code == 200
    v = fc.get(f"{C}/colreg/runs/active", headers=H()).json()
    assert all(x["missingEvidence"] and x["evidenceIds"] == [] for x in v["annotations"]["bands"].values())
    fc.post(f"{C}/colreg:evaluate", json={"evidenceIds": ["EV-001", "EV-003"]}, headers=H())
    v = fc.get(f"{C}/colreg/runs/active", headers=H()).json()
    assert all(x["evidenceIds"] == ["EV-001", "EV-003"] for x in v["annotations"]["bands"].values())


# ------------------------------------------------ 裁定 7：source / reviewedBy / engineVerdict

def test_r7_confirm_keeps_source_records_reviewer(client):
    r = client.patch(f"{C}/colreg/checks/CK-03", json={"action": "confirm"}, headers=H(operator="调查员 B"))
    assert r.status_code == 200
    chk = r.json()
    _ok("colreg#/$defs/check", chk)
    assert chk["source"] == "Seed" and chk["reviewStatus"] == "Confirmed"
    ann = client.get(f"{C}/colreg/runs/active", headers=H()).json()["annotations"]["checks"]["CK-03"]
    assert ann["reviewedBy"] == "调查员 B" and ann["reviewedAt"].endswith("Z")
    assert "engineVerdict" not in ann


def test_r7_modify_sets_investigator_and_keeps_engine_verdict(client):
    orig = _check(client.get(f"{C}/colreg", headers=H()).json(), "CK-04")["verdict"]
    nv1 = "NeedsReview" if orig != "NeedsReview" else "Partial"
    nv2 = "NotAssessable"
    assert client.patch(f"{C}/colreg/checks/CK-04", json={"action": "modify", "verdict": nv1, "reason": "一改"}, headers=H()).status_code == 200
    r = client.patch(f"{C}/colreg/checks/CK-04", json={"action": "modify", "verdict": nv2, "reason": "二改"}, headers=H())
    assert r.status_code == 200 and r.json()["source"] == "Investigator" and r.json()["verdict"] == nv2
    ann = client.get(f"{C}/colreg/checks/CK-04/reviews", headers=H()).json()
    assert ann["engineVerdict"] == orig and len(ann["history"]) == 2
    assert [h["verdictAfter"] for h in ann["history"]] == [nv1, nv2]


# ------------------------------------------------ 裁定 8：海力5 证据来源标注

def test_r8_haili5_every_evidence_tagged(client):
    evs = client.get(f"{H5}/evidence", headers=H()).json()
    assert {e["evidenceId"] for e in evs} >= {"EV-101", "EV-106"}
    for e in evs:
        assert any(t in (e.get("note") or "") + (e.get("source") or "") for t in TAG), e["evidenceId"]


# ------------------------------------------------ 裁定 9：非虚构二次确认 + 版本化

def test_r9_nonfictional_requires_two_step_confirmation(fapp, fc):
    _make_nonfictional(fapp)
    seed_before = fc.get(f"{C}/colreg", headers=H()).json()
    # 先做一条复核，验证之后不被覆盖
    assert fc.patch(f"{C}/colreg/checks/CK-02", json={"action": "dismiss", "reason": "合成驳回"}, headers=H(operator="甲")).status_code == 200
    seed_reviewed = fc.get(f"{C}/colreg", headers=H()).json()

    r1 = fc.post(f"{C}/colreg:evaluate", json={}, headers=H(operator="甲"))
    assert r1.status_code == 409 and r1.json()["code"] == "colreg_evaluate_confirm_required"
    _ok("common#/$defs/problem", r1.json())
    tok = r1.json()["detail"]["confirmToken"]
    assert fc.get(f"{C}/colreg", headers=H()).json() == seed_reviewed      # 409 时什么都没改
    assert fc.get(f"{C}/audit", params={"action": "colreg.evaluate"}, headers=H()).json() == []

    # 他人的令牌无效
    bad = fc.post(f"{C}/colreg:evaluate", params={"confirmToken": tok}, json={}, headers=H(operator="乙"))
    assert bad.status_code == 409 and bad.json()["code"] == "colreg_evaluate_confirm_invalid"
    # 令牌已被上一步消耗 → 重新申请
    tok = fc.post(f"{C}/colreg:evaluate", json={}, headers=H(operator="甲")).json()["detail"]["confirmToken"]
    ok = fc.post(f"{C}/colreg:evaluate", params={"confirmToken": tok}, json={}, headers=H(operator="甲"))
    assert ok.status_code == 200, ok.text
    again = fc.post(f"{C}/colreg:evaluate", params={"confirmToken": tok}, json={}, headers=H(operator="甲"))
    assert again.status_code == 409 and again.json()["code"] == "colreg_evaluate_confirm_invalid"   # 一次性

    runs = fc.get(f"{C}/colreg/runs", headers=H()).json()
    assert [r["kind"] for r in runs["runs"]] == ["Seed", "RuleEngine"]
    assert runs["activeRunId"] == runs["runs"][1]["runId"]
    seed_run = fc.get(f"{C}/colreg/runs/{runs['runs'][0]['runId']}", headers=H()).json()
    assert seed_run["analysis"] == seed_reviewed                              # 种子 + 复核原样保留
    assert _check(seed_run["analysis"], "CK-02")["reviewStatus"] == "Rejected"
    assert seed_run["annotations"]["checks"]["CK-02"]["reason"] == "合成驳回"
    assert seed_before != seed_reviewed

    # 切回种子版本
    act = fc.post(f"{C}/colreg/runs/{runs['runs'][0]['runId']}:activate", headers=H())
    assert act.status_code == 200
    assert fc.get(f"{C}/colreg", headers=H()).json() == seed_reviewed
    ev = fc.get(f"{C}/audit", params={"action": "colreg.activate"}, headers=H()).json()
    assert ev and ev[-1]["category"] == "Colreg"

    cmp_ = fc.get(f"{C}/colreg/compare", params={"base": runs["runs"][0]["runId"], "other": runs["runs"][1]["runId"]},
                  headers=H()).json()
    assert cmp_["changedCheckCount"] >= 1 and cmp_["bands"]


def test_r9_fictional_evaluate_no_confirm_but_versioned(fc):
    seed = fc.get(f"{C}/colreg", headers=H()).json()
    r = fc.post(f"{C}/colreg:evaluate", json={}, headers=H())
    assert r.status_code == 200
    body = r.json()
    run_id = body.pop("runId")                                   # W6.2（W6-D06）：响应带 runId
    assert fc.get(f"{C}/colreg", headers=H()).json() == body
    runs = fc.get(f"{C}/colreg/runs", headers=H()).json()["runs"]
    assert len(runs) == 2 and runs[1]["active"] and not runs[0]["active"]
    assert run_id == runs[1]["runId"] == fc.get(f"{C}/colreg/runs", headers=H()).json()["activeRunId"]
    assert fc.get(f"{C}/colreg/runs/{runs[0]['runId']}", headers=H()).json()["analysis"] == seed


def test_r9_review_targets_selected_run_only(fc):
    fc.post(f"{C}/colreg:evaluate", json={}, headers=H())
    runs = fc.get(f"{C}/colreg/runs", headers=H()).json()["runs"]
    seed_id = runs[0]["runId"]
    r = fc.patch(f"{C}/colreg/checks/CK-01", params={"runId": seed_id}, json={"action": "confirm"}, headers=H())
    assert r.status_code == 200
    assert _check(fc.get(f"{C}/colreg/runs/{seed_id}", headers=H()).json()["analysis"], "CK-01")["reviewStatus"] == "Confirmed"
    assert all(c["checkId"] != "CK-01" for c in fc.get(f"{C}/colreg", headers=H()).json()["checks"])  # 当前版本没被动


def test_r9_external_current_overwrite_becomes_new_version(fapp, fc):
    seed = fc.get(f"{C}/colreg", headers=H()).json()
    with fapp.state.db.session() as s:
        doc = dict(seed)
        doc["engineVersion"] = "imported"
        put_doc(s, ColregAnalysisRow, CASE, "current", doc)
    runs = fc.get(f"{C}/colreg/runs", headers=H()).json()["runs"]
    assert [r["kind"] for r in runs] == ["Seed", "External"]
    assert fc.get(f"{C}/colreg/runs/{runs[0]['runId']}", headers=H()).json()["analysis"]["engineVersion"] == seed["engineVersion"]


def test_r9_readonly_cannot_activate(client):
    rid = client.get(f"{C}/colreg/runs", headers=H()).json()["activeRunId"]
    assert client.post(f"{C}/colreg/runs/{rid}:activate", headers=H("ExternalExpert")).status_code in (403, 404)


# ------------------------------------------------ 裁定 10：地址不写死（服务端只校验端口来自配置；页面见 web 测试）

def test_r10_service_port_from_config(tmp_path, monkeypatch):
    monkeypatch.setenv("MCIS_PORT", "18999")
    assert make_settings(tmp_path).port == 18999 and make_settings(tmp_path).host == "127.0.0.1"


# ------------------------------------------------ 裁定 11：章节草稿接口归 W16（Codex），本包后端不提供

def test_r11_report_draft_endpoint_left_to_w16():
    # 章节草稿接口 POST /cases/{caseId}/reports/sections/colreg:draft 归 W16；colreg 路由不抢实现（前端 404/405/501 时友好提示，见 web 测试）
    assert not any("draft" in r.path for r in colreg_router.router.routes)


# ------------------------------------------------ 裁定 12：真实数据口径——测试不对海力5 跑 evaluate，种子版本保持

def test_r12_haili5_seed_stays_active_without_evaluate(client):
    runs = client.get(f"{H5}/colreg/runs", headers=H()).json()
    assert runs["isFictionalDemo"] is False
    assert [r["kind"] for r in runs["runs"]] == ["Seed"] and runs["runs"][0]["active"]
    assert client.get(f"{H5}/audit", params={"action": "colreg.evaluate"}, headers=H()).json() == []


def test_r12_haili5_evaluate_blocked_without_token(fapp, fc):
    r = fc.post(f"{H5}/colreg:evaluate", json={}, headers=H())
    assert r.status_code == 409 and r.json()["code"] == "colreg_evaluate_confirm_required"
    assert [x["kind"] for x in fc.get(f"{H5}/colreg/runs", headers=H()).json()["runs"]] == ["Seed"]


# ------------------------------------------------ W6.2（W6-D07）：扩展路由已入合同，进入 app.openapi()

def test_extension_routes_listed_and_in_openapi(app, client):
    paths = {(m, r.path) for r in colreg_router.router.routes for m in getattr(r, "methods", ())}
    hidden = {(m, r.path) for r in colreg_router.router.routes for m in getattr(r, "methods", ())
              if not getattr(r, "include_in_schema", True)}
    assert colreg_router.PENDING_CONTRACT is False
    assert hidden == set()
    spec_paths = app.openapi()["paths"]
    for m, p in colreg_router.EXTENSION_ROUTES:
        assert (m, p) in paths, (m, p)
        assert m.lower() in spec_paths.get(p.replace("{case_id}", "{case_id}"), {}), (m, p)
        probe = p.replace("{case_id}", CASE).replace("{run_id}", "active").replace("{check_id}", "CK-01")
        if m == "GET" and "compare" not in p:
            assert client.get(probe, headers=H()).status_code == 200, probe


# ------------------------------------------------ 并发：页面同时拉多个版本接口时首次收编只建一个版本

def test_r9_concurrent_first_access_single_seed_run(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    app = create_app(make_settings(tmp_path))
    with TestClient(app) as c:
        urls = [f"{C}/colreg/runs", f"{C}/colreg/runs/active", f"{C}/colreg", f"{H5}/colreg/runs", f"{H5}/colreg"] * 4
        with ThreadPoolExecutor(8) as ex:
            codes = list(ex.map(lambda u: c.get(u, headers=H()).status_code, urls))
        assert codes == [200] * len(urls)
        assert [r["kind"] for r in c.get(f"{C}/colreg/runs", headers=H()).json()["runs"]] == ["Seed"]
        assert [r["kind"] for r in c.get(f"{H5}/colreg/runs", headers=H()).json()["runs"]] == ["Seed"]
