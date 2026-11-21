"""Synthetic registered-query preview; creates no service and exports no DB/raw rows."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FROZEN='2eb5d477191e93f8cb0bc2d06dad5cab62528343'

def build(output):
    if output.exists():raise FileExistsError(output)
    for path in ['tools/replay_evidence_workbench/registered_build.py','tools/replay_evidence_workbench/registered.js','tools/replay_evidence_workbench/style.css','tools/replay_evidence_workbench/workbench.html','tests_acceptance/registered-trajectory-pair/business.py','tests_acceptance/registered-trajectory-pair/business_ui.py']:
        if (ROOT/path).read_bytes()!=subprocess.check_output(['git','show',FROZEN+':'+path],cwd=ROOT):raise ValueError('Frozen input changed')
    ui=runpy.run_path(str(HERE/'business_ui.py'));frames=[]
    class Capture:
        def test_capture_finite_query_results(self):
            from mcis_service.trajectory_exchange.registered_query import _query_registered_pair
            for stamp in ['2026-02-01T12:00:20.000Z','2026-02-01T12:01:20.000Z','2026-02-01T12:01:40.000Z','2026-02-01T12:02:04.250Z']:
                frames.append(_query_registered_pair(self.ctx,self.cid,self.pins,'Synthetic preview frame',stamp))
            self.assertEqual(self.counts(),(2,10,10))
    with tempfile.TemporaryDirectory(prefix='registered-preview-') as d:
        source=ui['base']['materialize'](Path(d),ref=ui['PRODUCT'],paths=ui['PATHS'])
        if not ui['base']['run'](source,extra_cases=(Capture,),allowed_paths=ui['PATHS']):raise RuntimeError('Synthetic query checks failed')
        page=Path(d)/'shell.html'
        html=runpy.run_path(str(ROOT/'tools/replay_evidence_workbench/registered_build.py'))['build'](page)
        models=Path(d)/'frames.json';models.write_text(json.dumps(frames))
        # Existing strict UI validator checks actual finite model, no raw payload.
        subprocess.run(['node',str(HERE/'ui.cjs'),str(page),str(models)],check=True)
    controls='''<section class="panel" aria-label="合成预览操作"><p>纯合成临时登记查询结果 · 模拟传输 · 无 HTTP；不是业务入口或持续授权。设备记录未提供，不补造。</p><label>本地暂选 <input id="preview-slider" type="range" min="0" max="3" step="1" value="0" aria-label="本地暂选时点"></label><button id="preview-reset">重新选当前合成案</button><button id="preview-late">演练切案时旧响应迟到</button><p id="preview-count" role="status">模拟查询次数：0</p><p id="preview-event" role="status">未查询；页面操作不写访问审计。</p></section>'''
    html=html.replace('<title>粤海探析 · 复盘与取证</title>','<title>复盘与取证｜登记轨迹 · 合成离线预览</title>').replace('<div class="columns">',controls+'<div class="columns">')
    script=(HERE/'preview_transport.js').read_text().replace('/* FRAMES */',json.dumps(frames,ensure_ascii=True,separators=(',',':')).replace('<','\\u003c'))
    html=html.replace('</body>', '<script>'+script+'</script></body>')
    with output.open('x',encoding='utf-8') as f:f.write(html)
    print(json.dumps({'bytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}))
    return html

if __name__=='__main__':
    if not sys.flags.isolated:raise SystemExit('Use existing reviewed Python -I')
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path)
    build(p.parse_args().output)
