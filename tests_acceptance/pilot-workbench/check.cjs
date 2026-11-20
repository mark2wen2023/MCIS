// Production inline script, hand-written DOM and memory promises. No network.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname,'../../service/mcis_service/local_review_pilot/workbench.html'),'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
assert.equal(scripts.length,1);
assert(!/\bsrc=|<iframe|<form|localStorage|X-MCIS|Authorization|DEMO_CASE_ID/.test(html));
class Element {
 constructor() { this.children=[]; this.textContent=''; this.attrs={}; this.disabled=false; }
 replaceChildren(...nodes) { this.children=nodes; }
 appendChild(node) { this.children.push(node); }
 setAttribute(k,v) { this.attrs[k]=v; }
 removeAttribute(k) { delete this.attrs[k]; }
}
function setup(images=false) {
 const nodes = Object.fromEntries([...html.matchAll(/id="([^"]+)"/g)].map(m=>[m[1],new Element()]));
 const requests=[], events={};
 const document={hidden:false,getElementById:id=>{assert(nodes[id],id);return nodes[id];},createElement:tag=>{assert(['button','a'].includes(tag));return new Element();},addEventListener:(n,f)=>events[n]=f};
 const window={addEventListener:(n,f)=>events[n]=f};
 function fetch(url,options) {
  assert(/^\/api\/v1\/(pilot\/cases|cases\/SYN-[\w.-]+)$/.test(url));
  assert.deepEqual(JSON.parse(JSON.stringify(options)),{method:'GET',credentials:'same-origin',cache:'no-store',redirect:'error',headers:{Accept:'application/json'}});
  let resolve,reject; const promise=new Promise((a,b)=>{resolve=a;reject=b;});
  requests.push({url,resolve:(body,status=200)=>resolve({ok:status===200,status,json:async()=>body}),reject}); return promise;
 }
 vm.runInNewContext(images?scripts[0][1].replace('const imagePageAvailable=false;','const imagePageAvailable=true;'):scripts[0][1],{document,window,fetch,console});
 return {nodes,requests,events,document};
}
const A={caseId:'SYN-A',title:'合成 A'},B={caseId:'SYN-B',title:'合成 B'};
const flush=async()=>{for(let i=0;i<8;i++)await Promise.resolve();};
async function loaded(s,list=[A,B]) { const p=s.nodes.refresh.onclick();s.requests.at(-1).resolve(list);await p; }
async function test(name,f){await f();console.log('PASS '+name);}
(async()=>{
 await test('initial no request; explicit discovery and detail; no role or writes',async()=>{
  const s=setup();assert.equal(s.requests.length,0);await loaded(s);
  assert.equal(s.requests.length,1);assert.equal(s.nodes.cases.children.length,2);
  const p=s.nodes.cases.children[0].onclick();assert.match(s.nodes.context.textContent,/SYN-A/);assert.equal(s.nodes['case-title'].textContent,'');
  s.requests[1].resolve(A);await p;assert.equal(s.nodes['case-title'].textContent,A.title);assert.equal(s.nodes.stage.attrs['aria-current'],'step');
  assert.match(s.nodes['detail-status'].textContent,/不能视为零条或已完成/);assert.equal(s.requests.length,2);
 });
 await test('A late success or failure cannot overwrite B',async()=>{
  for(const fail of [false,true]){const s=setup();await loaded(s);
   const a=s.nodes.cases.children[0].onclick(), b=s.nodes.cases.children[1].onclick();
   s.requests[2].resolve(B);await b;
   if(fail)s.requests[1].reject(new Error('synthetic'));else s.requests[1].resolve(A);
   await a;assert.equal(s.nodes['case-title'].textContent,B.title);assert.equal(s.nodes.context.textContent,'当前案号：SYN-B');
  }
 });
 await test('loaded A cleared immediately for B pending and failure',async()=>{
  const s=setup();await loaded(s);let p=s.nodes.cases.children[0].onclick();s.requests[1].resolve(A);await p;
  p=s.nodes.cases.children[1].onclick();assert.equal(s.nodes['case-title'].textContent,'');assert(!s.nodes.stage.attrs['aria-current']);
  s.requests[2].reject(new Error('offline'));await p;assert.match(s.nodes['detail-status'].textContent,/未能确认/);assert.equal(s.nodes['case-title'].textContent,'');
 });
 await test('identity mismatch is not accepted; no fallback request',async()=>{
  const s=setup();await loaded(s);const p=s.nodes.cases.children[1].onclick();s.requests[1].resolve(A);await p;
  assert.equal(s.nodes['case-title'].textContent,'');assert.match(s.nodes['detail-status'].textContent,/响应不符/);assert.equal(s.requests.length,2);
 });
 await test('empty, malformed, duplicate and failed lists distinguished',async()=>{
  for(const list of [[],[A,A],[{caseId:'',title:'bad'}],[{caseId:'SYN-A',title:123}],{}]){
   const s=setup();await loaded(s,list);assert.equal(s.nodes.cases.children.length,0);
   assert.match(s.nodes['list-status'].textContent,Array.isArray(list)&&list.length===0?/没有可读取/:/失败或格式无效/);
  }
  const s=setup();const p=s.nodes.refresh.onclick();s.requests[0].reject(new Error('offline'));await p;
  assert.match(s.nodes['list-status'].textContent,/读取失败/);assert.equal(s.nodes.refresh.disabled,false);
 });
 await test('session failure clears case/list and old buttons cannot read',async()=>{
  for(const status of [401,403]){const s=setup();await loaded(s);const old=s.nodes.cases.children[0];
   const p=old.onclick();s.requests[1].resolve({},status);await p;
   assert.equal(s.nodes.cases.children.length,0);assert.equal(s.nodes.context.textContent,'未选择案件');assert.match(s.nodes['list-status'].textContent,/会话或案件授权/);
   await old.onclick();assert.equal(s.requests.length,2);
  }
 });
 await test('refresh invalidates detail and overlapping discovery responses',async()=>{
  const s=setup();await loaded(s);const a=s.nodes.cases.children[0].onclick();const first=s.nodes.refresh.onclick(),second=s.nodes.refresh.onclick();
  s.requests[3].resolve([B]);await second;s.requests[2].resolve([A]);await first;s.requests[1].resolve(A);await a;
  assert.equal(s.nodes.cases.children.length,1);assert.match(s.nodes.cases.children[0].textContent,/SYN-B/);assert.equal(s.nodes['case-title'].textContent,'');
 });
 await test('hidden/pagehide invalidate pending and erase cached context',async()=>{
  for(const kind of ['pagehide','visibilitychange']){const s=setup();await loaded(s);const p=s.nodes.cases.children[0].onclick();
   s.document.hidden=true;s.events[kind]();s.requests[1].resolve(A);await p;await flush();
   assert.equal(s.nodes.cases.children.length,0);assert.equal(s.nodes['case-title'].textContent,'');assert.equal(s.nodes.context.textContent,'未选择案件');
  }
 });
 await test('titles rendered as text; seven stages are not completion; no fake media links',async()=>{
  const s=setup();await loaded(s,[{caseId:'SYN-A',title:'<img src=x>'}]);assert.match(s.nodes.cases.children[0].textContent,/<img src=x>/);
  assert(html.includes('完成状态未评估'));assert(html.includes('图音接入范围'));
  assert.deepEqual([...html.matchAll(/href="([^"]+)"/g)].map(m=>m[1]),['#case-picker']);
 });
 await test('image capability: confirmed case only, clear before switch and ignore late response',async()=>{
  const s=setup(true);assert.equal(s.nodes['image-entry'].children.length,0);await loaded(s);
  let p=s.nodes.cases.children[0].onclick();s.requests[1].resolve(A);await p;assert.equal(s.nodes['image-entry'].children[0].href,'/pilot/image-review?case=SYN-A');
  p=s.nodes.cases.children[1].onclick();assert.equal(s.nodes['image-entry'].children.length,0);s.requests[2].reject(new Error('fail'));await p;assert.equal(s.nodes['image-entry'].children.length,0);
  const old=s.nodes.cases.children[0].onclick(),fresh=s.nodes.cases.children[1].onclick();s.requests[4].resolve(B);await fresh;s.requests[3].resolve(A);await old;assert.equal(s.nodes['image-entry'].children[0].href,'/pilot/image-review?case=SYN-B');
  const off=setup();await loaded(off);const d=off.nodes.cases.children[0].onclick();off.requests[1].resolve(A);await d;assert.equal(off.nodes['image-entry'].children.length,0);
 });
 console.log('COMPLETE 10 groups; synthetic DOM/Promise only');
})().catch(error=>{console.error(error);process.exitCode=1;});
