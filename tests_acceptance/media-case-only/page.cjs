// Actual inline source, fake DOM/history and memory response queue. No real requests.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const pages=JSON.parse(fs.readFileSync(0,'utf8'));
const settle=()=>new Promise(r=>setImmediate(r));
function setup(media,mode,search){
 const els={},requests=[],writes=[];
 class E{constructor(){this.value='';this.children=[];this.events={};this.textContent=''}addEventListener(k,f){(this.events[k]??=[]).push(f)}fire(k){this['on'+k]?.();for(const f of this.events[k]||[])f()}setAttribute(){}removeAttribute(){}load(){}pause(){}append(...x){this.children.push(...x)}replaceChildren(){this.children=[]}}
 const location={search},history={replaceState(state,title,url){assert.equal(state,null);assert.equal(title,'');writes.push(url);location.search=url},pushState(){throw Error('push forbidden')}};
 const ctx=vm.createContext({document:{getElementById:id=>els[id]??(els[id]=new E()),createElement:()=>new E()},window:{addEventListener(){}},location,history,URLSearchParams,URL:{revokeObjectURL(){}},confirm:()=>true,OcrPagePreview:{create:()=>({clear(){},load(){throw Error('original forbidden')},select(){throw Error('preview forbidden')}})},fetch(){throw Error('real fetch forbidden')},createImageBitmap(){throw Error('decode forbidden')},memoryRequest:(path,body)=>new Promise((resolve,reject)=>requests.push({path,body,resolve,reject}))});
 const boot="reopenFromUrl(typeof location==='undefined'?'':location.search);";
 const script=pages[media][mode].split('<script>')[1].split('</script>')[0].replace(boot,'json=memoryRequest;'+boot);
 vm.runInContext(script,ctx);
 return {els,requests,writes,location,read:s=>vm.runInContext(s,ctx)};
}
function record(media){const run=(media==='image'?'OCR-':'AR-')+'a'.repeat(32);return media==='image'?{caseId:'SYN-1',runId:run,revision:0,reviews:[],initial:{candidate:{source:{},text_lines:[]}}}:{caseId:'SYN-1',runId:run,revision:0,humanRevisions:[],initial:{audio:{},machineDraft:{source:{},transcript:{segments:[],unlocatedSegments:[]}}}}}
async function check(media,mode){
 const d=record(media),run=d.runId;
 const s=setup(media,mode,'?case=SYN%2D1');
 assert.equal(s.els.case.value,'SYN-1');assert.equal(s.els.run.value,'');assert.equal(s.requests.length,0);assert.equal(s.writes.length,0);assert.equal(s.read('state'),null);assert.match(s.els['reopen-context'].textContent,/未查询是否已有记录/);
 assert.equal(typeof s.els['start-task']?.onclick,mode==='full'?'function':'undefined');
 await s.els.load.onclick();assert.equal(s.requests.length,0);assert.equal(s.writes.length,0);
 const importing=s.els[media==='image'?'create':'attach'].onclick();assert.equal(s.requests.length,1);assert.equal(s.requests[0].path,'/api/v1/cases/SYN-1/'+media+'-reviews');assert.equal(s.writes.length,0);s.requests[0].resolve(d);await importing;
 const expected='?case=SYN-1&run='+run;assert.deepEqual(s.writes,[expected]);assert.equal(s.read('state.runId'),run);
 const reopen=setup(media,mode,s.location.search);assert.equal(reopen.requests.length,1);assert.equal(reopen.requests[0].path,'/api/v1/cases/SYN-1/'+media+'-reviews/'+run);reopen.requests[0].resolve(d);await settle();assert.equal(reopen.read('state.runId'),run);
 for(const bad of ['?run='+run,'?case=&run='+run,'?case=%20','?case=SYN-1%0A','?case=SYN-1&run=','?case=SYN-1&case=SYN-1','?case=SYN-1&case=SYN-2','?case=SYN-1&role=Investigator','?case=SYN-1&tasks=true','?case=SYN-1&run='+run+'&run='+run,'?case=SYN-1&run='+run+'%0A','?case=SYN-1&revision=0']){
  const n=setup(media,mode,bad);assert.equal(n.els.case.value,'');assert.equal(n.els.run.value,'');assert.equal(n.requests.length,0);assert.equal(n.writes.length,0);assert.match(n.els['reopen-context'].textContent,/链接无效/);
 }
 for(const outcome of ['late','mismatch','malformed','failure']){
  const n=setup(media,mode,'?case=SYN-1');const p=n.els[media==='image'?'create':'attach'].onclick();
  if(outcome==='late'){n.els.case.value='SYN-2';n.els.case.fire('input')}
  if(outcome==='failure')n.requests[0].reject(Error('synthetic ordinary error'));
  else n.requests[0].resolve(outcome==='mismatch'?{...d,caseId:'SYN-2'}:outcome==='malformed'?{caseId:'SYN-1',runId:run}:d);
  await p;assert.equal(n.writes.length,0);assert.equal(n.requests.length,1);assert.equal(n.read('state'),null);assert.equal(n.location.search,'?case=SYN-1');
 }
 const manual=setup(media,mode,'');assert.equal(manual.requests.length,0);assert.equal(manual.writes.length,0);assert.equal(manual.els.case.value,'');
 console.log(media+' '+mode+': case-only zero-request, invalid forms, accepted import/reopen, late/unconfirmed and manual PASS');
}
(async()=>{for(const media of ['image','audio'])for(const mode of ['full','limited'])await check(media,mode)})().catch(e=>{console.error(e);process.exitCode=1});
