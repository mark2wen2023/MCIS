"""W6.1 独立验收：补测 21:03 十二条裁定中原 W6 用例未覆盖的项。

只用虚构 Lily/Mary 与合成非虚构标记；海力5 只取 409 令牌、不跑 evaluate。
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from conftest import HAILI, HAS_CORE, LILY, H
from schema_check import check as schema

from mcis_service.cases.models import CaseRow
from mcis_service.colreg import router as colreg_router
from mcis_service.db import get_doc, put_doc

L = f"/api/v1/cases/{LILY}"
H5 = f"/api/v1/cases/{HAILI}"
OP = "验收员·合成甲"
OP2 = "验收员·合成乙"
needs_core = pytest.mark.skipif(not HAS_CORE, reason="需要真实 dotnet 与预构建 mcis-core.dll（支持 MCIS_DOTNET/MCIS_CORE_DLL）")
ROOT = Path(__file__).resolve().parents[2]


def _ok(ref, doc):
    errs = schema(ref, doc)
    assert not errs, f"{ref}: {errs[:8]}"


def _colreg(client, base=L):
    r = client.get(f"{base}/colreg", headers=H())
    assert r.status_code == 200, r.text
    return r.json()


def _check(doc, cid):
    return next(c for c in doc["checks"] if c["checkId"] == cid)


def _patch(client, cid, body, role="Investigator", op=OP, base=L, **params):
    return client.patch(f"{base}/colreg/checks/{cid}", json=body, headers=H(role, op), params=params)


def _make_nonfictional(client, case_id=LILY):
    with client.app.state.db.session() as s:
        doc = get_doc(s, CaseRow, case_id, case_id)
        doc["isFictionalDemo"] = False
        put_doc(s, CaseRow, case_id, case_id, doc)


def _line_reason(ev):
    return json.loads(ev["line"]).get("reason")


# ---------------- 裁定 1：旧列表格式 422 ----------------

def test_W61_vessel_status_legacy_list_is_422(client):
    n_before = len(client.get(f"{L}/colreg/runs", headers=H()).json()["runs"])
    r = client.post(f"{L}/colreg:evaluate", json={
        "vesselStatus": [{"vesselId": "vessel_mary", "timeSec": 0, "status": "PowerDriven"}],
    }, headers=H())
    assert r.status_code == 422, r.text
    _ok("common#/$defs/problem", r.json())
    assert r.json()["code"] == "VALIDATION_ERROR"
    assert len(client.get(f"{L}/colreg/runs", headers=H()).json()["runs"]) == n_before


# ---------------- 裁定 2：reason 全文落盘逐字一致 ----------------

def test_W61_reason_verbatim_on_disk_and_history(client):
    reason = "合成理由全文核对-" + "甲乙丙丁戊己庚辛壬癸" * 50
    r = _patch(client, "CK-08", {"action": "dismiss", "reason": reason})
    assert r.status_code == 200, r.text
    evs = client.get(f"{L}/audit", params={"action": "colreg.review", "entityId": "CK-08", "order": "asc"},
                     headers=H()).json()
    assert evs
    ev = evs[-1]
    _ok("audit-event", ev)
    assert len(ev["after"]) <= 400
    assert _line_reason(ev) == reason
    hist = client.get(f"{L}/colreg/checks/CK-08/reviews", headers=H()).json()
    assert hist["history"][-1]["reason"] == reason
    run = client.get(f"{L}/colreg/runs/active", headers=H()).json()
    assert run["annotations"]["checks"]["CK-08"]["reason"] == reason


# ---------------- 裁定 3：confirm/dismiss 带 verdict 422 ----------------

@pytest.mark.parametrize("body", [
    {"action": "confirm", "verdict": "NotComplied"},
    {"action": "dismiss", "verdict": "NotComplied", "reason": "合成"},
    {"action": "confirm", "verdict": "NotComplied", "evidenceIds": ["EV-001"]},
    {"action": "dismiss", "verdict": "NotComplied", "reason": "合成", "evidenceIds": ["EV-001"]},
])
def test_W61_confirm_dismiss_with_verdict_422(client, body):
    before = _check(_colreg(client), "CK-05")
    r = _patch(client, "CK-05", body)
    assert r.status_code == 422, r.text
    _ok("common#/$defs/problem", r.json())
    assert r.json()["code"] == "colreg_review_verdict_not_allowed"
    assert _check(_colreg(client), "CK-05") == before


# ---------------- 裁定 4：modify 同判定 422 ----------------

def test_W61_modify_same_verdict_422(client):
    cur = _check(_colreg(client), "CK-07")["verdict"]
    r = _patch(client, "CK-07", {"action": "modify", "verdict": cur, "reason": "合成无变化"})
    assert r.status_code == 422, r.text
    _ok("common#/$defs/problem", r.json())
    assert r.json()["code"] == "colreg_review_no_change"
    r = _patch(client, "CK-07", {"action": "modify", "verdict": "Undetermined", "reason": "证据冲突，暂不判定"})
    assert r.status_code == 200 and r.json()["verdict"] == "Undetermined"


# ---------------- 裁定 5：未登记证据 422 ----------------

@pytest.mark.parametrize("ids", [["EV-999"], ["EV-001", "EV-998"], ["bad-id"]])
def test_W61_unregistered_evidence_422_on_review(client, ids):
    before = _check(_colreg(client), "CK-11")
    r = _patch(client, "CK-11", {"action": "modify", "verdict": "NeedsReview", "reason": "合成", "evidenceIds": ids})
    assert r.status_code == 422, r.text
    _ok("common#/$defs/problem", r.json())
    assert r.json()["code"] == "evidence_not_registered"
    assert _check(_colreg(client), "CK-11") == before


def test_W61_unregistered_evidence_422_on_evaluate(client):
    r = client.post(f"{L}/colreg:evaluate", json={"evidenceIds": ["EV-777"]}, headers=H())
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "evidence_not_registered"


# ---------------- 裁定 9：409 令牌绑定案件、操作员、过期、一次性 ----------------

def test_W61_confirm_token_bound_to_case_and_operator(client):
    _make_nonfictional(client, LILY)
    r_lily = client.post(f"{L}/colreg:evaluate", json={}, headers=H(operator=OP))
    assert r_lily.status_code == 409 and r_lily.json()["code"] == "colreg_evaluate_confirm_required"
    _ok("common#/$defs/problem", r_lily.json())
    d = r_lily.json()["detail"]
    assert d["caseId"] == LILY and d["isFictionalDemo"] is False
    assert d["expiresInSec"] == 300 and d.get("confirmToken") and d.get("nextVersion")
    tok_lily = d["confirmToken"]

    # 他人令牌
    bad_op = client.post(f"{L}/colreg:evaluate", params={"confirmToken": tok_lily}, json={}, headers=H(operator=OP2))
    assert bad_op.status_code == 409 and bad_op.json()["code"] == "colreg_evaluate_confirm_invalid"
    # 上一步消耗了令牌（pop 后校验失败），需重申
    tok_lily = client.post(f"{L}/colreg:evaluate", json={}, headers=H(operator=OP)).json()["detail"]["confirmToken"]

    # 跨案：海力5 令牌用在 Lily，Lily 令牌用在海力5（均不跑引擎）
    r_h5 = client.post(f"{H5}/colreg:evaluate", json={}, headers=H(operator=OP))
    assert r_h5.status_code == 409 and r_h5.json()["code"] == "colreg_evaluate_confirm_required"
    tok_h5 = r_h5.json()["detail"]["confirmToken"]
    cross1 = client.post(f"{L}/colreg:evaluate", params={"confirmToken": tok_h5}, json={}, headers=H(operator=OP))
    assert cross1.status_code == 409 and cross1.json()["code"] == "colreg_evaluate_confirm_invalid"
    cross2 = client.post(f"{H5}/colreg:evaluate", params={"confirmToken": tok_lily}, json={}, headers=H(operator=OP))
    assert cross2.status_code == 409 and cross2.json()["code"] == "colreg_evaluate_confirm_invalid"
    # 海力5 种子未被 evaluate
    kinds = [x["kind"] for x in client.get(f"{H5}/colreg/runs", headers=H()).json()["runs"]]
    assert kinds == ["Seed"]


def test_W61_confirm_token_expires_after_5_minutes(client, monkeypatch):
    _make_nonfictional(client, LILY)
    clock = {"t": time.monotonic()}
    monkeypatch.setattr(colreg_router.time, "monotonic", lambda: clock["t"])
    r1 = client.post(f"{L}/colreg:evaluate", json={}, headers=H(operator=OP))
    assert r1.status_code == 409
    tok = r1.json()["detail"]["confirmToken"]
    clock["t"] += 301
    r2 = client.post(f"{L}/colreg:evaluate", params={"confirmToken": tok}, json={}, headers=H(operator=OP))
    assert r2.status_code == 409 and r2.json()["code"] == "colreg_evaluate_confirm_invalid"
    # 过期后不会误跑引擎
    assert [x["kind"] for x in client.get(f"{L}/colreg/runs", headers=H()).json()["runs"]] == ["Seed"]


@needs_core
def test_W61_confirm_token_is_single_use(client):
    _make_nonfictional(client, LILY)
    tok = client.post(f"{L}/colreg:evaluate", json={}, headers=H(operator=OP)).json()["detail"]["confirmToken"]
    ok = client.post(f"{L}/colreg:evaluate", params={"confirmToken": tok}, json={}, headers=H(operator=OP))
    assert ok.status_code == 200, ok.text
    again = client.post(f"{L}/colreg:evaluate", params={"confirmToken": tok}, json={}, headers=H(operator=OP))
    assert again.status_code == 409 and again.json()["code"] == "colreg_evaluate_confirm_invalid"


@needs_core
def test_W61_new_run_does_not_overwrite_seed_or_reviews(client):
    seed = _colreg(client)
    r0 = _patch(client, "CK-02", {"action": "dismiss", "reason": "合成驳回-保留复核"})
    assert r0.status_code == 200
    reviewed = _colreg(client)
    assert _check(reviewed, "CK-02")["reviewStatus"] == "Rejected"
    ev = client.post(f"{L}/colreg:evaluate", json={}, headers=H())
    assert ev.status_code == 200, ev.text
    runs = client.get(f"{L}/colreg/runs", headers=H()).json()
    assert [x["kind"] for x in runs["runs"]] == ["Seed", "RuleEngine"]
    assert runs["activeRunId"] == runs["runs"][1]["runId"]
    seed_run = client.get(f"{L}/colreg/runs/{runs['runs'][0]['runId']}", headers=H()).json()
    assert seed_run["analysis"] == reviewed
    assert _check(seed_run["analysis"], "CK-02")["reviewStatus"] == "Rejected"
    assert seed_run["annotations"]["checks"]["CK-02"]["reason"] == "合成驳回-保留复核"
    assert seed != reviewed
    # 当前版本是新引擎结果，种子仍可切回
    act = client.post(f"{L}/colreg/runs/{runs['runs'][0]['runId']}:activate", headers=H())
    assert act.status_code == 200
    assert _colreg(client) == reviewed


# ---------------- W6.2 evaluate 响应 runId（缺.NET时不宣称验证通过） ----------------

@needs_core
def test_W61_evaluate_response_includes_runId(client):
    r = client.post(f"{L}/colreg:evaluate", json={}, headers=H())
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc.get("runId"), "evaluate 响应缺少 runId（21:34 裁定：须带本次新建版本 id）"
    runs = client.get(f"{L}/colreg/runs", headers=H()).json()
    assert doc["runId"] == runs["activeRunId"]


# ---------------- W6.2 扩展路由进入自动生成合同 ----------------

def test_W61_extension_routes_appear_in_app_openapi(client):
    """W6-D07：合同与自动生成schema均包含五条扩展路由。"""
    import re
    def _norm(p):
        return re.sub(r"\{[^}]+\}", "{}", p)
    declared = {
        "/api/v1/cases/{}/colreg/runs",
        "/api/v1/cases/{}/colreg/runs/{}",
        "/api/v1/cases/{}/colreg/runs/{}:activate",
        "/api/v1/cases/{}/colreg/compare",
        "/api/v1/cases/{}/colreg/checks/{}/reviews",
    }
    # 路由可访问
    assert client.get(f"{L}/colreg/runs", headers=H()).status_code == 200
    assert client.get(f"{L}/colreg/runs/active", headers=H()).status_code == 200
    cid = _colreg(client)["checks"][0]["checkId"]
    assert client.get(f"{L}/colreg/checks/{cid}/reviews", headers=H()).status_code == 200
    # 自动生成 schema 应包含，复测 W6-D07
    paths = {_norm(p) for p in client.app.openapi()["paths"]}
    missing = declared - paths
    assert not missing, f"app.openapi() 未包含已写入合同的扩展路由：{sorted(missing)}"
    assert colreg_router.PENDING_CONTRACT is False


# ---------------- 裁定 10：__MCIS_API__ 配置生效（源码 + vite） ----------------

def test_W61_vite_injects_mcis_api():
    vite = (ROOT / "web/vite.config.ts").read_text(encoding="utf-8")
    assert "__MCIS_API__" in vite
    assert "process.env.MCIS_API" in vite
    cfg = (ROOT / "web/src/config.ts").read_text(encoding="utf-8")
    assert "__MCIS_API__" in cfg and "DEFAULT_SERVICE_URL" in cfg
    assert "127.0.0.1:8765" in cfg


def test_W61_colreg_page_friendly_draft_errors():
    src = (ROOT / "web/src/pages/ColregPage.tsx").read_text(encoding="utf-8")
    assert "REPORT_DRAFT_PATH" in src and "colreg:draft" in src
    assert "404" in src and "405" in src and "501" in src
    assert "DRAFT_UNAVAILABLE" in src or "尚未上线" in src
