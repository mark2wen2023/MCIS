"""Independent restore acceptance against generated scripts; no browser claim."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
import export_review as exporter
import render_restore_review as renderer

HARNESS = r'''
const vm=require('node:vm'), assert=require('node:assert/strict');
const input=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
const template=JSON.parse(input.html.match(/<script id="worksheet-template" type="application\/json">(.*?)<\/script>/s)[1]);
const listeners={}, nodes={}, downloads=[], timers=[];
for(const id of ['import-file','apply-import','cancel-import','clear-notes','confirm-clear','import-status','download-notes','download-status']) nodes[id]={addEventListener(e,f){this[e]=f}};
const fields=template.items.map((_,i)=>{const boxes=[false,true,false].map(checked=>({checked})),area={value:`existing ${i}`,focus(){}};return{boxes,area,querySelectorAll:()=>boxes,querySelector:()=>area}});
const doc={getElementById:id=>id==='worksheet-template'?{textContent:JSON.stringify(template)}:nodes[id],querySelectorAll:()=>fields,
addEventListener(e,f){(listeners[e]??=[]).push(f)},dispatchEvent(e){for(const f of listeners[e.type]||[])f({target:this})},
body:{appendChild(){}},createElement:()=>({click(){},remove(){}})};
const context={document:doc,Event,TextDecoder,Blob,URL:{createObjectURL:b=>{downloads.push(b);return'blob:test'},revokeObjectURL(){}},setTimeout:f=>timers.push(f)};
for(const match of input.html.matchAll(/<script>(.*?)<\/script>/sg))vm.runInNewContext(match[1],context);
const picker=nodes['import-file'], apply=nodes['apply-import'];
const state=()=>JSON.stringify(fields.map(f=>[f.area.value,...f.boxes.map(b=>b.checked)]));
const original=state();
const valid=structuredClone(template);valid.items.forEach((row,i)=>{row.note=`restored ${i} <script> & 😀\n`;row.sourceAssociationNeedsCheck=true});
async function select(raw){const bytes=Buffer.isBuffer(raw)?raw:Buffer.from(raw);picker.files=[{size:bytes.length,arrayBuffer:async()=>bytes}];await picker.change()}
function deferred(){let resolve;picker.files=[{size:4,arrayBuffer:()=>new Promise(r=>resolve=r)}];const finished=picker.change();return{finish:async raw=>{resolve(Buffer.from(raw));await finished}}}
(async()=>{
 if(input.mode==='invalid'){
  await select(Buffer.from(input.payload,'base64'));assert.equal(apply.disabled,true);apply.click();assert.equal(state(),original);assert.match(nodes['import-status'].textContent,/拒绝/);
 }else if(input.mode==='race'){
  const a=deferred();await select(JSON.stringify(valid));await a.finish('bad JSON');assert.equal(apply.disabled,false);apply.click();assert.equal(fields[0].area.value,valid.items[0].note);
  const b=deferred();fields[0].area.value='newer edit';doc.dispatchEvent(new Event('input'));await b.finish(JSON.stringify(valid));apply.click();assert.equal(fields[0].area.value,'newer edit');
  const c=deferred();nodes['clear-notes'].click();await c.finish(JSON.stringify(valid));assert.equal(nodes['confirm-clear'].hidden,false);assert.equal(apply.disabled,true);nodes['cancel-import'].click();nodes['confirm-clear'].click();assert.equal(fields[0].area.value,'newer edit');
 }else if(input.mode==='controls'){
  await select(JSON.stringify(valid));fields.at(-1).querySelector=()=>null;apply.click();assert.equal(state(),original);assert.match(nodes['import-status'].textContent,/未应用/);
  nodes['clear-notes'].click();nodes['confirm-clear'].click();assert.equal(state(),original);assert.match(nodes['import-status'].textContent,/未清空/);
 }else if(input.mode==='clear'){
  nodes['clear-notes'].click();doc.dispatchEvent(new Event('input'));nodes['confirm-clear'].click();assert.equal(state(),original);
  nodes['clear-notes'].click();nodes['confirm-clear'].click();assert.ok(fields.every(f=>f.area.value===''&&f.boxes.every(b=>!b.checked)));
  nodes['download-notes'].click();assert.deepEqual(JSON.parse(await downloads.at(-1).text()),template);
 }else{
  valid.items.reverse();await select(JSON.stringify(valid));assert.equal(state(),original);apply.click();const first=state();
  await select(JSON.stringify(valid));apply.click();assert.equal(state(),first);
  nodes['download-notes'].click();const result=JSON.parse(await downloads.at(-1).text());
  assert.deepEqual(result.items.map(x=>x.itemId),template.items.map(x=>x.itemId));assert.deepEqual([...result.items].reverse(),valid.items);
  assert.match(nodes['download-status'].textContent,/请在浏览器下载列表确认/);console.log(JSON.stringify(result));return;
 }
 console.log('{}');
})().catch(e=>{console.error(e);process.exitCode=1});
'''


def inputs():
    corpus, cs = exporter.load(ROOT / 'jiangxin9-provisional.json')
    predictions, ps = exporter.load(ROOT / 'jiangxin9-real-predictions.json')
    return corpus, cs, predictions, ps


def execute(mode, payload=b''):
    args = inputs()
    data = {'html': renderer.render_restore(*args).decode(), 'mode': mode, 'payload': base64.b64encode(payload).decode()}
    result = subprocess.run(['node', '-e', HARNESS], input=json.dumps(data), capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    return args, json.loads(result.stdout)


def bad_payloads():
    base = exporter.template(*inputs())
    raw = json.dumps(base)
    yield b'\xef\xbb\xbf' + raw.encode()
    yield b'\xff'
    yield (raw + '{}').encode()
    yield raw.replace('"schemaVersion": 1', '"schemaVersion": 1e0').encode()
    yield raw.replace('"schemaVersion": 1', '"schemaVersion": 1,"schemaVersion":1').encode()
    yield raw.replace('"note": ""', '"note":"","n\\u006fte":""', 1).encode()
    yield ('[' * 18 + '0' + ']' * 18).encode()
    for key, value in [('corpusSha256', '0' * 64), ('predictionsSha256', '0' * 64), ('status', 'approved'), ('__proto__', {'polluted': True})]:
        changed = json.loads(raw); changed[key] = value
        yield json.dumps(changed).encode()
    for key, value in [('note', '\ud800'), ('note', '😀' * 4001), ('sourceAssociationNeedsCheck', 1), ('itemId', '__proto__')]:
        changed = json.loads(raw); changed['items'][-1][key] = value
        yield json.dumps(changed).encode()
    changed = json.loads(raw); changed['items'][-1] = changed['items'][0]
    yield json.dumps(changed).encode()
    changed = json.loads(raw); changed['items'].pop()
    yield json.dumps(changed).encode()
    changed = json.loads(raw); changed['items'][0].update(note='\u0085\u001c', otherNeedsCheck=True)
    yield json.dumps(changed).encode()


@pytest.mark.parametrize('payload', list(bad_payloads()), ids=lambda x: hashlib.sha256(x).hexdigest()[:10])
def test_invalid_import_never_changes_existing_edits(payload):
    execute('invalid', payload)


def test_late_read_does_not_override_new_selection_edit_or_clear():
    execute('race')


def test_missing_last_control_prevents_all_writes_and_clear():
    execute('controls')


def test_clear_requires_current_confirmation_and_exports_empty_unverified():
    execute('clear')


def test_reordered_repeat_import_then_export_passes_strict_cli_format():
    args, worksheet = execute('roundtrip')
    exporter.validate_worksheet(worksheet, exporter.template(*args))
    digest = hashlib.sha256(json.dumps(worksheet).encode()).hexdigest()
    html = exporter.export(*args, worksheet, digest).decode()
    assert '<script>' not in html and '&lt;script&gt;' in html
    assert args[1] in html and args[3] in html and '未认证' in html


def test_restore_freeze_unchanged():
    for line in (ROOT / 'browser-restore-hashes-frozen.txt').read_text().splitlines():
        digest, filename = line.split(maxsplit=1)
        assert hashlib.sha256((ROOT.parents[1] / filename).read_bytes()).hexdigest() == digest
