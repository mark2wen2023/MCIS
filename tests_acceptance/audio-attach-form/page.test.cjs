// New ordinary synthetic successful-save tests. DOM/HTTP doubles, not a browser or ASR.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync('service/mcis_service/audio_review/review.html','utf8').split('<script>')[1].split('</script>')[0];
function setup(){
 class Element{constructor(){this.value='';this.textContent='';this.children=[];}addEventListener(n,f){(this.events??={})[n]=f;}setAttribute(){}removeAttribute(){}load(){}pause(){}append(...xs){this.children.push(...xs)}replaceChildren(){this.children=[]}}
 const elements={},events={};let release,requests=0;
 const ctx=vm.createContext({document:{getElementById:id=>elements[id]??(elements[id]=new Element()),createElement:()=>new Element()},window:{addEventListener:(name,fn)=>events[name]=fn},URL:{revokeObjectURL(){}},confirm:()=>false,fetch:async()=>{requests++;const prior=JSON.parse(vm.runInContext('JSON.stringify(state)',ctx));return new Promise(resolve=>{release=()=>resolve({ok:true,json:async()=>({...prior,runId:"AR-11111111111111111111111111111111"})})})}});
 vm.runInContext(script,ctx);
 vm.runInContext(`state={caseId:'SYNTHETIC',runId:'AR-fixture',revision:0,initial:{audio:{frames:8000,sampleRateHz:8000},machineDraft:{transcript:{segments:[{id:'s1',text:'synthetic',startMs:0,endMs:500},{id:'s2',text:'other',startMs:500,endMs:1000}],unlocatedSegments:[]}}},humanRevisions:[]};context='SYNTHETIC';el('case').value=context;el('run').value=state.runId;render();`,ctx);
 return {ctx,elements,boxes:elements.segments.children,release:()=>release(),requests:()=>requests,warning:()=>{let warned=false;events.beforeunload({preventDefault(){warned=true}});return warned;}};
}
function change(row,text){row.children[1].value=text;row.children[1].oninput();row.children[5].value='synthetic correction';row.children[5].oninput();}
for(const field of ['audio-digest','draft-digest','ack'])for(const back of [false,true])test('attach ignores changed form '+field+' back='+back,async()=>{
 const s=setup(),row=s.boxes[0],p=s.elements.attach.onclick(),x=s.elements[field],prop=field==='ack'?'checked':'value',old=x[prop];x[prop]=field==='ack'?true:'new receipt';x.events?.input?.();if(back){x[prop]=old;x.events?.input?.();}s.release();await p;assert.equal(s.elements.segments.children[0],row);assert.equal(s.elements.run.value,'AR-fixture');assert.match(s.elements.status.textContent,/核查/);assert.equal(s.requests(),1);
});
test('attach unchanged form accepts new run',async()=>{const s=setup(),p=s.elements.attach.onclick();s.release();await p;assert.equal(s.elements.run.value,'AR-11111111111111111111111111111111');assert.equal(s.requests(),1);});
