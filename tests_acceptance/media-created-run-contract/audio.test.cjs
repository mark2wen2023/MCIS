// New ordinary synthetic successful-save tests. DOM/HTTP doubles, not a browser or ASR.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync('service/mcis_service/audio_review/review.html','utf8').split('<script>')[1].split('</script>')[0];
function setup(mutate=x=>x){
 class Element{constructor(){this.value='';this.textContent='';this.children=[];}addEventListener(n,f){(this.events??={})[n]=f;}setAttribute(){}removeAttribute(){}load(){}pause(){}append(...xs){this.children.push(...xs)}replaceChildren(){this.children=[]}}
 const elements={},events={};let release,requests=0;
 const ctx=vm.createContext({document:{getElementById:id=>elements[id]??(elements[id]=new Element()),createElement:()=>new Element()},window:{addEventListener:(name,fn)=>events[name]=fn},URL:{revokeObjectURL(){}},confirm:()=>false,fetch:async()=>{requests++;const prior=JSON.parse(vm.runInContext('JSON.stringify(state)',ctx));return new Promise(resolve=>{release=()=>resolve({ok:true,json:async()=>mutate({...prior,runId:"AR-"+"1".repeat(32)})})})}});
 vm.runInContext(script,ctx);
 vm.runInContext(`state={caseId:'SYNTHETIC',runId:'AR-00000000000000000000000000000000',revision:0,initial:{audio:{frames:8000,sampleRateHz:8000},machineDraft:{transcript:{segments:[{id:'s1',text:'synthetic',startMs:0,endMs:500},{id:'s2',text:'other',startMs:500,endMs:1000}],unlocatedSegments:[]}}},humanRevisions:[]};context='SYNTHETIC';el('case').value=context;el('run').value=state.runId;render();`,ctx);
 return {ctx,elements,boxes:elements.segments.children,release:()=>release(),requests:()=>requests,warning:()=>{let warned=false;events.beforeunload({preventDefault(){warned=true}});return warned;}};
}
function change(row,text){row.children[1].value=text;row.children[1].oninput();row.children[5].value='synthetic correction';row.children[5].oninput();}
for(const [name,mutate] of [
 ['same run',d=>({...d,runId:'AR-00000000000000000000000000000000'})],
 ['blank run',d=>({...d,runId:''})],
 ['invalid run',d=>({...d,runId:'not-a-run'})],
 ['nonzero revision',d=>({...d,revision:1})],
 ['existing history',d=>({...d,humanRevisions:[{synthetic:true}]})]
])test('audio create rejects '+name+' response without replacing input',async()=>{
 const s=setup(mutate),row=s.boxes[0],p=s.elements.attach.onclick();s.release();await p;assert.equal(s.elements.segments.children[0],row);assert.equal(s.elements.run.value,'AR-00000000000000000000000000000000');assert.match(s.elements.status.textContent,/核查/);assert.equal(s.requests(),1);
});
test('audio create accepts new initial run response',async()=>{const s=setup(),p=s.elements.attach.onclick();s.release();await p;assert.equal(s.elements.run.value,'AR-'+'1'.repeat(32));assert.equal(s.requests(),1);});
