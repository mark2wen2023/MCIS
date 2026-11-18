// Actual inline render callback, synthetic DOM only. No requests/media/Python.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync('service/mcis_service/audio_review/review.html','utf8');
const script=html.split('<script>')[1].split('</script>')[0];
function setup(){
 let fetches=0;class Element{constructor(){this.children=[];this.events={};this.value='';this.textContent=''}addEventListener(n,f){(this.events[n]??=[]).push(f)}fire(n){for(const f of this.events[n]||[])f()}pause(){}load(){}removeAttribute(){}replaceChildren(){this.children=[]}append(...v){this.children.push(...v)}setAttribute(){}}
 const elements={},ctx=vm.createContext({document:{getElementById:id=>elements[id]??(elements[id]=new Element()),createElement:()=>new Element()},window:{addEventListener(){}},URL:{revokeObjectURL(){}},fetch(){fetches++;throw Error('fetch forbidden')}});
 vm.runInContext(script,ctx);
 return {elements,fetches:()=>fetches,render(run,source){ctx.fixture={caseId:'SYNTHETIC',runId:run,revision:0,humanRevisions:[],initial:{audio:{},machineDraft:{source,transcript:{segments:[],unlocatedSegments:[]}}}};vm.runInContext("state=fixture;context=fixture.caseId;el('case').value=context;el('run').value=state.runId;render()",ctx);return elements['record-source'].textContent}};
}
const source=(id,hash)=>({caseId:'SYNTHETIC',evidenceId:id,registeredSha256:hash.repeat(64),currentSha256:hash.repeat(64)});
test('two accepted runs display their own declarations without retaining the previous source',()=>{
 const s=setup();assert.match(s.render('AR-A',source('EV-001','a')),/EV-001/);
 const second=s.render('AR-B',source('EV-002','b'));assert.match(second,/运行：AR-B/);assert.match(second,/EV-002/);assert.ok(second.includes('b'.repeat(64)));assert.ok(!second.includes('EV-001')&&!second.includes('a'.repeat(64)));assert.equal(s.fetches(),0);
});
test('missing and malformed source fields stay explicitly unknown',()=>{
 const s=setup();for(const value of [undefined,null,{},[],{caseId:42,evidenceId:null,registeredSha256:'short',currentSha256:12}]){s.render('AR-old',source('EV-old','a'));const output=s.render('AR-missing',value);assert.equal((output.match(/未知（缺失或格式异常）/g)||[]).length,4);assert.ok(!output.includes('EV-old'));}assert.equal(s.fetches(),0);
});
test('literal declarations are text, digests remain distinct, and disclosure claims no matching or verification',()=>{
 const s=setup(),v=source('<b>synthetic</b>','a');v.currentSha256='b'.repeat(64);const output=s.render('AR-C',v);assert.ok(output.includes('<b>synthetic</b>'));assert.equal(s.elements['record-source'].children.length,0);assert.ok(output.includes('登记 SHA-256：'+'a'.repeat(64)));assert.ok(output.includes('当时当前 SHA-256：'+'b'.repeat(64)));assert.ok(html.includes('本展示未自动核验原件或当前登记版本，也未与笔录匹配'));assert.equal(s.fetches(),0);
});
test('editing case or run clears the displayed declaration until another record is accepted',()=>{
 for(const id of ['case','run']){const s=setup();s.render('AR-A',source('EV-001','a'));s.elements[id].value='OTHER';s.elements[id].fire('input');assert.equal(s.elements['record-source'].textContent,'');assert.equal(s.fetches(),0);}
});
