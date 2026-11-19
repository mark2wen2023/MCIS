// Actual server-shaped inline source; no network, original, decode or real model.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const pages=JSON.parse(fs.readFileSync(0,'utf8'));
async function check(media,mode){
 const els={},requests=[];class E{constructor(){this.value='';this.children=[];this.events={};this.textContent=''}addEventListener(k,f){this.events[k]=f}setAttribute(){}removeAttribute(){}pause(){}load(){}append(...x){this.children.push(...x)}replaceChildren(){this.children=[]}}
 const run=(media==='image'?'OCR-':'AR-')+'a'.repeat(32);
 const fixture=media==='image'?{caseId:'SYN-1',runId:run,revision:0,reviews:[],initial:{artifactTaskId:'synthetic-task',candidate:{source:{},text_lines:[]}}}:{caseId:'SYN-1',runId:run,revision:0,humanRevisions:[],initial:{audio:{},machineDraft:{source:{},transcript:{segments:[],unlocatedSegments:[]}}}};
 const ctx=vm.createContext({document:{getElementById:id=>els[id]??(els[id]=new E()),createElement:()=>new E()},window:{addEventListener(){}},URL:{revokeObjectURL(){}},confirm:()=>true,crypto:{randomUUID:()=> 'a'.repeat(32)},OcrPagePreview:{create:()=>({clear(){},load(){throw Error('original forbidden')},select(){}})},fetch(){throw Error('real fetch forbidden')},createImageBitmap(){throw Error('decode forbidden')},fixture});
 vm.runInContext(pages[media][mode].split('<script>')[1].split('</script>')[0],ctx);
 const taskIds=media==='image'?['new-task','start-task','list-tasks','check-task']:['new-task','start-task','task-status','task-list','open-task'];
 for(const id of taskIds)assert.equal(typeof els[id]?.onclick,mode==='full'?'function':'undefined');
 ctx.memoryRequest=async(path,body)=>{requests.push({path,body});if(path.endsWith('-tasks'))return [];return fixture};
 vm.runInContext('json=memoryRequest',ctx);
 els.case.value='SYN-1';els.run.value=run;
 await els.load.onclick();assert.equal(vm.runInContext('state.runId',ctx),run);assert.equal(requests.length,1);
 assert.match(requests[0].path,new RegExp('/'+media+'-reviews/'));
 // Existing-results import remains available and cannot invoke a task route.
 els.run.value='';vm.runInContext('state=null;context=null',ctx);
 if(media==='image')delete fixture.initial.artifactTaskId;
 await els[media==='image'?'create':'attach'].onclick();assert.equal(requests.length,2);assert.match(requests[1].path,new RegExp('/'+media+'-reviews$'));
 if(media==='image'){
  fixture.initial.artifactTaskId='synthetic-task';vm.runInContext('state=fixture;context=fixture.caseId;render()',ctx);
  const labels=els.source.children.map(x=>x.textContent);
  assert.equal(labels.some(x=>x.includes('授权下载 raw')),mode==='full');
  assert.equal(labels.some(x=>x.includes('授权下载 candidate')),mode==='full');
  assert.ok(labels.some(x=>x.includes('授权下载 pdf')));
  if(mode==='limited')await assert.rejects(vm.runInContext("readOriginal('raw')",ctx),/限定核对模式/);
 }
 if(mode==='full'){
  // Unconfirmed start is stopped locally; explicit confirmation sends only a fake request.
  els[media==='image'?'task':'task-id'].value='a'.repeat(32);
  await els['start-task'].onclick();assert.equal(requests.length,2);
  els[media==='image'?'task-ack':'task-confirm'].checked=true;
  await els['start-task'].onclick();assert.equal(requests.length,3);assert.ok(requests[2].body.confirmed);
  assert.match(requests[2].path,media==='image'?/image-ocr-tasks$/:/audio-asr-tasks$/);
  await els[media==='image'?'list-tasks':'task-list'].onclick();assert.equal(requests.length,4);
 }else{
  assert.equal(requests.length,2);
  // Arbitrary URL flag is not a capability source; it also cannot start a task.
  ctx.URLSearchParams=URLSearchParams;vm.runInContext("reopenFromUrl('?tasks=true')",ctx);
  for(const id of taskIds)assert.equal(typeof els[id]?.onclick,'undefined');
  assert.equal(requests.length,2);
 }
 console.log(media+' '+mode+': task handlers, import/read, confirmation and artifact boundary PASS');
}
(async()=>{for(const m of ['image','audio'])for(const mode of ['limited','full'])await check(m,mode)})().catch(e=>{console.error(e);process.exitCode=1});
