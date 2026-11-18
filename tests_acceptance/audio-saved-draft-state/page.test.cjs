// New ordinary synthetic successful-save tests. DOM/HTTP doubles, not a browser or ASR.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync('service/mcis_service/audio_review/review.html','utf8').split('<script>')[1].split('</script>')[0];
function setup(){
 class Element{constructor(){this.value='';this.textContent='';this.children=[];}addEventListener(){}setAttribute(){}removeAttribute(){}load(){}pause(){}append(...xs){this.children.push(...xs)}replaceChildren(){this.children=[]}}
 const elements={},events={};let release,requests=0;
 const ctx=vm.createContext({document:{getElementById:id=>elements[id]??(elements[id]=new Element()),createElement:()=>new Element()},window:{addEventListener:(name,fn)=>events[name]=fn},URL:{revokeObjectURL(){}},confirm:()=>false,fetch:async(path,options)=>{requests++;const body=JSON.parse(options.body),prior=JSON.parse(vm.runInContext('JSON.stringify(state)',ctx));return new Promise(resolve=>{release=()=>resolve({ok:true,json:async()=>({...prior,revision:prior.revision+1,humanRevisions:[...prior.humanRevisions,body]})})})}});
 vm.runInContext(script,ctx);
 vm.runInContext(`state={caseId:'SYNTHETIC',runId:'AR-fixture',revision:0,initial:{audio:{frames:8000,sampleRateHz:8000},machineDraft:{transcript:{segments:[{id:'s1',text:'synthetic',startMs:0,endMs:500},{id:'s2',text:'other',startMs:500,endMs:1000}],unlocatedSegments:[]}}},humanRevisions:[]};context='SYNTHETIC';el('case').value=context;el('run').value=state.runId;render();`,ctx);
 return {ctx,elements,boxes:elements.segments.children,release:()=>release(),requests:()=>requests,warning:()=>{let warned=false;events.beforeunload({preventDefault(){warned=true}});return warned;}};
}
function change(row,text){row.children[1].value=text;row.children[1].oninput();row.children[5].value='synthetic correction';row.children[5].oninput();}
test('successful last draft save clears unsaved warning and permits reread',async()=>{
 const s=setup(),row=s.boxes[0];change(row,'saved synthetic');assert.equal(s.warning(),true);
 const saving=row.children[7].onclick();s.release();await saving;
 assert.match(s.elements.status.textContent,/本段已保存/);assert.equal(s.warning(),false);assert.equal(vm.runInContext('canReplace()',s.ctx),true);assert.equal(s.requests(),1);
});
test('saving one segment keeps other draft warning until both are saved',async()=>{
 const s=setup();change(s.boxes[0],'first');change(s.boxes[1],'second');
 let saving=s.boxes[0].children[7].onclick();s.release();await saving;
 assert.equal(s.warning(),true);assert.equal(s.boxes[1].children[1].value,'second');
 saving=s.boxes[1].children[7].onclick();s.release();await saving;
 assert.equal(s.warning(),false);assert.equal(s.requests(),2);assert.equal(vm.runInContext('state.humanRevisions.length',s.ctx),2);
});
test('edit during successful pending save remains unsaved without automatic retry',async()=>{
 const s=setup(),row=s.boxes[0];change(row,'submitted');const saving=row.children[7].onclick();
 change(row,'later unsaved');s.release();await saving;
 assert.equal(row.children[1].value,'later unsaved');assert.equal(s.warning(),true);assert.equal(s.requests(),1);
 assert.equal(vm.runInContext('state.humanRevisions[0].text',s.ctx),'submitted');assert.match(s.elements.status.textContent,/本段仍有之后修改的未保存输入/);
});
