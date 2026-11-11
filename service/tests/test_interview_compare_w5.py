"""W5 询问笔录比对页（#interview，原型第 10 页）服务端：名单 / 页面视图 / 行复核 / 陈述修订 / 重新比对。
W5.1：statementVersion + 过期标记（stale）、重新提交只能从 Dismissed 发起、旧条目 Superseded 留痕。全部为虚构演示数据。"""
from mcis_service.common import contracts

from .conftest import C, H

P = f"{C}/interview-compare"
INV = H("Investigator", "调查员 A")


def _page(client, rid="IR-03", h=INV):
    r = client.get(f"{P}/{rid}", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def _row(page, sid):
    return next(x for x in page["rows"] if x["statementId"] == sid)


def _audit(client, action):
    return client.get(f"{C}/audit?action={action}", headers=H("LeadInvestigator")).json()


def _doc(client, rid="IR-03"):
    return client.get(f"{C}/interviews/{rid}", headers=H("LeadInvestigator")).json()


def test_roster_lists_records_with_contract_counts(client):
    r = client.get(P, headers=INV)
    assert r.status_code == 200
    body = r.json()
    assert body["fictional"] is True and "虚构" in body["disclaimer"]
    ids = [x["recordId"] for x in body["records"]]
    assert ids == sorted(ids) and len(ids) == 6
    by = {x["recordId"]: x for x in body["records"]}
    # IR-03：S01/S05 矛盾待确认，S03 矛盾已确认 → 只计已确认
    assert by["IR-03"]["confirmedContradictions"] == 1 and by["IR-03"]["status"] == "Contradictions"
    assert by["IR-03"]["label"] == "1 处矛盾 · 7 条待确认"
    assert by["IR-01"]["label"] == "1 处矛盾"
    assert by["IR-02"]["status"] == "Pending" and by["IR-02"]["label"] == "1 条待确认"
    assert all(x["staleCount"] == 0 for x in body["records"])


def test_page_rows_summary_segments_and_chart(client):
    pg = _page(client)
    assert pg["record"]["recordId"] == "IR-03" and pg["fictional"] is True
    assert len(pg["rows"]) == 8
    assert pg["summary"]["headerText"] == "8 条陈述 · 3 条矛盾"
    s03 = _row(pg, "IR-03-S03")
    assert s03["state"] == "Confirmed" and s03["isContradiction"] and not s03["isStale"]
    assert s03["citation"] == "IR-03 第 3 问" and s03["statementVersion"] == 1 and s03["statementRevision"] == 1
    # 片段覆盖全文，矛盾标记来自当前条目
    t3 = next(t for t in pg["turns"] if t["round"] == 3)
    assert "".join(s["text"] for s in t3["answerSegments"]) == t3["answer"]
    marks = {sid: s["contradiction"] for s in t3["answerSegments"] for sid in s["statementIds"]}
    assert marks["IR-03-S03"] == "Confirmed" and marks["IR-03-S05"] == "Pending" and marks["IR-03-S04"] == "None"
    assert pg["highlightSuppressed"] is False
    # 时间轴：时刻类陈述 = 陈述时刻 − Δ
    pts = pg["chart"]["points"]
    assert [p["statementUtc"] for p in pts] == sorted(p["statementUtc"] for p in pts)
    p3 = next(p for p in pts if p["statementId"] == "IR-03-S03")
    assert p3["observedUtc"] is not None and p3["deltaSeconds"] == 45
    assert pg["chart"]["axisStartUtc"] <= p3["observedUtc"] <= pg["chart"]["axisEndUtc"]


def test_records_without_statements_show_crosscheck_rows(client):
    pg = _page(client, "IR-01")
    assert len(pg["rows"]) == 1
    row = pg["rows"][0]
    assert row["statementMissing"] is True and row["isContradiction"] and row["state"] == "Confirmed"


def test_revise_marks_stale_and_confirm_is_refused(client):
    r = client.post(f"{P}/IR-03/statements/IR-03-S08:revise", headers=INV,
                    json={"summary": "事发前连续睡眠约 2 h（更正，虚构）", "claim": {"valueType": "Scalar", "scalar": 2.0, "unit": "h"}, "reason": "复听录音更正"})
    assert r.status_code == 200, r.text
    assert r.json()["revision"] == 2 and r.json()["reviewStatus"] == "Modified"
    pg = _page(client)
    row = _row(pg, "IR-03-S08")
    assert row["isStale"] and row["statementVersion"] == 1 and row["statementRevision"] == 2
    assert pg["summary"]["staleCount"] == 1 and pg["summary"]["headerText"].endswith("· 1 条需重新比对")
    assert pg["summary"]["pendingCount"] == 6
    contracts.validate("interview", _doc(client))
    # 过期结论不能确认
    r = client.post(f"{P}/IR-03/rows/IR-03-S08:confirm", headers=INV, json={})
    assert r.status_code == 409 and r.json()["code"] == "icmp_entry_stale"
    a = _audit(client, "statement.modify")
    assert a and "r1" in a[-1]["before"] and "r2" in a[-1]["after"]


def test_revise_only_open_statements(client):
    r = client.post(f"{P}/IR-03/statements/IR-03-S01:revise", headers=INV, json={"summary": "x", "reason": "r"})
    assert r.status_code == 409 and r.json()["code"] == "interview_statement_not_editable"
    r = client.post(f"{P}/IR-03/statements/IR-03-S08:revise", headers=INV, json={"summary": "x", "reason": " "})
    assert r.status_code == 422


def test_recheck_stale_pending_dismisses_then_resubmits_and_keeps_superseded(client):
    client.post(f"{P}/IR-03/statements/IR-03-S08:revise", headers=INV, json={"summary": "睡眠约 2 h（虚构）", "reason": "更正"})
    body = {"outcome": "Contradictory", "observedText": "工休记录：休息 5 h（虚构）", "sourceLabel": "工休记录（虚构）",
            "delta": -3, "deltaUnit": "h", "reason": "陈述已更正，按工休记录重比"}
    r = client.post(f"{P}/IR-03/rows/IR-03-S08:recheck", headers=INV, json=body)
    assert r.status_code == 200, r.text
    doc = _doc(client)
    mine = [c for c in doc["crossChecks"] if c["statementId"] == "IR-03-S08"]
    assert [c["state"] for c in mine] == ["Superseded", "PendingConfirmation"]
    assert mine[0]["note"].startswith("陈述已改版 r1→r2")
    assert mine[1]["statementVersion"] == 2 and mine[1]["claimedText"] == "睡眠约 2 h（虚构）"
    contracts.validate("interview", doc)
    pg = _page(client)
    row = _row(pg, "IR-03-S08")
    assert not row["isStale"] and row["outcome"] == "Contradictory" and row["supersededCount"] == 1
    assert pg["summary"]["staleCount"] == 0
    assert any(x["statementId"] == "IR-03-S08" and x["state"] == "Superseded" for x in pg["superseded"])
    assert _audit(client, "interview.contradiction.dismiss")[-1]["entityId"] == "IR-03-S08"
    rs = _audit(client, "interview.crosscheck.resubmit")
    assert rs and rs[-1]["before"].startswith("Dismissed；Unverifiable") and "理由=陈述已更正" in rs[-1]["after"]
    # 新条目可以确认
    assert client.post(f"{P}/IR-03/rows/IR-03-S08:confirm", headers=INV, json={}).status_code == 200


def test_recheck_rules(client):
    body = {"outcome": "Consistent", "observedText": "x", "sourceLabel": "VDR（虚构）", "reason": "重比"}
    # 未过期的待确认：直接确认或驳回
    r = client.post(f"{P}/IR-03/rows/IR-03-S01:recheck", headers=INV, json=body)
    assert r.status_code == 409 and r.json()["code"] == "icmp_recheck_not_allowed"
    # 已确认：不可撤销
    r = client.post(f"{P}/IR-03/rows/IR-03-S03:recheck", headers=INV, json=body)
    assert r.status_code == 409 and r.json()["code"] == "icmp_recheck_not_allowed"
    # 已驳回 → Resubmit
    assert client.post(f"{C}/interviews/IR-03/crosscheck/IR-03-S01:dismiss", headers=INV, json={"note": "AIS 时钟偏差（虚构）"}).status_code == 200
    r = client.post(f"{P}/IR-03/rows/IR-03-S01:recheck", headers=INV, json={**body, "reason": " "})
    assert r.status_code == 422 and r.json()["code"] == "icmp_invalid_argument"
    r = client.post(f"{P}/IR-03/rows/IR-03-S01:recheck", headers=INV, json=body)
    assert r.status_code == 200
    assert [c["state"] for c in _doc(client)["crossChecks"] if c["statementId"] == "IR-03-S01"] == ["Superseded", "PendingConfirmation"]
    # 结论枚举非法
    r = client.post(f"{P}/IR-03/rows/IR-03-S02:recheck", headers=INV, json={**body, "outcome": "Maybe"})
    assert r.status_code == 422


def test_confirm_and_reject_rows(client):
    r = client.post(f"{P}/IR-03/rows/IR-03-S01:confirm", headers=INV, json={"note": "与 AIS 核对（虚构）"})
    assert r.status_code == 200
    assert _row(_page(client), "IR-03-S01")["state"] == "Confirmed"
    assert _audit(client, "interview.contradiction.confirm")[-1]["entityId"] == "IR-03-S01"
    r = client.post(f"{P}/IR-03/rows/IR-03-S01:confirm", headers=INV, json={})
    assert r.status_code == 409 and r.json()["code"] == "icmp_not_reviewable"
    # 驳回：理由必填；陈述须为草稿/已修改
    assert client.post(f"{P}/IR-03/rows/IR-03-S08:reject", headers=INV, json={"reason": ""}).status_code == 422
    r = client.post(f"{P}/IR-03/rows/IR-03-S02:reject", headers=INV, json={"reason": "x"})
    assert r.status_code == 409 and r.json()["code"] == "icmp_not_reviewable"
    r = client.post(f"{P}/IR-03/rows/IR-03-S08:reject", headers=INV, json={"reason": "非本人陈述（虚构）"})
    assert r.status_code == 200
    doc = _doc(client)
    assert next(s for s in doc["statements"] if s["statementId"] == "IR-03-S08")["reviewStatus"] == "Rejected"
    assert next(c for c in doc["crossChecks"] if c["statementId"] == "IR-03-S08")["state"] == "Dismissed"
    assert all(x["statementId"] != "IR-03-S08" for x in _page(client)["rows"])
    r = client.post(f"{P}/IR-03/rows/IR-03-S99:confirm", headers=INV, json={})
    assert r.status_code == 404 and r.json()["code"] == "icmp_statement_not_found"


def test_external_roles_get_redacted_page_and_cannot_write(client):
    h = H("ExternalExpert", "外部专家")
    r = client.get(f"{P}/IR-03", headers=h)
    assert r.status_code == 200
    text = r.text
    assert "张某（虚构）" not in text and "家里有事没睡好" not in text and "138 0000 0000" not in text
    assert r.json()["highlightSuppressed"] is True
    roster = client.get(P, headers=h).text
    assert "张某（虚构）" not in roster
    for path in ("rows/IR-03-S01:confirm", "rows/IR-03-S01:reject", "rows/IR-03-S01:recheck", "statements/IR-03-S08:revise"):
        r = client.post(f"{P}/IR-03/{path}", headers=h, json={"reason": "x", "summary": "x", "outcome": "Consistent", "observedText": "x"})
        assert r.status_code == 403, path


def test_unknown_record_404(client):
    r = client.get(f"{P}/IR-99", headers=INV)
    assert r.status_code == 404
