// Real production json() parses synthetic fetch responses. No actual network or backend.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync(process.env.AUDIO_PAGE_SOURCE||'service/mcis_service/audio_review/review.html','utf8').split('<script>')[1].split('</script>')[0];
const run='AR-'+'a'.repeat(32),code='AUDIO_REVISION_STALE';
function setup(prior=false){
 const els={},requests=[],writes=[],events={};
 class E{constructor(){this.value='';this.children=[];this.events={};this.textContent=''}addEventListener(k,f){(this.events[k]??=[]).push(f)}fire(k){this['on'+k]?.();for(const f of this.events[k]||[])f()}setAttribute(){}removeAttribute(){}pause(){}load(){}append(...x){this.children.push(...x)}replaceChildren(){this.children=[]}}
 const fixture={caseId:'SYN-1',runId:run,revision:2,humanRevisions:[],initial:{audio:{frames:8000,sampleRateHz:8000},machineDraft:{source:{},transcript:{segments:[{id:'s1',text:'synthetic',startMs:null,endMs:null},{id:'s2',text:'other synthetic',startMs:null,endMs:null}],unlocatedSegments:[]}}}};
 const location={search:''};const ctx=vm.createContext({document:{getElementById:id=>els[id]??(els[id]=new E()),createElement:()=>new E()},window:{addEventListener:(k,f)=>events[k]=f},URL:{revokeObjectURL(){}},location,history:{replaceState(){writes.push('unexpected')}},confirm:()=>true,fixture,fetch:(path,options)=>{assert.equal(options.method,'POST');assert.equal(path,'/api/v1/cases/SYN-1/audio-reviews/'+run+'/revisions');return new Promise((resolve,reject)=>requests.push({path,options,resolve,reject}))}});
 vm.runInContext(script,ctx);vm.runInContext("state=fixture;context=fixture.caseId;el('case').value=context;el('run').value=state.runId;render()",ctx);
 const row=els.segments.children[0];row.children[1].value='unsaved correction';row.children[1].fire('input');row.children[5].value='synthetic reason';row.children[5].fire('input');
 if(prior)vm.runInContext("rememberUnknownSave('prior unrelated unknown')",ctx);
 return {els,requests,writes,location,read:s=>vm.runInContext(s,ctx),warning:()=>{let warned=false;events.beforeunload({preventDefault(){warned=true}});return warned;},save:()=>row.children[7].onclick()};
}
function respond(s,status,body){s.requests[0].resolve({status,ok:status>=200&&status<300,json:async()=>body})}

function edit(s,index,value,segment=0){const n=s.els.segments.children[segment].children[index];n.value=value;n.fire('input');}
function result(s){const d=JSON.parse(s.read('JSON.stringify(state)'));return {...d,revision:3,humanRevisions:[...d.humanRevisions,JSON.parse(s.requests[0].options.body)]};}
for(const [index,value] of [[1,'later text'],[2,'transcription_checked'],[3,'100'],[4,'500'],[5,'later reason']])test('same segment edit and revert remains unsaved: '+index,async()=>{
 const s=setup(),before=s.els.segments.children[0].children[index].value,p=s.save(),d=result(s);
 edit(s,index,value);edit(s,index,before);respond(s,200,d);await p;
 assert.equal(s.read('state.revision'),3);assert.equal(s.read('unknownSaves.size'),0);assert.equal(s.read('dirtySegments.has("s1")'),true);assert.equal(s.warning(),true);
 assert.equal(s.els.segments.children[0].children[index].value,before);assert.match(s.els.status.textContent,/已保存提交时内容.*之后修改的未保存输入/);assert.equal(s.writes.length,0);assert.equal(s.location.search,'');assert.equal(s.requests.length,1);
});
test('other segment edits do not mark submitted segment dirty',async()=>{const s=setup(),p=s.save(),d=result(s);edit(s,1,'other new draft',1);respond(s,200,d);await p;assert.equal(s.read('state.revision'),3);assert.equal(s.read('dirtySegments.has("s1")'),false);assert.equal(s.read('dirtySegments.has("s2")'),true);assert.equal(s.els.segments.children[1].children[1].value,'other new draft');assert.equal(s.warning(),true);assert.equal(s.writes.length,0);assert.equal(s.read('unknownSaves.size'),0)});
test('no subsequent segment edit clears submitted dirty; prior unknown remains',async()=>{const s=setup(true),p=s.save();respond(s,200,result(s));await p;assert.equal(s.read('state.revision'),3);assert.equal(s.read('dirtySegments.has("s1")'),false);assert.equal(s.warning(),false);assert.equal(s.read('unknownSaves.size'),1);assert.equal(s.writes.length,0)});
test('edit generation does not reject matching response or clear prior unknown',async()=>{const s=setup(true),p=s.save(),d=result(s);edit(s,1,'new text');respond(s,200,d);await p;assert.equal(s.read('state.revision'),3);assert.equal(s.read('unknownSaves.size'),1);assert.equal(s.els.segments.children[0].children[1].value,'new text');assert.equal(s.warning(),true);assert.equal(s.writes.length,0)});
