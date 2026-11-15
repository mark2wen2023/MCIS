from .conftest import C, CASE, H


def test_case_list_and_get(client):
    cases = client.get("/api/v1/cases").json()
    assert cases[0]["caseId"] == CASE and cases[0]["isFictionalDemo"] is True
    c = client.get(C).json()
    assert c["caseEpochUtc"] == "2026-05-18T06:15:00Z"      # 14:15 北京时间
    assert c["incidentTimeUtc"] == "2026-05-18T06:24:00Z"   # 14:24 碰撞
    assert c["durationSec"] == 720
    assert client.get("/api/v1/cases/NOPE").status_code == 404


def test_create_case_audited(client):
    body = dict(client.get(C).json())
    body.update({"caseId": "CASE-TEST-1", "title": "测试案件（虚构）"})
    assert client.post("/api/v1/cases", json=body, headers=H()).status_code == 201
    assert client.post("/api/v1/cases", json=body, headers=H()).status_code == 409
    a = client.get("/api/v1/cases/CASE-TEST-1/audit", headers=H()).json()
    assert a[0]["action"] == "case.create" and a[0]["seq"] == 1
    assert client.post("/api/v1/cases", json={**body, "caseId": "CASE-TEST-2"}, headers=H("ExternalExpert")).status_code == 403


def test_tracks_resample_and_collision_geometry(client):
    r = client.get(f"{C}/tracks", params={"stepSec": 60, "fromSec": 0, "toSec": 540}).json()
    for t in r["tracks"]:
        assert len(t["points"]) == 10
        assert t["points"][0]["utc"] == "2026-05-18T06:15:00Z"
    lily = {p["timeSec"]: p for p in r["tracks"][0]["points"]}
    mary = {p["timeSec"]: p for p in r["tracks"][1]["points"]}
    # 碰撞时刻两船参考点相距 < 100 m
    dlat = (lily[540]["latDeg"] - mary[540]["latDeg"]) * 111320
    assert abs(dlat) < 100


def test_overview_counts(client):
    c = client.get(f"{C}/overview").json()["counts"]
    assert c["evidence"] == 6 and c["interviews"] == 6 and c["recommendations"] == 7 and c["conflictsOpen"] == 2


def test_timeline_filter_add(client):
    tl = client.get(f"{C}/timeline").json()
    assert tl["events"] == sorted(tl["events"], key=lambda e: (e["timeSec"], e["eventId"]))
    col = [e for e in tl["events"] if e["title"] == "两船发生碰撞"][0]
    assert col["timeSec"] == 540 and col["utc"] == "2026-05-18T06:24:00Z"
    win = client.get(f"{C}/timeline", params={"fromSec": 430, "toSec": 470}).json()["events"]
    assert any(e["title"] == "Mary 轮违规左转" for e in win)
    r = client.post(f"{C}/timeline/events", json={"timeSec": 600, "title": "拖轮到达（虚构）", "kind": "Event"}, headers=H())
    assert r.status_code == 201 and r.json()["utc"] == "2026-05-18T06:25:00Z"
    assert client.post(f"{C}/timeline/events", json={"timeSec": 1, "title": "x", "kind": "Event"}, headers=H("ExternalExpert")).status_code == 403


def test_conflicts_patch_audited(client):
    cs = client.get(f"{C}/conflicts").json()
    assert [c["conflictId"] for c in cs] == ["C-01", "C-02", "C-03", "C-04"]
    editable = client.get(f"{C}/conflicts:editable", headers=H()).json()
    version = next(row["version"] for row in editable if row["conflict"]["conflictId"] == "C-01")
    r = client.patch(f"{C}/conflicts/C-01", json={"status": "Resolved", "resolution": "补充询问后确认 14:22:15", "expectedVersion": version}, headers=H())
    assert r.status_code == 200 and r.json()["status"] == "Resolved"
    last = client.get(f"{C}/audit", params={"entityId": "C-01"}).json()[-1]
    assert last["action"] == "conflict.update" and "PendingInterview" in last["before"] and "Resolved" in last["after"]
    assert client.patch(f"{C}/conflicts/C-01", json={"status": "Bogus"}).status_code == 422
