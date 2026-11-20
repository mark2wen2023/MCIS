// Actual server-shaped script and production fetch wrapper; memory responses only.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(process.argv[2],'utf8');
assert(html.includes('<section hidden inert class="image-pane"'));
assert(html.includes('<details data-task-controls hidden inert>'));
assert(html.includes('服务器会话与逐案授权'));
const script=html.split('<script>')[1].split('</script>')[0];
const id='OCR-'+'a'.repeat(32);
const record={caseId:'SYN-A',runId:id,revision:0,reviews:[],initial:{mode:'imported-existing-output',candidate:{source:{},recognizer:{},text_lines:[{line_index:0,text:'synthetic',bbox:[0,0,1,1]}]}}};
function setup(search='?case=SYN-A'){
 const els={},requests=[],writes=[],events={},navigations=[];let accepted=true;
 class E{constructor(){this.value='';this.children=[];this.textContent='';this.events={};}addEventListener(k,f){(this.events[k]??=[]).push(f)}fire(k){this['on'+k]?.();for(const f of this.events[k]||[])f()}setAttribute(){}removeAttribute(){}append(...x){this.children.push(...x)}replaceChildren(){this.children=[]}}
 const location={search,assign:url=>navigations.push(url)};
 const ctx=vm.createContext({document:{getElementById:id=>els[id]??(els[id]=new E()),createElement:()=>new E()},window:{addEventListener:(n,f)=>events[n]=f},location,history:{replaceState(a,b,url){writes.push(url);location.search=url}},URLSearchParams,confirm:()=>accepted,OcrPagePreview:{create:()=>({clear(){},load(){throw Error('preview forbidden')},select(){throw Error('locate forbidden')}})},createImageBitmap(){throw Error('decode forbidden')},fetch:(path,options)=>{
  assert(!/tasks|download|preview|commit/.test(path));assert.equal(options.credentials,'same-origin');assert.equal(options.redirect,'error');
  return new Promise((resolve,reject)=>requests.push({path,options,resolve:d=>resolve({ok:true,json:async()=>d}),reject}));
 }});
 vm.runInContext(script,ctx);return {els,requests,writes,location,events,navigations,confirm:value=>accepted=value,read:s=>vm.runInContext(s,ctx)};
}
(async()=>{
 const s=setup();assert.equal(s.els.case.value,'SYN-A');assert.equal(s.requests.length,0);
 for(const key of ['start-task','check-task','list-tasks','new-task','show-image'])assert.equal(typeof s.els[key]?.onclick,'undefined');
 await assert.rejects(s.read("readOriginal('pdf')"),/尚未开放/);assert.equal(s.requests.length,0);
 let p=s.els.create.onclick();assert.equal(s.requests[0].options.method,'POST');s.requests[0].resolve(record);await p;
 assert.equal(s.read('state.runId'),id);assert.equal(s.writes.length,1);
 assert(!s.els.source.children.some(n=>n.textContent.includes('授权下载')));
 const row=s.els.lines.children[0];assert.equal(row.children[1].hidden,true);assert.equal(row.children[1].disabled,true);row.children[1].onclick();
 row.children[2].value='synthetic edited';row.children[2].fire('input');row.children[4].value='synthetic reason';row.children[4].fire('input');
 p=row.children[5].onclick();const submitted=JSON.parse(s.requests[1].options.body);
 const saved={...record,revision:1,reviews:[{...submitted,revision:1}]};s.requests[1].resolve(saved);await p;
 assert.equal(s.read('dirty'),false);assert.equal(s.read('state.revision'),1);
 const r=setup(s.location.search);assert.equal(r.requests.length,1);assert(r.requests[0].path.endsWith(id));r.requests[0].resolve(saved);await new Promise(resolve=>setImmediate(resolve));assert.equal(r.els.lines.children[0].children[2].value,'synthetic edited');
 const t=setup('?case=SYN-A&run='+id);t.els.case.value='SYN-B';t.els.case.fire('input');t.requests[0].resolve(record);await new Promise(resolve=>setImmediate(resolve));assert.equal(t.read('state'),null);assert.equal(t.writes.length,0);
 for(const query of ['', '?case=', '?case=SYN-A&run=', '?case=SYN-A&case=SYN-B', '?case=SYN-A&tasks=true']){const t=setup(query);assert.equal(t.requests.length,0);}
 const list=setup();p=list.els.list.onclick();list.requests[0].resolve([{caseId:'SYN-A',runId:id,utc:'synthetic',sourceCheck:'not-performed-by-list'}]);await p;assert(list.els['run-options'].children.length>0);assert.equal(list.writes.length,0);
 // Return uses accepted current scope, not URL or editable targets; no request.
 const back=setup();assert(back.els['pilot-return'],'old page lacks contextual return');assert.equal(back.requests.length,0);
 back.els['pilot-return'].onclick();assert.equal(back.navigations.length,0);
 p=back.els.create.onclick();back.requests[0].resolve(record);await p;assert.equal(back.els['pilot-return'].hidden,false);
 const input=back.els.lines.children[0].children[2];input.value='unsaved';input.fire('input');
 back.confirm(false);back.els['pilot-return'].onclick();assert.equal(back.navigations.length,0);assert.equal(back.read('dirty'),true);assert.equal(input.value,'unsaved');
 let prevented=false;const unload={preventDefault(){prevented=true;}};back.events.beforeunload(unload);assert(prevented);assert.equal(unload.returnValue,'');
 back.confirm(true);back.read('busy=true');back.els['pilot-return'].onclick();assert.equal(back.navigations.length,0);back.read('busy=false');back.els['pilot-return'].onclick();assert.deepEqual(back.navigations,['/pilot?case=SYN-A']);assert.equal(back.read('dirty'),true);assert.equal(back.requests.length,1);
 back.els.case.value='SYN-B';back.els.case.fire('input');assert.equal(back.els['pilot-return'].hidden,true);back.els['pilot-return'].onclick();assert.equal(back.navigations.length,1);
 // A loaded, B pending and fails: neither old return scope nor late A can navigate.
 back.els.run.value=id;back.els.run.fire('input');p=back.els.load.onclick();back.requests[1].reject(new Error('synthetic'));await p;assert.equal(back.els['pilot-return'].hidden,true);
 assert.equal(t.els['pilot-return'].hidden,true);t.els['pilot-return'].onclick();assert.equal(t.navigations.length,0);
 console.log('PASS pilot contextual return: explicit confirmation, retained draft/unload guard, target mismatch and stale response; no extra requests');
 console.log('PASS pilot shaped image: no forbidden controls/requests, case-only, import/save/reopen, stale response, invalid inputs, explicit list (memory only)');
})().catch(e=>{console.error(e);process.exitCode=1});
