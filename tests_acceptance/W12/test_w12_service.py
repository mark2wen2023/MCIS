"""W12 服务验收：三案例、W14 对比表、关键时刻来源、404/500、虚构标注、海力5 说明、caseId 规则。"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

import pytest

from mcis_service.analysis import router as ar

from conftest import CASE_ID_RE, CASE_IDS, HAILI, H, LILY, ROOT, YANGZE, get_analysis

LOGS = ROOT / "logs"
YCASE = json.loads((ROOT / "reports/yangze22/case.json").read_text(encoding="utf-8"))


def _dump(name: str):
    return json.loads((LOGS / name).read_text(encoding="utf-8-sig"))


def test_list_three_cases_and_meta(client):
    r = client.get("/api/v1/analysis/cases", headers=H())
    assert r.status_code == 200, r.text
    body = r.json()
    assert [c["caseId"] for c in body["cases"]] == CASE_IDS
    assert body["cases"][0]["isFictionalDemo"] is True
    assert body["cases"][1]["isFictionalDemo"] is False
    assert body["cases"][2]["isFictionalDemo"] is False
    assert body["cases"][0]["hasWhatIf"] is True
    assert body["cases"][1]["hasWhatIf"] is False
    assert body["cases"][2]["hasWhatIf"] is True
    assert body["seedVerified"] is True
    assert body["seedSha256"] == hashlib.sha256(ar.SEED.read_bytes()).hexdigest()
    assert body["crossCheck"]["ok"] is True
    assert body["crossCheck"]["maxAbsDiff"] <= 1e-6
    assert body["timeZone"] if "timeZone" in body else True


def test_yangze_case_id_is_canonical_and_valid():
    assert YCASE["caseId"] == YANGZE
    assert re.match(CASE_ID_RE, YANGZE)
    # 与 EvidenceItem.IsValidCaseId 同一条规则：至少 3 位，仅 A-Za-z0-9._-
    assert re.match(CASE_ID_RE, LILY) and re.match(CASE_ID_RE, HAILI)
    assert not re.match(CASE_ID_RE, "ab")  # 过短
    assert not re.match(CASE_ID_RE, "CJK 2024")  # 空格非法
    assert not re.match(CASE_ID_RE, "CJK-2024-1230-YangZe22-VegaDream\n")


def test_analysis_serves_canonical_yangze_id(client):
    c = get_analysis(client, YANGZE)
    assert c["caseId"] == YANGZE
    # 也允许用 key 查询
    by_key = get_analysis(client, "yangze22")
    assert by_key["caseId"] == YANGZE
    # W16 占位编号不应作为分析页案例 id 出现
    r = client.get("/api/v1/cases/CASE-REAL-YANGZE22/analysis", headers=H())
    assert r.status_code == 404 and r.json()["code"] == "analysis_case_not_found"


def test_unknown_case_404(client):
    r = client.get("/api/v1/cases/NOPE/analysis", headers=H())
    assert r.status_code == 404
    body = r.json()
    assert body["code"] == "analysis_case_not_found"
    assert set(body["detail"]["available"]) == set(CASE_IDS)


def test_tampered_seed_returns_500(tmp_path, monkeypatch, client):
    seed = tmp_path / "s.json"
    side = tmp_path / "s.sha256"
    shutil.copy(ar.SEED, seed)
    shutil.copy(ar.SIDECAR, side)
    raw = seed.read_bytes().replace(b'"isCritical":true', b'"isCritical":false', 1)
    assert raw != seed.read_bytes()
    seed.write_bytes(raw)
    # load_seed 的默认 path/sidecar 在定义时绑定，不能只改模块常量；改走函数本身。
    orig = ar.load_seed
    def _load(path=seed, sidecar=side):
        return orig(path, sidecar)
    monkeypatch.setattr(ar, "load_seed", _load)
    ar._cache.clear()
    r = client.get("/api/v1/analysis/cases", headers=H())
    assert r.status_code == 500, r.text
    assert r.json()["code"] == "analysis_seed_tampered"
    r2 = client.get(f"/api/v1/cases/{LILY}/analysis", headers=H())
    assert r2.status_code == 500 and r2.json()["code"] == "analysis_seed_tampered"
    ar._cache.clear()


def test_every_key_moment_has_source(client):
    for cid in CASE_IDS:
        c = get_analysis(client, cid)
        moments = list(c["baseline"]["keyMoments"])
        if c["whatif"]:
            for row in c["whatif"]["rows"]:
                moments.extend(row["keyMoments"])
        assert moments, cid
        for m in moments:
            assert m.get("source"), f"{cid} {m}"
            assert m.get("clock") and m.get("label") and m.get("kind")


def test_fictional_flags_and_labels(client):
    lily = get_analysis(client, LILY)
    haili = get_analysis(client, HAILI)
    yangze = get_analysis(client, YANGZE)
    assert lily["isFictionalDemo"] is True
    assert "虚构" in lily["sourceLabel"] or "虚构" in lily["title"]
    assert haili["isFictionalDemo"] is False and yangze["isFictionalDemo"] is False
    assert "公开" in haili["sourceLabel"] and "公开" in yangze["sourceLabel"]


def test_haili5_explains_missing_w14(client):
    c = get_analysis(client, HAILI)
    assert c["whatif"] is None
    joined = " ".join(c["notes"])
    assert "W14" in joined and ("无" in joined or "没有" in joined)


def test_yangze_baseline_notes_s0_source(client):
    c = get_analysis(client, YANGZE)
    joined = " ".join(c["notes"]) + c["baseline"]["label"]
    assert "S0" in joined and ("报告航迹" in joined or "未接入服务数据库" in joined)
    assert "【估计】" in c["baseline"]["label"]  # 天线位置


def test_yangze_w14_table_matches_retest_logs_and_known_values(client):
    y = {r["id"]: r for r in get_analysis(client, YANGZE)["whatif"]["rows"]}
    sens = _dump("w14.2-retest-sensitivity-dump.json")
    scen = {r["id"]: r for r in _dump("w14.2-retest-scenario-dump.json")["yangze22"]["results"]}
    for r in sens["default"]["results"]:
        assert y[r["id"]]["minClearanceM"] == pytest.approx(r["minClearanceM"], abs=1e-9)
        assert y[r["id"]]["minClearanceTimeSeconds"] == pytest.approx(r["minClearanceTime"], abs=1e-9)
        assert y[r["id"]]["verdict"] == r["verdict"]
    # 验收任务给出的已知结果
    assert y["S0"]["collision"] is True
    assert y["S0"]["tcLocal"] == scen["S0"]["tcLocal"] == "22:02:00.12"
    assert y["S0"]["collisionAngleText"] == "69°"
    assert y["Y1"]["isCritical"] is True
    assert y["Y1"]["displayVerdictText"] == "险情（临界）"
    assert y["Y1"]["minClearanceM"] == pytest.approx(184.35, abs=5e-3)
    assert y["Y5"]["collision"] is False and y["Y5"]["displayVerdictText"] == "无碰撞"
    assert y["Y5"]["minClearanceM"] == pytest.approx(238.75, abs=5e-3)
    assert y["Y1+Y5"]["minClearanceM"] == pytest.approx(292.45, abs=5e-3)
    assert y["Y4"]["minClearanceM"] == pytest.approx(29.81, abs=5e-3)
    assert [k for k, r in y.items() if r["isCritical"]] == ["Y1"]


def test_demo_w14_matches_retest_logs(client):
    d = {r["id"]: r for r in get_analysis(client, LILY)["whatif"]["rows"]}
    for r in _dump("w14.2-retest-scenario-dump.json")["demo"]["results"]:
        assert d[r["id"]]["minClearanceM"] == pytest.approx(r["minClearanceM"], abs=1e-9)
        assert d[r["id"]]["tcLocal"] == r["tcLocal"]


def test_antenna_unmodified_row_is_control(client):
    ant = get_analysis(client, YANGZE)["whatif"]["antennaSensitivity"]
    controls = [a for a in ant if not a["inEstimateRange"]]
    assert controls, "应有不计入估计范围的对照行"
    assert any("不改正" in a["label"] or a["yangzeAftRatio"] == 0 for a in controls)


@pytest.mark.knowndefect
def test_W12_D01_heading_as_cog_marked_derived(client):
    """21:52 裁定：航向当对地航向须在页面标【推算】。当前 curveNote / assumptions 只写「航向作对地航向」，未加【推算】。"""
    for cid in (LILY, YANGZE):
        w = get_analysis(client, cid)["whatif"]
        blob = " ".join([w.get("curveNote") or "", *(w.get("assumptions") or []), w.get("disclaimer") or ""])
        assert "航向" in blob and "对地航向" in blob
        assert "【推算】" in blob, f"{cid} 将航向作对地航向处未标【推算】：{w.get('curveNote')}"
