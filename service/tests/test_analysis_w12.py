"""W12 分析页：种子完整性、三案例、与 W14.2 留档逐项一致、曲线可由 mcis-core 复算。"""
import hashlib
import json
import shutil

import pytest

from mcis_service.analysis import router as ar
from mcis_service.colreg import core_client
from mcis_service.config import PROJECT_ROOT, Settings

from .conftest import H, HAS_DOTNET

LOGS = PROJECT_ROOT / "logs"
YCASE = json.loads((PROJECT_ROOT / "reports/yangze22/case.json").read_text(encoding="utf-8"))
EXPECTED_IDS = ["CASE-2026-DEMO-LILY-MARY", "CASE-2025-HAILI5-WANA17", YCASE["caseId"]]


def _dump(name):
    return json.loads((LOGS / name).read_text(encoding="utf-8-sig"))


def _get(client, cid):
    r = client.get(f"/api/v1/cases/{cid}/analysis", headers=H())
    assert r.status_code == 200, r.text
    return r.json()


def test_list_three_cases_with_source_flags(client):
    r = client.get("/api/v1/analysis/cases", headers=H())
    assert r.status_code == 200
    body = r.json()
    assert [c["caseId"] for c in body["cases"]] == EXPECTED_IDS
    flags = {c["caseId"]: c["isFictionalDemo"] for c in body["cases"]}
    assert flags == {EXPECTED_IDS[0]: True, EXPECTED_IDS[1]: False, EXPECTED_IDS[2]: False}
    assert body["seedVerified"] is True
    assert body["seedSha256"] == hashlib.sha256(ar.SEED.read_bytes()).hexdigest()
    assert body["crossCheck"]["ok"] and body["crossCheck"]["maxAbsDiff"] <= 1e-6


@pytest.mark.parametrize("cid", EXPECTED_IDS)
def test_each_case_has_curves_and_key_moments(client, cid):
    c = _get(client, cid)
    s = c["baseline"]["series"]
    assert len(s) > 50
    for p in s:
        assert set(("t", "clock", "distanceNm", "dcpaNm", "tcpaMin", "riskLevel")) <= set(p)
    assert [p["t"] for p in s] == sorted(p["t"] for p in s)
    kinds = {m["kind"] for m in c["baseline"]["keyMoments"]}
    assert "collision" in kinds and "minDcpa" in kinds
    assert c["sourceLabel"] and c["sourceRefs"]
    assert c["timeZone"] == "UTC+8"


def test_whatif_presence(client):
    assert _get(client, EXPECTED_IDS[0])["whatif"]["rows"]
    assert _get(client, EXPECTED_IDS[1])["whatif"] is None
    y = _get(client, EXPECTED_IDS[2])["whatif"]
    assert [r["id"] for r in y["rows"]] == [r["id"] for r in _dump("w14.2-retest-scenario-dump.json")["yangze22"]["results"]]


def test_yangze_numbers_match_w14_retest_logs(client):
    y = {r["id"]: r for r in _get(client, EXPECTED_IDS[2])["whatif"]["rows"]}
    sens = _dump("w14.2-retest-sensitivity-dump.json")
    for r in sens["default"]["results"]:
        assert y[r["id"]]["minClearanceM"] == pytest.approx(r["minClearanceM"], abs=1e-9)
        assert y[r["id"]]["minClearanceTimeSeconds"] == pytest.approx(r["minClearanceTime"], abs=1e-9)
        assert y[r["id"]]["verdict"] == r["verdict"]
        assert y[r["id"]]["safeDistanceM"] == pytest.approx(sens["safeM"])
    assert y["Y1"]["isCritical"] is sens["default"]["y1Critical"] is True
    assert y["Y1"]["displayVerdictText"] == sens["default"]["y1Display"]
    assert y["Y1"]["sensitivityRangeText"] == sens["default"]["y1Range"]
    assert [k for k, r in y.items() if r["isCritical"]] == ["Y1"]
    scen = {r["id"]: r for r in _dump("w14.2-retest-scenario-dump.json")["yangze22"]["results"]}
    assert y["S0"]["tcLocal"] == scen["S0"]["tcLocal"]
    assert y["S0"]["collision"] is True


def test_antenna_sensitivity_matches_logs(client):
    y = _get(client, EXPECTED_IDS[2])["whatif"]
    ant = {(a["yangzeAftRatio"], a["vegaAftRatio"]): a for a in y["antennaSensitivity"]}
    for s in _dump("w14.2-retest-sensitivity-dump.json")["sensitivity"]:
        a = ant[(s["yangzeAft"], s["vegaAft"])]
        assert a["inEstimateRange"] == s["inEstimateRange"]
        for r in s["results"]:
            assert a["outcomes"][r["id"]]["minClearanceM"] == pytest.approx(r["minClearanceM"], abs=1e-9)
            assert a["outcomes"][r["id"]]["verdict"] == r["verdict"]


def test_demo_numbers_match_logs(client):
    d = {r["id"]: r for r in _get(client, EXPECTED_IDS[0])["whatif"]["rows"]}
    for r in _dump("w14.2-retest-scenario-dump.json")["demo"]["results"]:
        assert d[r["id"]]["minClearanceM"] == pytest.approx(r["minClearanceM"], abs=1e-9)
        assert d[r["id"]]["tcLocal"] == r["tcLocal"]


