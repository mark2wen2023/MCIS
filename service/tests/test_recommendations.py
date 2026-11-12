from .conftest import C, H as identity_headers
import pytest
from fastapi.testclient import TestClient
from mcis_service.config import Settings
from mcis_service.main import create_app
from mcis_service.seed.lily_mary import seed

# W7 original-content compatibility tightening: business lifecycle runs as an
# already-authorized lead; no policy grant and no weakening of denial assertions.
def H(role="LeadInvestigator", operator=None):
    return identity_headers(role, operator)

@pytest.fixture
def client(tmp_path):
    app = create_app(Settings(data_dir=tmp_path, seed_demo=False))
    with app.state.db.session() as s: seed(s, app.state.settings.blob_dir)
    with TestClient(app) as client: yield client



def _rec(client, rid):
    return client.get(f"{C}/recommendations/{rid}", headers=H()).json()


def test_board_four_columns(client):
    b = client.get(f"{C}/recommendations:board", headers=H()).json()
    cols = {c["key"]: c for c in b["columns"]}
    assert [c["title"] for c in b["columns"]] == ["草拟", "已发布", "落实中", "已关闭"]
    assert cols["Closed"]["statuses"] == ["Implemented", "NotAdopted", "Closed"]
    assert {r["id"] for r in cols["InProgress"]["items"]} == {"SR-2026-03", "SR-2026-04"}
    assert all(r["column"] == k for k, c in cols.items() for r in c["items"])
    assert b["allowed"]["Issued"] == ["Responded"]


def test_full_lifecycle_and_audit(client):
    r = client.post(f"{C}/recommendations", json={"title": "测试建议（虚构）", "addressee": "星屿 VTS（虚构）",
                                                 "causeNodeIds": ["COLREG-R19"], "dueUtc": "2099-01-01T00:00:00Z"}, headers=H())
    assert r.status_code == 201
    rid = r.json()["id"]
    assert rid == "SR-2026-08" and r.json()["status"] == "Draft" and r.json()["progressPct"] == 0
    # 内容修改只在 Draft；进度只在 Responded
    assert client.patch(f"{C}/recommendations/{rid}", json={"title": "改名"}, headers=H()).status_code == 200
    assert client.patch(f"{C}/recommendations/{rid}", json={"progressPct": 10}, headers=H()).status_code == 409
    assert client.post(f"{C}/recommendations/{rid}:transition", json={"to": "Issued"}, headers=H()).json()["status"] == "Issued"
    assert client.patch(f"{C}/recommendations/{rid}", json={"title": "再改"}, headers=H()).status_code == 409
    # Responded 只能经回复
    x = client.post(f"{C}/recommendations/{rid}:transition", json={"to": "Responded"}, headers=H())
    assert x.status_code == 409 and x.json()["code"] == "safetyrec_illegal_transition"
    r = client.post(f"{C}/recommendations/{rid}/responses", json={"party": "星屿 VTS", "text": "接受"}, headers=H())
    assert r.status_code == 201 and r.json()["status"] == "Responded" and r.json()["responseSummary"] == "接受"
    assert client.patch(f"{C}/recommendations/{rid}", json={"progressPct": 101}, headers=H()).status_code == 422
    assert client.patch(f"{C}/recommendations/{rid}", json={"progressPct": 40, "note": "完成培训一批"}, headers=H()).json()["progressPct"] == 40
    # 非法：Responded → Draft
    assert client.post(f"{C}/recommendations/{rid}:transition", json={"to": "Draft"}, headers=H()).status_code == 409
    # NotAdopted 必须理由
    assert client.post(f"{C}/recommendations/{rid}:transition", json={"to": "NotAdopted"}, headers=H()).status_code == 422
    r = client.post(f"{C}/recommendations/{rid}:transition", json={"to": "Implemented", "note": "现场核实"}, headers=H()).json()
    assert r["progressPct"] == 100 and r["verificationNote"] == "现场核实" and r["column"] == "Closed"
    r = client.post(f"{C}/recommendations/{rid}:transition", json={"to": "Closed"}, headers=H()).json()
    assert r["status"] == "Closed" and [h["to"] for h in r["history"]] == ["Issued", "Responded", "Implemented", "Closed"]
    assert client.post(f"{C}/recommendations/{rid}/responses", json={"party": "a", "text": "b"}, headers=H()).status_code == 409

    hist = client.get(f"{C}/recommendations/{rid}/history", headers=H()).json()
    assert [a["action"] for a in hist] == ["safetyrec.create", "safetyrec.update", "safetyrec.transition", "safetyrec.response",
                                          "safetyrec.progress", "safetyrec.transition", "safetyrec.transition"]
    prog = hist[4]
    assert prog["command"] == f"更新落实进度 {rid}" and prog["before"] == "0%" and prog["after"] == "40%；完成培训一批"
    assert hist[3]["before"] == "Issued" and hist[3]["after"] == "Responded；回复方=星屿 VTS"


