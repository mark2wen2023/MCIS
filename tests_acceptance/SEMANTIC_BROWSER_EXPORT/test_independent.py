"""Independent acceptance: offline script/CLI boundary, not browser-engine QA."""
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / 'research/semantic_support'
sys.path.insert(0, str(ROOT))
import export_review as exporter
import render_browser_review as browser

NODE = r'''
const vm=require('node:vm');
const input=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
let onClick, blobs=[], urls=[], status={}, count=0, removed=0, timers=[];
const fields=input.template.items.map((item,i)=>({
 querySelectorAll:()=>input.mode==='missing'&&i===0?[]:[0,1,2].map(j=>({checked:j===i%3})),
 querySelector:()=>({value:`备注 ${i} <script> & \n😀`,focus(){}})
}));
const doc={getElementById:id=>id==='worksheet-template'?{textContent:JSON.stringify(input.template)}:id==='download-status'?status:{addEventListener:(e,f)=>onClick=f},querySelectorAll:()=>fields,
addEventListener(){},body:{appendChild(){}},createElement:()=>({click(){count++},remove(){removed++}})};
const context={document:doc,Blob,URL:{createObjectURL(blob){if(input.mode==='url-fail')throw Error('storage denied');blobs.push(blob);return 'blob:local'},revokeObjectURL(u){urls.push(u)}},setTimeout:f=>timers.push(f)};
vm.runInNewContext(input.script, context);
(async()=>{if(count!==0)throw Error('automatic download');onClick();onClick();timers.forEach(f=>f());console.log(JSON.stringify({count,removed,status:status.textContent,urls,results:await Promise.all(blobs.map(b=>b.text()))}));})();
'''


def fixture():
    c, cs = exporter.load(ROOT / 'jiangxin9-provisional.json')
    p, ps = exporter.load(ROOT / 'jiangxin9-real-predictions.json')
    return c, cs, p, ps


def run(mode='normal'):
    args = fixture()
    page = browser.render_browser(*args).decode()
    template = json.loads(re.search(r'<script id="worksheet-template" type="application/json">(.*?)</script>', page, re.S)[1])
    script = re.search(r'<script>(.*?)</script>', page, re.S)[1]
    result = subprocess.run(['node', '-e', NODE], input=json.dumps({'template': template, 'script': script, 'mode': mode}), capture_output=True, text=True, check=True, timeout=10)
    return args, json.loads(result.stdout)


def test_every_item_flag_mapping_repeat_and_strict_export():
    args, result = run()
    assert result['count'] == result['removed'] == len(result['urls']) == 2
    assert result['results'][0] == result['results'][1]
    notes = json.loads(result['results'][0])
    assert notes['corpusSha256'] == args[1] and notes['predictionsSha256'] == args[3]
    assert notes['status'] == exporter.STATUS
    assert [i['itemId'] for i in notes['items']] == [i['id'] for i in args[0]['items']]
    for index, row in enumerate(notes['items']):
        assert [row[flag] for flag in exporter.FLAGS] == [j == index % 3 for j in range(3)]
        assert row['note'] == f'备注 {index} <script> & \n😀'
    html = exporter.export(*args, notes, hashlib.sha256(result['results'][0].encode()).hexdigest()).decode()
    assert '<script>' not in html
    assert '未标记（不表示核实通过）' in html
    assert '请在浏览器下载列表确认文件已保存' in result['status']


@pytest.mark.parametrize('mode', ['url-fail', 'missing'])
def test_fail_closed_before_download(mode):
    _, result = run(mode)
    assert result['count'] == 0 and result['results'] == []
    assert '无法发起下载' in result['status'] and '未确认保存' in result['status']


@pytest.mark.parametrize('field', ['corpusSha256', 'predictionsSha256', 'status'])
def test_download_binding_tamper_rejected_without_output(field, tmp_path):
    args, result = run()
    notes = json.loads(result['results'][0])
    notes[field] = 'approved' if field == 'status' else '0' * 64
    worksheet = tmp_path / 'notes.json'; worksheet.write_text(json.dumps(notes))
    output = tmp_path / 'snapshot.html'
    cmd = [sys.executable, str(ROOT / 'export_review.py'), 'export', '--corpus', str(ROOT / 'jiangxin9-provisional.json'), '--predictions', str(ROOT / 'jiangxin9-real-predictions.json'), '--worksheet', str(worksheet), '--output', str(output)]
    process = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    assert process.returncode == 2 and not output.exists()
    assert json.loads(process.stderr)['errorCode'] == 'RESEARCH_NOTES_EXPORT_REJECTED'


def test_frozen_files_match():
    for line in (REPO / 'logs/semantic-browser-export-impl-hashes-frozen.txt').read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        assert hashlib.sha256((REPO / name).read_bytes()).hexdigest() == digest
