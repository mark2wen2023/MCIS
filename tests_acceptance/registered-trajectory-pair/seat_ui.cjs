// Existing workbench script + actual host handoff. Fake DOM/transport, never HTTP.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(process.argv[2],'utf8'),record=JSON.parse(fs.readFileSync(0,'utf8'));
assert(html.includes('<dt>原件记载 UTC</dt>'));assert(html.includes('<dt>展示对齐 UTC</dt>'));
assert.equal(record.scope,'synthetic-test-host-only');assert.equal(record.frames.length,2);
class E{constructor(){this.children=[];this.attrs={};this.textContent='';this.value='';this.disabled=false;this.open=false;this.onclick=null;this.classList={toggle:(k,v)=>this.attrs[k]=v};}appendChild(e){this.children.push(e);return e;}replaceChildren(){this.children=[];}setAttribute(k,v){this.attrs[k]=String(v);}getAttribute(k){return this.attrs[k]??null;}}
const nodes=Object.fromEntries([...html.matchAll(/id="([^"]+)"/g)].map(m=>[m[1],new E()]));
const forbidden=()=>{throw Error('No network/storage/navigation in this check');};
const ctx={document:{getElementById:id=>{assert(nodes[id],id);return nodes[id];},createElement:()=>new E(),createElementNS:()=>new E()},fetch:forbidden,XMLHttpRequest:forbidden};
for(const k of ['location','localStorage','sessionStorage'])Object.defineProperty(ctx,k,{get:forbidden});
vm.runInNewContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],ctx);
const api=ctx.MCISRegisteredWorkbench,copy=o=>JSON.parse(JSON.stringify(o));
const config={caseId:record.caseId,pins:record.frames[0].vessels.map(v=>v.original),times:record.frames.map(f=>f.alignedUtc)};
const [t100,t124]=config.times, frame=t=>copy(record.frames.find(f=>f.alignedUtc===t));
const markers=()=>nodes.map.children.filter(n=>n.attrs['data-current']);
const blank=()=>{assert.equal(markers().length,0);for(const id of ['pointer','ref','source-time','correction'])assert.equal(nodes[id].textContent,'—');};
(async()=>{
 let calls=0;api.attach(async q=>{calls++;return frame(q.alignedUtc);});api.selectCase(config);blank();assert.equal(calls,0);
 for(let i=0;i<10;i++){nodes.time.value=i%2?t100:t124;nodes.time.oninput();}
 blank();assert.equal(calls,0);nodes.time.value=t100;nodes.time.onchange();await nodes['registered-load'].onclick();assert.equal(calls,1);assert.equal(markers().length,2);
 nodes['source-b'].onclick();assert.equal(nodes.pointer.textContent,'/points/12');assert.equal(nodes.correction.textContent,'12 s');assert.equal(nodes['source-time'].textContent,'2026-02-01T12:01:28.000Z');
 assert.match(nodes.basis.textContent,/来源声明.*待人工复核/);assert.match(nodes.basis.textContent,/校时依据未交付、人审未签/);assert.match(nodes.basis.textContent,/事件先后或同时仍未确定/);assert.equal(nodes['aligned-time'].textContent,t100);
 for(const pin of config.pins)for(const value of [pin.evidenceId,pin.requestDigest,pin.sourceSha256])for(const n of Object.values(nodes))assert(!n.textContent.includes(value));
 nodes['source-a'].onclick();assert.equal(nodes.pointer.textContent,'/points/7');assert.match(nodes.quality.textContent,/契约记录点.*未认证/);assert.match(nodes.warning.textContent,/艏向未知/);const oldDetail=nodes['source-a'].onclick;
 nodes.time.value=t124;nodes.time.oninput();blank();oldDetail();blank();assert.equal(calls,1);
 await nodes['registered-load'].onclick();assert.equal(calls,2);assert.equal(markers().length,0);assert.match(nodes['state-note'].textContent,/声明缺轨.*无精确行/);
 assert(nodes['source-b'].disabled);assert.equal(nodes.pointer.textContent,'—');nodes['source-a'].onclick();assert.equal(nodes.pointer.textContent,'/sampling/missingIntervals/1');assert.match(nodes.quality.textContent,/声明缺轨/);assert.match(nodes.basis.textContent,/不是位置观测/);
 assert.equal(nodes['source-time'].textContent,'—');assert.equal(nodes.correction.textContent,'—');assert(nodes['raw-open'].disabled);
 // Controlled same-case slow transport; late completion must not revive old point/details.
 let pending=[];api.attach(q=>new Promise(resolve=>pending.push({q,resolve})));api.selectCase(config);
 const early=api.load(t100);blank();const later=api.load(t124);blank();pending[1].resolve(frame(t124));await later;pending[0].resolve(frame(t100));await early;
 assert.equal(markers().length,0);assert.equal(nodes.pointer.textContent,'—');assert.match(nodes['state-note'].textContent,/无精确行/);
 const late=api.load(t100);api.invalidate();blank();pending[2].resolve(frame(t100));await late;blank();assert(nodes['registered-load'].disabled);
 console.log('PASS actual handoff -> existing sidebar: T100 pins/clock pending; T124.250 gap/no point; stage zero calls; explicit one call; stale details/late results cleared. Synthetic DOM/transport only.');
})().catch(e=>{console.error(e);process.exitCode=1;});