def test_collision_curves_cut_at_contact_and_key_moment_clock(client):
    for cid in (EXPECTED_IDS[0], EXPECTED_IDS[2]):
        for r in _get(client, cid)["whatif"]["rows"]:
            mk = {m["kind"]: m for m in r["keyMoments"]}
            assert mk["minClearance"]["value"] == r["minClearanceM"]
            if r["collision"]:
                assert r["series"][-1]["t"] <= r["tcSeconds"] + 1e-9
                assert mk["collision"]["clock"] == r["tcLocal"]
            else:
                # 未碰撞：mcis-core 曲线最小中心距与 W14 最小中心距吻合（2 s 采样，容差 2e-3 nm）
                assert min(p["distanceNm"] for p in r["series"]) == pytest.approx(r["minDistanceNm"], abs=2e-3)


def test_unknown_case_404(client):
    r = client.get("/api/v1/cases/NOPE/analysis", headers=H())
    assert r.status_code == 404 and r.json()["code"] == "analysis_case_not_found"


def test_tampered_seed_rejected(tmp_path):
    seed = tmp_path / "s.json"
    side = tmp_path / "s.sha256"
    shutil.copy(ar.SEED, seed)
    shutil.copy(ar.SIDECAR, side)
    ar.load_seed(seed, side)
    seed.write_bytes(seed.read_bytes().replace(b'"isCritical":true', b'"isCritical":false', 1))
    with pytest.raises(Exception) as e:
        ar.load_seed(seed, side)
    assert getattr(e.value, "status_code", None) == 500


def test_seed_sources_not_stale():
    doc, _ = ar.load_seed()
    refs = [doc["w14Export"], doc["w14Frozen"], doc["coreDll"]] + [r for c in doc["cases"] for r in c["sourceRefs"]]
    for path, sha in doc["crossCheck"]["sha256"].items():
        refs.append({"path": path, "sha256": sha})
    for r in refs:
        p = PROJECT_ROOT / r["path"]
        assert hashlib.sha256(p.read_bytes()).hexdigest() == r["sha256"], f"种子已过期：{r['path']} 已变化，请重跑 build_seed"


def test_extension_routes_hidden_until_contract(app, client):
    paths = app.openapi()["paths"]
    for _m, p in ar.EXTENSION_ROUTES:
        assert p.replace("{case_id}", "{caseId}") not in paths and p not in paths
    actual = {(m.upper(), r.path) for r in ar.router.routes for m in r.methods}
    assert actual == set(ar.EXTENSION_ROUTES)
    assert client.get("/api/v1/analysis/cases", headers=H()).status_code == 200


@pytest.mark.skipif(not HAS_DOTNET, reason="需要 dotnet + mcis-core")
def test_whatif_curve_reproducible_with_mcis_core(client):
    y = _get(client, EXPECTED_IDS[2])["whatif"]
    export = json.loads((ar.DATA / "w12-w14-export.json").read_text(encoding="utf-8"))
    row = next(r for r in export["yangze22"]["rows"] if r["id"] == "Y1")
    seed_row = next(r for r in y["rows"] if r["id"] == "Y1")
    own, tgt = y["ownVesselId"], y["targetVesselId"]
    a = {int(round(s[0])): s for s in row["tracks"][own]["samples"]}
    b = {int(round(s[0])): s for s in row["tracks"][tgt]["samples"]}
    picks = [seed_row["series"][i] for i in (0, len(seed_row["series"]) // 2, -1)]
    pairs = []
    for p in picks:
        k = int(round(p["t"]))
        pairs.append({"pairId": str(k), "timeSec": p["t"],
                      "own": {"eastNm": a[k][1] / 1852, "northNm": a[k][2] / 1852, "speedKn": a[k][4], "courseDeg": a[k][3] % 360},
                      "target": {"eastNm": b[k][1] / 1852, "northNm": b[k][2] / 1852, "speedKn": b[k][4], "courseDeg": b[k][3] % 360}})
    env = core_client.run(Settings().core_cmd, "cpa", {"pairs": pairs})
    for p, r in zip(picks, env["result"]["results"]):
        assert r["currentDistanceNm"] == pytest.approx(p["distanceNm"], abs=1e-6)
        assert r["dcpaNm"] == pytest.approx(p["dcpaNm"], abs=1e-6)


@pytest.mark.skipif(not HAS_DOTNET, reason="需要 dotnet + mcis-core")
def test_db_baseline_matches_live_cpa_endpoint(client):
    c = _get(client, EXPECTED_IDS[1])
    live = client.get(f"/api/v1/cases/{EXPECTED_IDS[1]}/cpa?stepSec={c['baseline']['stepSec']:g}", headers=H())
    assert live.status_code == 200
    lr = {r["timeSec"]: r for r in live.json()["results"]}
    for p in c["baseline"]["series"][::10]:
        assert lr[p["t"]]["dcpaNm"] == pytest.approx(p["dcpaNm"], abs=1e-6)
        assert lr[p["t"]]["currentDistanceNm"] == pytest.approx(p["distanceNm"], abs=1e-6)
