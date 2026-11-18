// New ordinary synthetic successful-save tests. DOM/HTTP doubles, not a browser or ASR.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync('service/mcis_service/audio_review/review.html','utf8').split('<script>')[1].split('</script>')[0];
function setup(){
 class Element{constructor(){this.value='';this.textContent='';this.children=[];}addEventListener(n,f){(this.events??={})[n]=f;}setAttribute(){}removeAttribute(){}load(){}pause(){}append(...xs){this.children.push(...xs)}replaceChildren(){this.children=[]}}
 const elements={},events={};const releases=[],failures=[];let requests=0;
 const ctx=vm.createContext({document:{getElementById:id=>elements[id]??(elements[id]=new Element()),createElement:()=>new Element()},window:{addEventListener:(name,fn)=>events[name]=fn},URL:{revokeObjectURL(){}},confirm:()=>false,fetch:async()=>{requests++;const prior=JSON.parse(vm.runInContext('JSON.stringify(state)',ctx));return new Promise((resolve,reject)=>{failures.push(()=>reject(Error("synthetic transport error")));releases.push(()=>resolve({ok:true,json:async()=>({caseId:prior.caseId,taskId:"1".repeat(32),status:"succeeded",runId:"AR-new"})}));})}});
 vm.runInContext(script,ctx);
 vm.runInContext(`state={caseId:'SYNTHETIC',runId:'AR-fixture',revision:0,initial:{audio:{frames:8000,sampleRateHz:8000},machineDraft:{transcript:{segments:[{id:'s1',text:'synthetic',startMs:0,endMs:500},{id:'s2',text:'other',startMs:500,endMs:1000}],unlocatedSegments:[]}}},humanRevisions:[]};context='SYNTHETIC';el('task-id').value='1'.repeat(32);el('task-confirm').checked=true;el('case').value=context;el('run').value=state.runId;render();`,ctx);
 return {ctx,elements,boxes:elements.segments.children,release:(i=0)=>releases[i](),fail:(i=0)=>failures[i](),requests:()=>requests,warning:()=>{let warned=false;events.beforeunload({preventDefault(){warned=true}});return warned;}};
}
function change(row,text){row.children[1].value=text;row.children[1].oninput();row.children[5].value='synthetic correction';row.children[5].oninput();}
function begin(s){return s.elements['start-task'].onclick();}
function changed(s,field){const x=s.elements[field],p=field==='task-confirm'?'checked':'value',old=x[p];x[p]=p==='checked'?false:'OTHER';x.events?.input?.();x[p]=old;x.events?.input?.();}
test('audio start ignores changed case away-back',async()=>{const s=setup(),p=begin(s);changed(s,'case');s.release();await p;assert.doesNotMatch(s.elements['task-output'].textContent,/succeeded/);assert.equal(s.requests(),1);});
test('audio start ignores changed run away-back',async()=>{const s=setup(),p=begin(s);changed(s,'run');s.release();await p;assert.doesNotMatch(s.elements['task-output'].textContent,/succeeded/);assert.equal(s.requests(),1);});
test('audio start ignores changed task-id away-back',async()=>{const s=setup(),p=begin(s);changed(s,'task-id');s.release();await p;assert.doesNotMatch(s.elements['task-output'].textContent,/succeeded/);assert.equal(s.requests(),1);});
test('audio start ignores changed audio-digest away-back',async()=>{const s=setup(),p=begin(s);changed(s,'audio-digest');s.release();await p;assert.doesNotMatch(s.elements['task-output'].textContent,/succeeded/);assert.equal(s.requests(),1);});
test('audio start ignores changed task-confirm away-back',async()=>{const s=setup(),p=begin(s);changed(s,'task-confirm');s.release();await p;assert.doesNotMatch(s.elements['task-output'].textContent,/succeeded/);assert.equal(s.requests(),1);});
test('audio start retains input typed during request',async()=>{const s=setup(),p=begin(s);change(s.boxes[0],'new draft');s.release();await p;assert.doesNotMatch(s.elements['task-output'].textContent,/succeeded/);assert.equal(s.warning(),true);assert.equal(s.requests(),1);});
test('audio start ignores late transport error after selection',async()=>{const s=setup(),p=begin(s);s.elements.case.value='OTHER';s.elements.case.events?.input?.();s.elements['task-output'].textContent='new context';s.fail();await p;assert.equal(s.elements['task-output'].textContent,'new context');assert.equal(s.requests(),1);});
test('audio start unchanged displays result',async()=>{const s=setup(),p=begin(s);s.release();await p;assert.match(s.elements['task-output'].textContent,/succeeded/);assert.equal(s.requests(),1);});