def test_create_validation(client):
    base = {"title": "x", "addressee": "y", "causeNodeIds": ["N1"], "dueUtc": "2099-01-01T00:00:00Z"}
    assert client.post(f"{C}/recommendations", json={**base, "causeNodeIds": []}, headers=H()).status_code == 422
    assert client.post(f"{C}/recommendations", json={**base, "id": "SR-01"}, headers=H()).json()["code"] == "safetyrec_invalid_id"
    assert client.post(f"{C}/recommendations", json={**base, "id": "SR-2026-01"}, headers=H()).status_code == 409
    assert client.post(f"{C}/recommendations", json={**base, "dueUtc": "2020-01-01T00:00:00Z"}, headers=H()).status_code == 422
    assert client.post(f"{C}/recommendations", json=base, headers=H("ExternalExpert")).status_code == 403


def test_consultation_rounds(client):
    rounds = client.get(f"{C}/consultation/rounds", headers=H()).json()
    assert [r["roundNo"] for r in rounds] == [1, 2]
    r1, r2 = rounds
    assert r1["isClosed"] and r1["allReplied"] and {p["partyId"]: p["status"] for p in r1["partyStatus"]}["CO-MARY"] == "Waived"
    assert not r2["isClosed"] and 12 <= r2["daysRemaining"] <= 13
    assert client.post(f"{C}/consultation/rounds", json={"draftVersion": "v2", "parties": [{"partyId": "A", "name": "a"}]},
                       headers=H()).json()["code"] == "consultation_round_open"
    # 期限未到且有方未回复：不可关闭
    assert client.post(f"{C}/consultation/rounds/2:close", headers=H()).json()["code"] == "consultation_cannot_close"
    pending = next(c for c in r2["comments"] if c["decision"] == "Pending")
    assert client.patch(f"{C}/consultation/rounds/2/comments/{pending['commentId']}", json={"decision": "NotAdopted"},
                        headers=H()).status_code == 422
    ok = client.patch(f"{C}/consultation/rounds/2/comments/{pending['commentId']}", json={"decision": "Adopted"}, headers=H())
    assert ok.status_code == 200
    assert client.patch(f"{C}/consultation/rounds/2/comments/{pending['commentId']}", json={"decision": "Adopted"},
                        headers=H()).json()["code"] == "consultation_already_decided"
    r = client.post(f"{C}/consultation/rounds/2/replies", json={"partyId": "FLAG-B", "text": "意见", "comments": ["c1", "c2"]}, headers=H())
    assert r.status_code == 201
    assert client.post(f"{C}/consultation/rounds/2/replies", json={"partyId": "FLAG-B", "text": "again"}, headers=H()).status_code == 409
    assert client.post(f"{C}/consultation/rounds/2/waivers", json={"partyId": "CO-MARY", "reason": "无意见"}, headers=H()).status_code == 201
    closed = client.post(f"{C}/consultation/rounds/2:close", headers=H())
    assert closed.status_code == 200 and closed.json()["isClosed"]
    new = client.post(f"{C}/consultation/rounds", json={"draftVersion": "v1.3", "parties": [{"partyId": "FLAG-A", "name": "A"}],
                                                       "draftSha256": "a" * 64}, headers=H()).json()
    assert new["roundNo"] == 3 and new["daysRemaining"] == 30
    acts = [a["action"] for a in client.get(f"{C}/audit", params={"category": "Consultation"}, headers=H()).json()]
    assert acts == ["consultation.decide", "consultation.reply", "consultation.waive", "consultation.close", "consultation.open"]
