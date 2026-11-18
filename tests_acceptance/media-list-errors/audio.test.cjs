// New ordinary synthetic successful-save tests. DOM/HTTP doubles, not a browser or ASR.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync('service/mcis_service/audio_review/review.html','utf8').split('<script>')[1].split('</script>')[0];
function setup(){
 class Element{constructor(){this.value='';this.textContent='';this.children=[];}addEventListener(n,f){(this.events??={})[n]=f;}setAttribute(){}removeAttribute(){}load(){}pause(){}append(...xs){this.children.push(...xs)}replaceChildren(){this.children=[]}}
 const elements={},events={};let release,fail,requests=0;
 const ctx=vm.createContext({document:{getElementById:id=>elements[id]??(elements[id]=new Element()),createElement:()=>new Element()},window:{addEventListener:(name,fn)=>events[name]=fn},URL:{revokeObjectURL(){}},confirm:()=>false,fetch:async(url)=>{requests++;const prior=JSON.parse(vm.runInContext('JSON.stringify(state)',ctx));return new Promise((resolve,reject)=>{fail=()=>reject(Error("synthetic transport failure"));release=()=>resolve({ok:true,json:async()=>url.includes("/source/")?{source:{caseId:prior.caseId},humanListened:false,authenticityVerified:false}:[{caseId:prior.caseId,runId:prior.runId,taskId:"TASK"}]})})}});
 vm.runInContext(script,ctx);
 vm.runInContext(`state={caseId:'SYNTHETIC',runId:'AR-fixture',revision:0,initial:{audio:{frames:8000,sampleRateHz:8000},machineDraft:{transcript:{segments:[{id:'s1',text:'synthetic',startMs:0,endMs:500},{id:'s2',text:'other',startMs:500,endMs:1000}],unlocatedSegments:[]}}},humanRevisions:[]};context='SYNTHETIC';el('case').value=context;el('run').value=state.runId;render();`,ctx);
 return {ctx,elements,boxes:elements.segments.children,release:()=>release(),fail:()=>fail(),requests:()=>requests,warning:()=>{let warned=false;events.beforeunload({preventDefault(){warned=true}});return warned;}};
}
function change(row,text){row.children[1].value=text;row.children[1].oninput();row.children[5].value='synthetic correction';row.children[5].oninput();}
const pairs=[['list', 'runs'], ['source', 'source-context']];
for(const [button] of pairs){
 test(button+' late error preserves current status',async()=>{const s=setup(),p=s.elements[button].onclick();s.elements.case.value='OTHER';s.elements.case.events.input();s.elements.status.textContent='new context';s.fail();await p;assert.equal(s.elements.status.textContent,'new context');assert.equal(s.requests(),1);});
 test(button+' current error is explicit',async()=>{const s=setup(),p=s.elements[button].onclick();s.fail();await p;assert.match(s.elements.status.textContent,/不自动重试/);assert.equal(s.requests(),1);});
}
