from .conftest import C, H


def _utf16_slice(s: str, start: int, length: int) -> str:
    b = s.encode("utf-16-le")
    return b[start * 2:(start + length) * 2].decode("utf-16-le")


def test_interview_list_summary(client):
    lst = client.get(f"{C}/interviews", headers=H()).json()
    assert [x["recordId"] for x in lst] == [f"IR-0{i}" for i in range(1, 7)]
    ir3 = next(x for x in lst if x["recordId"] == "IR-03")
    assert ir3["turnCount"] == 8 and ir3["statementCount"] == 8
    assert ir3["contradictionCount"] == 1          # 只有 Confirmed 的矛盾计入
    assert ir3["contradictionCandidateCount"] >= 3


def test_statement_spans_are_utf16(client):
    d = client.get(f"{C}/interviews/IR-03", headers=H("LeadInvestigator")).json()
    turns = {t["round"]: t for t in d["turns"]}
    for st in d["statements"]:
        sp = st["span"]
        assert _utf16_slice(turns[sp["round"]]["answer"], sp["start"], sp["length"]) == st["quote"]


def test_redaction_by_role(client):
    lead = client.get(f"{C}/interviews/IR-03", headers=H("LeadInvestigator"))
    assert lead.headers["X-MCIS-Redaction"] == "none"
    name = lead.json()["interviewee"]["name"]
    ext = client.get(f"{C}/interviews/IR-03", headers=H("ExternalExpert"))
    assert "interviewee.name" in ext.headers["X-MCIS-Redaction"]
    e = ext.json()["interviewee"]
    assert e["name"] != name and e["name"] == e["role"]
    assert e.get("phone") == "██████"
    joined = "".join(t["answer"] for t in ext.json()["turns"])
    assert "[已遮盖]" in joined
    agent = client.get(f"{C}/agents/inputs/interviews/IR-03", headers=H("Investigator")).json()
    assert agent["interviewee"]["name"].startswith("<ROLE_")
    assert client.get(f"{C}/interviews/IR-03", headers=H("Public")).status_code == 403
    # 外部角色读取证词写审计
    a = client.get(f"{C}/audit", params={"action": "testimony.read"}, headers=H("LeadInvestigator")).json()
    assert a and a[-1]["role"] == "ExternalExpert"


def test_redaction_preview_and_policy(client):
    r = client.post(f"{C}/redaction/preview", json={"role": "InterestedState", "recordId": "IR-03"}, headers=H("LeadInvestigator"))
    assert r.status_code == 200 and r.json()["level"] == "Redacted"
    assert client.post(f"{C}/redaction/preview", json={"role": "X", "recordId": "IR-03"}, headers=H()).status_code == 422
    pol = client.get(f"{C}/access-policy", headers=H("LeadInvestigator")).json()
    pol["matrix"]["ExternalExpert"]["testimony"] = "Deny"
    assert client.put(f"{C}/access-policy", json=pol, headers=H("Investigator")).status_code == 403
    assert client.put(f"{C}/access-policy", json=pol, headers=H("LeadInvestigator")).status_code == 200
    assert client.get(f"{C}/interviews/IR-03", headers=H("ExternalExpert")).status_code == 403
    assert client.get(f"{C}/audit", params={"action": "policy.update"}, headers=H("LeadInvestigator")).json()


def test_crosscheck_requires_confirmation(client):
    cc = client.get(f"{C}/interviews/IR-03/crosscheck", headers=H()).json()
    assert all(c["state"] in ("PendingConfirmation", "Confirmed") for c in cc["results"])
    # 外部角色不能确认
    assert client.post(f"{C}/interviews/IR-03/crosscheck/IR-03-S01:confirm", json={}, headers=H("ExternalExpert")).status_code == 403
    # 驳回必须写理由
    assert client.post(f"{C}/interviews/IR-03/crosscheck/IR-03-S05:dismiss", json={}, headers=H()).status_code == 422
    r = client.post(f"{C}/interviews/IR-03/crosscheck/IR-03-S01:confirm", json={"note": "与 VDR 一致"}, headers=H(operator="调查员 B"))
    assert r.status_code == 200 and r.json()["updated"] == ["IR-03-S01"]
    assert client.post(f"{C}/interviews/IR-03/crosscheck/IR-03-S01:confirm", json={}, headers=H()).status_code == 409
    assert client.post(f"{C}/interviews/IR-03/crosscheck/IR-03-S05:dismiss", json={"note": "口误"}, headers=H()).status_code == 200
    s = next(x for x in client.get(f"{C}/interviews", headers=H()).json() if x["recordId"] == "IR-03")
    assert s["contradictionCount"] == 2
    # 一致项批量确认，不碰矛盾/无法核实
    b = client.post(f"{C}/interviews/IR-03/crosscheck:confirm-consistent", json={}, headers=H()).json()
    assert sorted(b["updated"]) == ["IR-03-S02", "IR-03-S04", "IR-03-S06", "IR-03-S07"]
    res = {c["statementId"]: c for c in b["results"]}
    assert res["IR-03-S08"]["state"] == "PendingConfirmation" and res["IR-03-S02"]["confirmedInBatch"] is True
    acts = [a["action"] for a in client.get(f"{C}/audit", params={"entityType": "crossCheck"}, headers=H()).json()]
    assert acts.count("interview.crosscheck.batch_confirm") == 4
    assert "interview.contradiction.confirm" in acts and "interview.contradiction.dismiss" in acts


def test_statement_add_and_review(client):
    d = client.get(f"{C}/interviews/IR-03", headers=H()).json()
    ans = d["turns"][1]["answer"]                      # 第 2 轮："有雾，能见度大约 1.5 海里。……"
    start = ans.index("1.5 海里")
    body = {"kind": "Observation", "subject": "visibility", "summary": "能见度约 1.5 nm",
            "claim": {"valueType": "Scalar", "scalar": 1.5, "unit": "nm"},
            "span": {"round": 2, "field": "Answer", "start": start, "length": len("1.5 海里")}, "extractedBy": "Agent"}
    r = client.post(f"{C}/interviews/IR-03/statements", json=body, headers=H())
    assert r.status_code == 201, r.text
    st = r.json()
    assert st["statementId"] == "IR-03-S09" and st["quote"] == "1.5 海里" and st["reviewStatus"] == "Draft"
    r = client.patch(f"{C}/interviews/IR-03/statements/IR-03-S09", json={"reviewStatus": "Confirmed"}, headers=H())
    assert r.json()["reviewStatus"] == "Confirmed"
    acts = [a["action"] for a in client.get(f"{C}/audit", params={"entityId": "IR-03-S09"}, headers=H()).json()]
    assert acts == ["statement.add", "statement.review"]
