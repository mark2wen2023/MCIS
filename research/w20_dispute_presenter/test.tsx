import assert from 'node:assert/strict';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {AgentOverviewSyntheticReview as View} from '../../web/src/pages/AgentOverviewPage';
const caseId='CASE-2026-DEMO-LILY-MARY',revision='synthetic-review-v1';
const items=[
 {id:'A',seat:'席位甲（合成）',claim:'声称发出了右满舵指令',sourceId:'S-A',start:2,end:2,quote:'我声称当时发出了右满舵指令。'},
 {id:'B',seat:'席位乙（合成）',claim:'声称当时没有发出该指令',sourceId:'S-B',start:2,end:2,quote:'我声称当时没有发出右满舵指令。'}];
const control={caseId,revision,question:'是否发出该指令（合成争议）',items:structuredClone(items),sources:[
 {id:'S-A',caseId,revision,lines:['合成笔记甲',items[0].quote]},
 {id:'S-B',caseId,revision,lines:['合成笔记乙',items[1].quote]}]};
function freeze(x:any){Object.freeze(x);Object.values(x).forEach(v=>{if(v&&typeof v==='object')freeze(v)});return x}freeze(control);
const input={kind:'developer_synthetic_dispute' as const,caseId,revision,question:control.question,items};
let passed=0;function check(name:string,fn:()=>void){fn();passed++;console.log('PASS '+name)}
const render=(i:any=input,c:any=control)=>renderToStaticMarkup(<View input={i} control={c}/>);
check('both opposing rows retain their own quote and source',()=>{const h=render();for(const i of items){const start=h.indexOf('data-item="'+i.id+'"');const row=h.slice(start,h.indexOf('</article>',start));assert(row.includes(i.quote)&&row.includes(i.sourceId));assert(!row.includes(items.find(x=>x.id!==i.id)!.quote))}});
check('unresolved pending and no authority or write controls',()=>{const h=render();assert(h.includes('分歧未解决')&&h.includes('未保存')&&h.includes('语义支持未评定'));assert(!/<(button|input|textarea|select|a|form)\b/.test(h))});
check('no default synthetic rows',()=>assert.equal(renderToStaticMarkup(<View/>),''));
const negatives=[
 ['confirmation flag',(x:any)=>x.confirmed=true],
 ['cross case',(x:any)=>x.caseId='OTHER'],
 ['stale revision',(x:any)=>x.revision='old'],
 ['borrowed quote',(x:any)=>x.items[0].quote=x.items[1].quote],
 ['swapped source',(x:any)=>x.items[0].sourceId='S-B'],
 ['wrong line',(x:any)=>x.items[0].start=1],
 ['missing opposing side',(x:any)=>x.items.pop()],
 ['invented resolution',(x:any)=>x.items[0].claim='已经确定责任'],
 ['changed question',(x:any)=>x.question='changed']];
for(const [name,change] of negatives as any){check(name,()=>{const x=structuredClone(input);change(x);const h=render(x);assert(h.includes('绑定不符'));assert(!h.includes(items[0].quote)&&!h.includes(items[1].quote))})}
check('source text identity mismatch',()=>{const c=structuredClone(control);c.sources[0].lines[1]='different';assert(render(input,c).includes('绑定不符'))});
check('source case mismatch',()=>{const c=structuredClone(control);c.sources[1].caseId='OTHER';assert(render(input,c).includes('绑定不符'))});
check('source revision mismatch',()=>{const c=structuredClone(control);c.sources[1].revision='old';assert(render(input,c).includes('绑定不符'))});
check('no mutation',()=>{const before=JSON.stringify(input);render();assert.equal(JSON.stringify(input),before)});

check('property order is not identity',()=>{const x=structuredClone(input);x.items=x.items.map(i=>Object.fromEntries(Object.entries(i).reverse())) as any;assert(render(x).includes(items[0].quote))});
check('toJSON is rejected without invocation',()=>{const x:any=structuredClone(input);let calls=0;x.items[0].toJSON=()=>{calls++;return items[0]};assert(render(x).includes('绑定不符'));assert.equal(calls,0)});
check('accessor is rejected without invocation',()=>{const x:any=structuredClone(input);let calls=0;Object.defineProperty(x.items[0],'quote',{enumerable:true,get(){calls++;return items[0].quote}});assert(render(x).includes('绑定不符'));assert.equal(calls,0)});
for(const key of ['id','seat','sourceId'])check('exact '+key,()=>{const x:any=structuredClone(input);x.items[0][key]='unknown';assert(render(x).includes('绑定不符'))});
check('array-like items rejected',()=>{const x:any=structuredClone(input);x.items={0:x.items[0],1:x.items[1],length:2};assert(render(x).includes('绑定不符'))});
check('sparse items rejected',()=>{const x:any=structuredClone(input);delete x.items[0];assert(render(x).includes('绑定不符'))});
check('source lines must be array',()=>{const c:any=structuredClone(control);c.sources[0].lines='wrong';assert(render(input,c).includes('绑定不符'))});
check('non-string source line rejected',()=>{const c:any=structuredClone(control);c.sources[0].lines[0]=42;assert(render(input,c).includes('绑定不符'))});
check('duplicate control seat rejected',()=>{const c:any=structuredClone(control);c.items[1].seat=c.items[0].seat;assert(render(input,c).includes('绑定不符'))});

console.log('TOTAL '+passed);
