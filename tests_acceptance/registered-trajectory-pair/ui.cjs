// Production adapter + shared HTML shell. Handwritten DOM, NOT a browser.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(process.argv[2],'utf8'), fixtures=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
assert(!html.includes('SYN-XREPO-001'));assert(!html.includes('SYN-DEVICE'));assert(!html.includes('data.frames'));
const js=html.match(/<script>([\s\S]*?)<\/script>/)[1];
class E{constructor(){this.children=[];this.attrs={};this.textContent='';this.value='';this.disabled=false;this.open=false;this.onclick=null;this.classList={toggle:(k,v)=>this.attrs[k]=v};}appendChild(e){this.children.push(e);return e;}replaceChildren(){this.children=[];}setAttribute(k,v){this.attrs[k]=String(v);}getAttribute(k){return this.attrs[k]??null;}}
const nodes=Object.fromEntries([...html.matchAll(/id="([^"]+)"/g)].map(m=>[m[1],new E()]));
const forbidden=()=>{throw Error('Unexpected network/storage/URL action');};
const ctx={document:{getElementById:id=>{assert(nodes[id],id);return nodes[id];},createElement:()=>new E(),createElementNS:()=>new E()},fetch:forbidden,XMLHttpRequest:forbidden};
for(const key of ['location','localStorage','sessionStorage'])Object.defineProperty(ctx,key,{get:forbidden});
vm.runInNewContext(js,ctx);
const api=ctx.MCISRegisteredWorkbench,copy=o=>JSON.parse(JSON.stringify(o)),times=fixtures.map(x=>x.alignedUtc).sort();
const config={caseId:fixtures[0].caseId,pins:fixtures[0].vessels.map(v=>v.original),times};
const model=t=>copy(fixtures.find(f=>f.alignedUtc===t));
const markers=()=>nodes.map.children.filter(n=>n.attrs['data-current']);
const blank=()=>{assert.equal(markers().length,0);assert.equal(nodes.pointer.textContent,'—');assert.equal(nodes.ref.textContent,'—');assert.equal(nodes['point-options'].children.length,0);};
const t20=times[0],t80=times[1],t100=times[2],t124=times[3];
(async()=>{
 blank();assert(nodes['registered-load'].disabled);let calls=[];
 api.attach(async q=>{calls.push(q);return model(q.alignedUtc);});api.selectCase(config);assert.equal(calls.length,0);blank();
 nodes.next.onclick();nodes.prev.onclick();assert.equal(calls.length,0);
 for(let i=0;i<20;i++){nodes.time.value=i%2?t20:t80;nodes.time.oninput();nodes.time.onchange();}
 assert.equal(calls.length,0);assert.equal(markers().length,0);assert(nodes.timeline.children.some(n=>n.attrs['data-preview']==='unqueried'));
 nodes.time.value=t20;nodes.time.onchange();await nodes['registered-load'].onclick();assert.equal(markers().length,2);assert.equal(calls.length,1);
 nodes['point-options'].children[1].onclick();assert.match(nodes.quality.textContent,/已存插值/);assert.equal(nodes.correction.textContent,'12 s');assert.equal(nodes['source-time'].textContent,'2026-02-01T12:00:08.000Z');assert.match(nodes.ref.textContent,/仅展示服务提供的 JSON 路径/);assert(!nodes.ref.textContent.includes(config.pins[1].sourceSha256));assert.equal(nodes.pointer.textContent,'/points/2');assert(nodes['raw-open'].disabled);
 const oldClick=nodes['point-options'].children[1].onclick;
 await api.load(t80);assert.equal(markers().length,1);assert.match(nodes['state-note'].textContent,/声明缺轨/);assert.equal(nodes.pointer.textContent,'—');oldClick();assert.equal(nodes.pointer.textContent,'—');
 nodes['point-options'].children[0].onclick();assert.equal(nodes.pointer.textContent,'/sampling/missingIntervals/0');
 await api.load(t124);assert.equal(markers().length,0);assert.match(nodes['state-note'].textContent,/无精确行/);assert(nodes['source-b'].disabled);
 await api.load(t100);nodes['source-a'].onclick();assert.match(nodes.warning.textContent,/艏向未知/);
 assert(nodes['device-known'].disabled&&nodes['device-unknown'].disabled);assert.equal(nodes['device-known'].onclick,null);
 // Same-case out-of-order completion, including old failure after new success.
 let pending=[];api.attach(q=>new Promise((resolve,reject)=>pending.push({q,resolve,reject})));api.selectCase(config);
 const a=api.load(t20);await api.load(t20);assert.equal(pending.length,1);assert(nodes['registered-load'].disabled);blank();assert.match(nodes['state-note'].textContent,/正在查询/);const b=api.load(t80);pending[1].resolve(model(t80));await b;assert.equal(markers().length,1);pending[0].resolve(model(t20));await a;assert.equal(markers().length,1);
 const c=api.load(t20),d=api.load(t100);pending[3].resolve(model(t100));await d;pending[2].reject({code:'ACCESS_DENIED'});await c;assert.equal(markers().length,2);assert.match(nodes.clock.textContent,/12:01:40/);
 // A->B switch must synchronously erase A, even while B has no accepted data.
 const late=api.load(t20);const other=copy(config);other.caseId='SYN-OTHER';other.pins.forEach(p=>p.caseId=other.caseId);api.selectCase(other);blank();assert.equal(nodes['registered-case'].textContent,'SYN-OTHER');pending[4].resolve(model(t20));await late;blank();
 const wrong=api.load(t80);pending[5].resolve(model(t80));await wrong;blank();assert.match(nodes['state-note'].textContent,/首次载入未通过/);
 api.selectCase(config);const ready=api.load(t20);pending[6].resolve(model(t20));await ready;
 const denied=api.load(t80);blank();pending[7].reject({code:'ACCESS_DENIED',message:'DO NOT DISPLAY PRIVATE TEXT'});await denied;blank();assert.match(nodes['state-note'].textContent,/此前显示已清除/);assert(!nodes['state-note'].textContent.includes('PRIVATE'));
 const stale=api.load(t20);api.invalidate();pending[8].resolve(model(t20));await stale;blank();assert(nodes['registered-load'].disabled);
 // Rejected first load cannot install coordinates, pin mismatches or extra prose.
 for(const mutate of [r=>r.vessels[0].original.sourceSha256='f'.repeat(64),r=>r.vessels[0].rawRecord={secret:'hidden'},r=>r.vessels[0].time.correctionSeconds=99]){
  api.attach(async()=>{const r=model(t20);mutate(r);return r;});api.selectCase(config);await api.load(t20);blank();assert.match(nodes['state-note'].textContent,/首次载入未通过/);
 }
 api.attach(async()=>{const r=model(t20);r.vessels[0].position.kind='manual_assumption';r.vessels[0].vesselId='合成船甲';return r;});api.selectCase(config);await api.load(t20);nodes['source-a'].onclick();assert.match(nodes.quality.textContent,/人工假设/);
 api.attach(async q=>model(q.alignedUtc));api.selectCase(config);await api.load(t20);api.selectCase({...config,caseId:''});blank();assert.equal(nodes['registered-case'].textContent,'未选案件');assert(nodes['registered-load'].disabled);
 api.selectCase(config);await api.load(t20);assert.throws(()=>api.attach(null));blank();assert(nodes['registered-load'].disabled);
 console.log('PASS registered controller: real query model rendering/pins, gaps/HDG, explicit-only requests, clear-on-load, stale detail and ordered completion, switch/denial/invalidation, malformed model; synthetic DOM, no browser');
})().catch(e=>{console.error(e);process.exitCode=1;});
