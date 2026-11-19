// New ordinary synthetic successful-save tests. DOM/HTTP doubles, not a browser or ASR.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync('service/mcis_service/audio_review/review.html','utf8').split('<script>')[1].split('</script>')[0];
function setup(){
 class Element{constructor(){this.value='';this.textContent='';this.children=[];}addEventListener(name,fn){(this.events??={})[name]=fn;}setAttribute(){}removeAttribute(){}load(){}pause(){}append(...xs){this.children.push(...xs)}replaceChildren(){this.children=[]}}
 const elements={},events={};let release,requests=0;
 const ctx=vm.createContext({document:{getElementById:id=>elements[id]??(elements[id]=new Element()),createElement:()=>new Element()},window:{addEventListener:(name,fn)=>events[name]=fn},URL:{revokeObjectURL(){}},confirm:()=>false,fetch:async(path,options)=>{requests++;const body=JSON.parse(options.body),prior=JSON.parse(vm.runInContext('JSON.stringify(state)',ctx));return new Promise(resolve=>{release=()=>resolve({ok:true,json:async()=>({...prior,revision:prior.revision+1,humanRevisions:[...prior.humanRevisions,body]})})})}});
 vm.runInContext(script,ctx);
 vm.runInContext(`state={caseId:'SYNTHETIC',runId:'AR-fixture',revision:0,initial:{audio:{frames:8000,sampleRateHz:8000},machineDraft:{transcript:{segments:[{id:'s1',text:'synthetic',startMs:0,endMs:500},{id:'s2',text:'other',startMs:500,endMs:1000}],unlocatedSegments:[]}}},humanRevisions:[]};context='SYNTHETIC';el('case').value=context;el('run').value=state.runId;render();`,ctx);
 return {ctx,elements,boxes:elements.segments.children,release:()=>release(),requests:()=>requests,warning:()=>{let warned=false;events.beforeunload({preventDefault(){warned=true}});return warned;}};
}
function change(row,text){row.children[1].value=text;row.children[1].oninput();row.children[5].value='synthetic correction';row.children[5].oninput();}
for(const field of ['case','run'])test('late save after '+field+' selection change leaves old state and draft',async()=>{
 const s=setup(),row=s.boxes[0];change(row,'submitted draft');const saving=row.children[7].onclick();
 s.elements[field].value='OTHER';s.elements[field].events.input();s.elements.status.textContent='current target feedback';s.release();await saving;
 assert.equal(vm.runInContext('state.revision',s.ctx),0);assert.equal(s.warning(),true);assert.equal(row.children[1].value,'submitted draft');assert.equal(s.requests(),1);assert.equal(s.elements.status.textContent,'current target feedback');assert.match(s.elements['save-unknown'].textContent,/SYNTHETIC/);
});
test('selection away and back still ignores late save',async()=>{
 const s=setup(),row=s.boxes[0];change(row,'submitted draft');const saving=row.children[7].onclick();
 const old=s.elements.run.value;s.elements.run.value='OTHER';s.elements.run.events.input();s.elements.run.value=old;s.elements.run.events.input();s.release();await saving;
 assert.equal(vm.runInContext('state.revision',s.ctx),0);assert.equal(s.warning(),true);assert.equal(s.requests(),1);
});
test('unchanged selection accepts matching save',async()=>{
 const s=setup(),row=s.boxes[0];change(row,'submitted draft');const saving=row.children[7].onclick();s.release();await saving;
 assert.equal(vm.runInContext('state.revision',s.ctx),1);assert.equal(s.warning(),false);assert.match(s.elements.status.textContent,/本段已保存/);
});
