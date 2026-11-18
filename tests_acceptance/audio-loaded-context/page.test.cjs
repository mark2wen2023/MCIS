// No network: replace only json() with controlled memory promises; fetch must never run.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync('service/mcis_service/audio_review/review.html','utf8').split('<script>')[1].split('</script>')[0];
const record=id=>({caseId:'SYNTHETIC',runId:id,revision:0,humanRevisions:[],initial:{audio:{},machineDraft:{source:{caseId:'SYNTHETIC',evidenceId:'EV-'+id,registeredSha256:'a'.repeat(64),currentSha256:'b'.repeat(64)},transcript:{segments:[{id:'s1',text:'text '+id,startMs:null,endMs:null}],unlocatedSegments:[]}}}});
function setup(){
 let fetches=0;const requests=[];
 class Element{constructor(){this.children=[];this.events={};this.value='';this.textContent=''}addEventListener(n,f){(this.events[n]??=[]).push(f)}fire(n){this['on'+n]?.();for(const f of this.events[n]||[])f()}pause(){}load(){}removeAttribute(){}setAttribute(){}append(...v){this.children.push(...v)}replaceChildren(){this.children=[]}}
 const elements={},ctx=vm.createContext({document:{getElementById:id=>elements[id]??(elements[id]=new Element()),createElement:()=>new Element()},window:{addEventListener(){}},URL:{revokeObjectURL(){}},confirm:()=>true,fetch(){fetches++;throw Error('fetch forbidden')},memoryRequest:path=>new Promise((resolve,reject)=>requests.push({path,resolve,reject})),fixture:record('AR-A')});
 vm.runInContext(script,ctx);vm.runInContext("json=memoryRequest;state=fixture;context=fixture.caseId;el('case').value=context;el('run').value=state.runId;render();taskResult={caseId:context,taskId:'task',status:'succeeded',runId:'AR-B'};el('task-id').value='task'",ctx);
 const input=elements.segments.children[0].children[1];input.value='unsaved A';input.fire('input');
 return {elements,ctx,requests,fetches:()=>fetches,read:s=>vm.runInContext(s,ctx)};
}
function oldContent(s,target){
 const e=s.elements;assert.match(e.metadata.textContent,/EV-AR-A/);assert.match(e['loaded-context']?.textContent??'',/已载入.*AR-A/);assert.ok(e['loaded-context'].textContent.includes(target));assert.match(e['loaded-context'].textContent,/未载入/);
 assert.match(e['record-source'].textContent,/EV-AR-A/);assert.match(e.metadata.textContent,/EV-AR-A/);
 assert.equal(e.segments.children[0].children[1].value,'unsaved A');assert.equal(s.read('dirty'),true);assert.equal(s.fetches(),0);
}
const settle=()=>new Promise(resolve=>setImmediate(resolve));
for(const outcome of ['failure','success','late'])test(`open-task ${outcome}: loaded and target context remain explicit`,async()=>{
 const s=setup();s.elements['open-task'].onclick();assert.equal(s.requests.length,1);oldContent(s,'AR-B');
 if(outcome==='late'){s.elements.run.value='AR-C';s.elements.run.fire('input');oldContent(s,'AR-C')}
 if(outcome==='failure')s.requests[0].reject(Error('synthetic read failure'));else s.requests[0].resolve(record('AR-B'));
 await settle();assert.equal(s.read('busy'),false);
 if(outcome==='success'){assert.match(s.elements['loaded-context'].textContent,/已载入.*AR-B/);assert.doesNotMatch(s.elements['loaded-context'].textContent,/未载入/);for(const id of ['record-source','metadata']){assert.match(s.elements[id].textContent,/EV-AR-B/);assert.doesNotMatch(s.elements[id].textContent,/EV-AR-A/)}assert.equal(s.read('dirty'),false)}
 else oldContent(s,outcome==='late'?'AR-C':'AR-B');
 assert.equal(s.fetches(),0);
});
test('manual run change retains drafts and labels both old source displays',()=>{const s=setup();s.elements.run.value='AR-B';s.elements.run.fire('input');oldContent(s,'AR-B');assert.equal(s.requests.length,0)});
