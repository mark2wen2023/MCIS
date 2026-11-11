"""W5 比对页纯函数视图（interview_compare.view）单元测试：合成文档，全部虚构。"""
from mcis_service.interview_compare import router, view
from mcis_service.redaction.gateway import MASK


def _st(sid, rnd=1, start=0, length=2, status="Draft", rev=1, kind="Time", time=None):
    claim = {"valueType": "EventTime" if time else "Occurrence", "time": time, "scalar": None, "unit": "", "position": None,
             "occurred": None if time else True}
    return {"statementId": sid, "recordId": "IR-09", "kind": kind, "subject": "x", "summary": f"{sid}（虚构）", "claim": claim,
            "referenceUtc": None, "span": {"round": rnd, "field": "Answer", "start": start, "length": length}, "quote": "",
            "reviewStatus": status, "revision": rev}


def _cc(sid, outcome="Contradictory", state="PendingConfirmation", ver=1, delta=None, unit=""):
    return {"statementId": sid, "recordId": "IR-09", "outcome": outcome, "delta": delta, "deltaUnit": unit, "claimedText": sid,
            "observedText": "obs（虚构）", "sourceLabel": "VDR（虚构）", "rule": "r", "state": state, "decidedBy": None,
            "decidedUtc": None, "note": "", "confirmedInBatch": False, "statementVersion": ver}


def _doc(statements, checks, answer="一二三四五六七八九十"):
    return {"recordId": "IR-09", "caseId": "CASE-X", "interviewee": {"intervieweeId": "P", "name": "虚构证人", "role": "水手", "affiliation": "Mary 轮"},
            "startUtc": "2026-05-19T01:00:00Z", "turns": [{"round": 1, "question": "问？", "answer": answer, "utc": None, "sensitiveFragments": []}],
            "statements": statements, "crossChecks": checks}


def test_current_entry_ignores_superseded_even_if_listed_last():
    d = _doc([_st("S1")], [_cc("S1", "Consistent"), _cc("S1", "Contradictory", "Superseded")])
    assert view.current_entries(d)["S1"]["outcome"] == "Consistent"
    assert view.rows(d)[0]["supersededCount"] == 1 and view.rows(d)[0]["outcome"] == "Consistent"


def test_stale_contradiction_is_not_a_contradiction_anywhere():
    d = _doc([_st("S1", rev=2, time="2026-05-18T06:23:00Z"), _st("S2", start=3, length=2)],
             [_cc("S1", ver=1, delta=45, unit="s"), _cc("S2", state="Confirmed")])
    r1 = view.rows(d)[0]
    assert r1["isStale"] and not r1["isContradiction"]
    s = view.summarize(d)
    assert s["staleCount"] == 1 and s["contradictionCount"] == 1 and s["confirmedContradictionCount"] == 1
    e = view.roster_entry(d)
    assert e["label"] == "1 处矛盾 · 1 条需重新比对" and e["staleCount"] == 1
    segs = view.segments(d, 1, "Answer", d["turns"][0]["answer"])
    marks = {sid: sg["contradiction"] for sg in segs for sid in sg["statementIds"]}
    assert marks == {"S1": "None", "S2": "Confirmed"}
    p = view.chart(d)["points"][0]
    assert p["isStale"] and p["observedUtc"] is None and p["note"] == view.STALE_LABEL and p["outcome"] is None


def test_roster_only_stale_is_pending():
    d = _doc([_st("S1", rev=3)], [_cc("S1", "Consistent", "Confirmed", ver=2)])
    e = view.roster_entry(d)
    assert e["status"] == "Pending" and e["label"] == "1 条需重新比对"


def test_fresh_entry_marks_and_chart_delta():
    d = _doc([_st("S1", rev=2, time="2026-05-18T06:23:00Z")], [_cc("S1", ver=2, delta=45, unit="s")])
    assert view.segments(d, 1, "Answer", d["turns"][0]["answer"])[0]["contradiction"] == "Pending"
    p = view.chart(d)["points"][0]
    assert p["observedUtc"] == "2026-05-18T06:22:15Z" and not p["isStale"]
    assert view.chart(d)["axisStartUtc"] == "2026-05-18T06:22:00Z" and view.chart(d)["axisEndUtc"] == "2026-05-18T06:23:00Z"


def test_rejected_statements_are_hidden_and_not_highlighted():
    d = _doc([_st("S1", status="Rejected"), _st("S2", start=3, length=2)], [_cc("S1", state="Dismissed"), _cc("S2")])
    assert [r["statementId"] for r in view.rows(d)] == ["S2"]
    ids = [sid for sg in view.segments(d, 1, "Answer", d["turns"][0]["answer"]) for sid in sg["statementIds"]]
    assert ids == ["S2"]
    assert "".join(sg["text"] for sg in view.segments(d, 1, "Answer", d["turns"][0]["answer"])) == d["turns"][0]["answer"]


def test_missing_versions_default_to_1_and_unchecked_counts():
    st = _st("S1")
    st.pop("revision")
    cc = _cc("S1")
    cc.pop("statementVersion")
    d = _doc([st, _st("S2", start=3, length=2)], [cc])
    assert not view.rows(d)[0]["isStale"]
    s = view.summarize(d)
    assert s["uncheckedCount"] == 1 and s["headerText"] == "2 条陈述 · 1 条矛盾"


def test_safe_quote_masks_fragments_hidden_in_redacted_turn():
    d = _doc([_st("S1", start=0, length=6)], [], answer="家里有事没睡好，所以累")
    d["turns"][0]["sensitiveFragments"] = ["家里有事没睡好"]
    red = {"turns": [{"round": 1, "question": "问？", "answer": MASK + "，所以累"}]}
    rst = dict(d["statements"][0], quote="家里有事没睡好")
    assert router._safe_quote(d, red, rst) == MASK
    red_clear = {"turns": [{"round": 1, "question": "问？", "answer": "家里有事没睡好，所以累"}]}
    assert router._safe_quote(d, red_clear, rst) == "家里有事没睡好"
