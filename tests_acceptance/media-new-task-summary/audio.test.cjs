// New ordinary synthetic successful-save tests. DOM/HTTP doubles, not a browser or ASR.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync('service/mcis_service/audio_review/review.html','utf8').split('<script>')[1].split('</script>')[0];
function setup(){
 class Element{constructor(){this.value='';this.textContent='';this.children=[];}addEventListener(n,f){(this.events??={})[n]=f;}setAttribute(){}removeAttribute(){}load(){}pause(){}append(...xs){this.children.push(...xs)}replaceChildren(){this.children=[]}}
 const elements={},events={};let release,requests=0;
 const ctx=vm.createContext({document:{getElementById:id=>elements[id]??(elements[id]=new Element()),createElement:()=>new Element()},window:{addEventListener:(name,fn)=>events[name]=fn},URL:{revokeObjectURL(){}},crypto:{randomUUID:()=> '11111111-1111-4111-8111-111111111111'},confirm:()=>false,fetch:async()=>{requests++;const prior=JSON.parse(vm.runInContext('JSON.stringify(state)',ctx));return new Promise(resolve=>{release=()=>resolve({ok:true,json:async()=>({...prior,runId:"AR-"+"1".repeat(32)})})})}});
 vm.runInContext(script,ctx);
 vm.runInContext(`state={caseId:'SYNTHETIC',runId:'AR-fixture',revision:0,initial:{audio:{frames:8000,sampleRateHz:8000},machineDraft:{transcript:{segments:[{id:'s1',text:'synthetic',startMs:0,endMs:500},{id:'s2',text:'other',startMs:500,endMs:1000}],unlocatedSegments:[]}}},humanRevisions:[]};context='SYNTHETIC';el('case').value=context;el('run').value=state.runId;render();`,ctx);
 return {ctx,elements,boxes:elements.segments.children,release:()=>release(),requests:()=>requests,warning:()=>{let warned=false;events.beforeunload({preventDefault(){warned=true}});return warned;}};
}
function change(row,text){row.children[1].value=text;row.children[1].oninput();row.children[5].value='synthetic correction';row.children[5].oninput();}
test('audio generated task clears previous summary but preserves current draft',()=>{
 const s=setup();change(s.elements.segments.children[0],'kept draft');vm.runInContext("el('task-id').value='';el('task-output').textContent='previous task list'",s.ctx);s.elements['new-task'].onclick();assert.equal(s.elements['task-id'].value,'11111111111141118111111111111111');assert.equal(s.elements['task-output'].textContent,'');const current=s.elements.segments.children[0];assert.equal(current.children[1].value,'kept draft');assert.equal(s.warning(),true);assert.equal(s.requests(),0);
});
