"""W6 独立验收：web ColregView 静态渲染（合成数据），由 web/run_web.mjs 打包运行，每个场景单独计数。"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
CASES = [
    "W01_disclaimer_banner_fixed", "W02_band_dangerStage_shown", "W03_band_doubt_shown_with_reason",
    "W04_band_vesselStatus_shown", "W05_needsreview_vs_notassessable_distinct", "W06_notassessable_vs_undetermined_distinct",
    "W07_legend_explains_both", "W08_every_check_row_shows_evidence", "W09_selected_check_has_evidence_link",
    "W10_dangling_evidence_flagged", "W11_audit_panel_who_when_before_after_reason", "W12_review_controls_present",
    "W13_switcher_fictional_and_public", "W14_mode_tag_fictional_vs_public", "W15_public_mode_source_tags_visible",
    "W16_selected_check_shows_source",
    "W17_dcpa_tcpa_chart_and_vessel_rows",
    "W18_pivot_and_actions_table",
    "W19_draft_button_and_404_notice",
    "W20_service_addr_from_prop",
]
KNOWN = {}  # W6-D05（W10 悬空证据）W6.1 已补「未登记」标记


@pytest.fixture(scope="module")
def web_results():
    out = subprocess.run(["node", str(HERE / "web" / "run_web.mjs")], capture_output=True, text=True, timeout=120, check=True)
    return json.loads(out.stdout)


@pytest.mark.parametrize("name", [pytest.param(n, marks=pytest.mark.knowndefect) if n in KNOWN else n for n in CASES])
def test_web_view(web_results, name):
    assert name in web_results, f"web 用例未执行：{name}"
    r = web_results[name]
    assert r["ok"], r["msg"]
