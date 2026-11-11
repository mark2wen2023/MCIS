"""W12 页面与截图验收：Layout 补丁仅影响 /analysis；虚构/来源/海力5 说明；截图尺寸。"""
from __future__ import annotations

import re
import subprocess
import os
from pathlib import Path

from conftest import ROOT

LAYOUT = (ROOT / "web/src/Layout.tsx").read_text(encoding="utf-8")
VIEW = (ROOT / "web/src/analysis/AnalysisView.tsx").read_text(encoding="utf-8")
PAGE = (ROOT / "web/src/pages/AnalysisPage.tsx").read_text(encoding="utf-8")
PATCH = (ROOT / "logs/w12-layout.patch").read_text(encoding="utf-8")


def test_layout_patch_only_affects_analysis_route(tmp_path):
    """21:52：Layout.tsx 补丁保留，且只在 /analysis 上回退到分析案例清单。"""
    assert "const onAnalysis = loc.pathname.endsWith('/analysis')" in LAYOUT
    assert "caseForLocation(loc.pathname, params.toString(), CASE_ID)" in LAYOUT
    assert "from './caseContext'" in LAYOUT
    # 404 回退到 /analysis/cases 必须受 onAnalysis 保护，colreg 等其它页不得走这条路径
    assert "if (!onAnalysis)" in LAYOUT
    assert "api.get" in LAYOUT and "/analysis/cases" in LAYOUT
    # 补丁本身声明只改 /analysis
    assert "W12：分析页也按 ?case= 显示当前案件" in PATCH
    # colreg 仍按 ?case= 取案件（原逻辑保留）
    # Execute the real Layout effect with deterministic hook/router stubs and mocked
    # fetch. This is a routing unit test, not a browser rendering claim.
    bundle = tmp_path / "layout.cjs"
    subprocess.run([
        str(ROOT / "web/node_modules/.bin/esbuild"), "src/Layout.tsx", "--bundle",
        "--platform=node", "--format=cjs", "--packages=external", "--jsx=automatic",
        "--log-level=warning", f"--outfile={bundle}",
    ], cwd=ROOT / "web", check=True, timeout=30)
    script = r"""
const assert = require('node:assert/strict');
const Module = require('node:module');
const original = Module._load;
let pathname, effects = [], calls = [], caseFails = true;
Module._load = function(name, ...args) {
  if (name === 'react') return { ...original.call(this, name, ...args),
    useState: x => [x, () => {}], useEffect: fn => effects.push(fn) };
  if (name === 'react-router-dom') return {
    useLocation: () => ({pathname}),
    useSearchParams: () => [new URLSearchParams('case=PUBLIC-CASE')],
    NavLink: () => null, Outlet: () => null };
  return original.call(this, name, ...args);
};
global.localStorage = {getItem: () => null};
global.fetch = async url => {
  calls.push(url);
  if (url.endsWith('/analysis/cases')) return new Response(JSON.stringify({cases: []}));
  return new Response(JSON.stringify({caseId:'PUBLIC-CASE',title:'Public',isFictionalDemo:false}), {status: caseFails ? 404 : 200});
};
const {Layout} = require(process.argv[1]);
(async () => {
  for (const fail of [true, false]) {
    caseFails = fail;
    for (const route of ['analysis','colreg','report','evidence','recs','interview','overview']) {
      pathname = '/' + route; effects = []; calls = [];
      Layout(); const cleanup = effects.map(fn => fn());
      await new Promise(resolve => setTimeout(resolve, 0));
      const bound = ['analysis','colreg','report','evidence','recs'].includes(route);
      const expected = ['/api/v1/cases/' + (bound ? 'PUBLIC-CASE' : 'CASE-2026-DEMO-LILY-MARY')];
      if (fail && route === 'analysis') expected.push('/api/v1/analysis/cases');
      assert.deepEqual(calls, expected, route + ' failure=' + fail);
      cleanup.forEach(fn => fn && fn());
    }
  }
  console.log('Layout case-context / exclusive analysis fallback: 14 scenarios passed');
})().catch(e => {console.error(e); process.exitCode = 1});
"""
    subprocess.run(["node", "-e", script, str(bundle)], cwd=ROOT / "web",
                   env={**os.environ, "NODE_PATH": str(ROOT / "web/node_modules")}, check=True, timeout=30)
    # 分析页切案走 ?case=
    assert "params.get('case')" in PAGE
    assert "onSwitchCase" in VIEW


def test_view_renders_required_labels_and_sources():
    assert "示例数据（虚构）" in VIEW
    assert "真实案例 · 公开报告" in VIEW
    assert "{m.source}" in VIEW  # 关键时刻来源列
    assert 'data-testid="no-whatif"' in VIEW
    assert "{data.notes[0]}" in VIEW
    assert "否（对照）" in VIEW
    assert "Lily / Mary（虚构）" in VIEW
    # 曲线说明会显示 curveNote（含「航向作对地航向」）；【推算】缺失见 D01
    assert "curveNote" in VIEW


def test_screenshots_exist_with_expected_sizes():
    from PIL import Image
    shots = {
        "screenshots/30-analysis-lily-mary.png": (1920, 1080),
        "screenshots/30-analysis-haili5.png": (1920, 1080),
        "screenshots/30-analysis-yangze22.png": (1920, 1080),
        "screenshots/30-analysis-lily-mary-full.png": (1920, 2300),
        "screenshots/30-analysis-haili5-full.png": (1920, 2300),
        "screenshots/30-analysis-yangze22-full.png": (1920, 2300),
        "screenshots/1440/30-analysis-lily-mary-1440.png": (1440, 900),
        "screenshots/1440/30-analysis-haili5-1440.png": (1440, 900),
        "screenshots/1440/30-analysis-yangze22-1440.png": (1440, 900),
    }
    for rel, size in shots.items():
        p = ROOT / rel
        assert p.exists(), rel
        im = Image.open(p)
        assert im.size == size, f"{rel} 实际 {im.size} 期望 {size}"


def test_yangze_1920_screenshot_path_recorded():
    p = ROOT / "screenshots/30-analysis-yangze22.png"
    assert p.exists()
    # 整页长图一并存在，供对照表/天线表/来源区看图
    assert (ROOT / "screenshots/30-analysis-yangze22-full.png").exists()
