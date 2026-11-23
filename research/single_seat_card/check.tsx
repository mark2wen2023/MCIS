import React from 'react'
import {renderToStaticMarkup} from 'react-dom/server'
import assert from 'node:assert/strict'
import fixed from '../single_seat_preview/result.json'
import {SingleSeatCard} from './Card'
const render=(value:unknown)=>renderToStaticMarkup(<SingleSeatCard preview={value}/>);
const html=render(fixed.preview);
for(const text of ['待人工审核','未确认','未保存','已声明轨迹缺口','该时刻无精确观测','证据不足','不可点击','/sampling/missingIntervals/1','无精确观测引用'])assert.ok(html.includes(text),text);
assert.ok(!/<(a|button|form|input)\b/.test(html));
assert.ok(!/href=|requestDigest|sourceSha256|onClick/.test(html));
assert.equal(render(structuredClone(fixed.preview)),html);
const cases: Array<[string,(p:any)=>unknown]> = [
 ['wrong case',p=>{p.caseId='OTHER';return p}],['wrong time',p=>{p.alignedUtc='2026-02-01T12:01:40.000Z';return p}],
 ['confirmed',p=>{p.humanAction.confirmed=true;return p}],['saved',p=>{p.humanAction.saved=true;return p}],
 ['wrong status',p=>{p.humanAction.status='confirmed';return p}],['conflicted',p=>{p.rows[0].sufficiency='conflicted';return p}],
 ['borrowed B reference',p=>{p.rows[1].reference=p.rows[0].reference;return p}],['missing A reference',p=>{p.rows[0].reference=null;return p}],
 ['extra private data',p=>{p.secret='PRIVATE CONTROL';return p}],['html changed',p=>{p.rows[0].statement='<script>BAD CONTROL</script>';return p}],
 ['unsupported type',p=>{p.type='AgentDraft';return p}],['malformed',()=>null]
];
for(const [name,change] of cases){const result=render(change(structuredClone(fixed.preview)));assert.ok(result.includes('单席意见不可展示'),name);assert.ok(!result.includes('SYN-E-A')&&!result.includes('PRIVATE CONTROL')&&!result.includes('BAD CONTROL'),name)}
assert.equal(render(fixed.preview),html,'rejected input does not retain or contaminate state');
console.log(JSON.stringify({mode:'React SSR only; no browser',positiveChecks:'Chinese labels, A/B distinction, noninteractive references, stable render',rejectionCases:cases.length,passed:true,sourcePreviewSha256:'ab3543be14e7e2271790a1a0cb03d61a3a779adb0f3682ef56f32050317f3dc9'}));
console.log(html);
