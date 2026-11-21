"""Explicit local display-only artifact; synthetic registration, no server/browser.
Existing fixed host/B validation precedes the allowlisted display projection.
"""
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
FIXED='654539f3c66e27ae98264b2abbbc5a87de0db138'

def build(output):
    if output.exists():raise FileExistsError('Output must be new')
    paths=['tools/replay_evidence_workbench/'+n for n in ('registered_build.py','registered.js','style.css','workbench.html')]
    paths+=['tests_acceptance/registered-trajectory-pair/'+n for n in ('display_projection.py','display_ui.py','display_ui.cjs','seat_handoff.py','preview_transport.js')]
    paths+=['tests_acceptance/registered-trajectory-pair/seat_receiver/'+n for n in ('run.py','check.py','receiver.py','fixed_objects.py','README.md')]
    for rel in paths:
        if (ROOT/rel).read_bytes()!=subprocess.check_output(['git','show',FIXED+':'+rel],cwd=ROOT):raise ValueError('Fixed source differs: '+rel)
    helper=runpy.run_path(str(HERE/'display_ui.py'))
    dependencies=helper['load']('fixed_objects').fixed_dependencies(ROOT)
    receiver=helper['load']('receiver')
    projection=runpy.run_path(str(HERE/'display_projection.py'))['project']
    captured=[];private=[]
    def consume(record):
        safe=projection(record,validate_host_record=lambda r:receiver.consumer(r,dependencies=dependencies))
        wire=json.dumps(safe)
        for row in record['frames'][0]['vessels']:
            for key in ('evidenceId','requestDigest','sourceSha256'):
                value=row['original'][key];assert value not in wire;private.append(value)
        captured.append(safe)
    if not runpy.run_path(str(HERE/'seat_handoff.py'))['run_handoff'](consume):raise RuntimeError('Host checks failed')
    if len(captured)!=1:raise RuntimeError('Exactly one verified handoff required')
    safe=captured[0]
    for key in ('original','pins','evidenceId','requestDigest','sourceSha256'):assert key not in json.dumps(safe)
    with tempfile.TemporaryDirectory(prefix='display-preview-') as temp:
        shell=Path(temp)/'shell.html'
        html=runpy.run_path(str(ROOT/'tools/replay_evidence_workbench/registered_build.py'))['build'](shell,display_only=True)
        subprocess.run(['node',str(HERE/'display_ui.cjs'),str(shell)],input=json.dumps(safe),text=True,check=True)
    controls='''<section class="panel" aria-label="合成预览操作"><p>纯合成回读展示 · 模拟传输 · 无 HTTP；不是业务入口、登录或授权。校时依据未交付、人审未签。</p><label>本地暂选 <input id="preview-slider" type="range" min="0" max="1" step="1" value="0" aria-label="本地暂选时点"></label><button id="preview-reset">重新选当前合成案</button><button id="preview-late">演练离开当前案后旧响应迟到</button><p id="preview-count" role="status">模拟查询次数：0</p><p id="preview-event" role="status">未查询；页面操作不写访问审计。</p></section>'''
    html=html.replace('<title>粤海探析 · 复盘与取证</title>','<title>复盘与取证｜登记轨迹 · 去 pin 合成验收</title>').replace('<div class="columns">',controls+'<div class="columns">')
    transport=(HERE/'preview_transport.js').read_text()
    changes={"pins:frames[0].vessels.map(v=>v.original)":"vesselIds:frames[0].vessels.map(v=>v.vesselId)","||JSON.stringify(q.pins)!==JSON.stringify(config.pins)":"||Object.keys(q).sort().join('|')!=='alignedUtc|caseId'",'/* FRAMES */':json.dumps(safe['frames'],ensure_ascii=True,separators=(',',':')).replace('<','\\u003c')}
    for before,after in changes.items():
        if transport.count(before)!=1:raise ValueError('Transport shape changed')
        transport=transport.replace(before,after)
    assert 'pins' not in transport and 'original' not in transport
    html=html.replace('</body>','<script>'+transport+'</script></body>')
    for value in private:assert value not in html
    with output.open('x',encoding='utf-8') as f:f.write(html)
    print(json.dumps({'bytes':len(html.encode()),'sha256':hashlib.sha256(html.encode()).hexdigest(),'browserRun':False}))
    return html

if __name__=='__main__':
    if not sys.flags.isolated:raise SystemExit('Use Python -I -B')
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path)
    build(p.parse_args().output)
