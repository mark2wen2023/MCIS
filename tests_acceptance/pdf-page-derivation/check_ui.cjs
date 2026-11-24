// Actual HTML and controller, simulated DOM/canvas/decoder and bounded HTTP responses.
// Not a real browser, authorization or OCR test.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const {webcrypto,createHash}=require('node:crypto');const {pathToFileURL}=require('node:url');
const root=path.resolve(__dirname,'../../service/mcis_service/image_review');
const html=fs.readFileSync(path.join(root,'review.html'),'utf8');
const source='92cf698d3070092139444f94b7dacb7286f774b6186503917e534b253734e774';
const bytes=Buffer.alloc(33);Buffer.from([137,80,78,71,13,10,26,10]).copy(bytes);bytes.writeUInt32BE(13,8);bytes.write('IHDR',12);bytes.writeUInt32BE(256,16);bytes.writeUInt32BE(256,20);
function reply(){return {caseId:'SYN-XREPO-001',runId:'OCR-synthetic-pdf',revision:0,description:{sourceSha256:source,physicalPage:1,renderSpec:{format:'PNG',dpi:72,scaleTo:256,pageBox:'MediaBox'},pageSha256:createHash('sha256').update(bytes).digest('hex'),width:256,height:256},pngBase64:bytes.toString('base64')};}
async function harness(t,fetcher=async()=>reply()){
 const {Window}=await import(pathToFileURL(path.resolve(process.env.MCIS_HAPPY_DOM)).href);
 const window=new Window({url:'http://127.0.0.1/'});t.after(()=>window.happyDOM.close());
 window.document.body.innerHTML=html;
 const draws=[];for(const canvas of window.document.querySelectorAll('canvas'))canvas.getContext=()=>({clearRect(){},drawImage(){draws.push('draw');},strokeRect(){draws.push('box');}});
 const requests=[];
 const context=vm.createContext({window,document:window.document,console,crypto:webcrypto,Blob,Uint8Array,ArrayBuffer,DataView,atob,URL,setTimeout,confirm:()=>true,createImageBitmap:async()=>({width:256,height:256,close(){}}),fetch:async(url,options)=>{requests.push({url,options});const d=await fetcher(url,options);if(d.arrayBuffer)return d;return {ok:true,json:async()=>d};}});
 for(const name of ['preview.js','pdf_host.js'])vm.runInContext(fs.readFileSync(path.join(root,name),'utf8'),context);
 vm.runInContext(html.match(/<script>\s*([\s\S]*?)<\/script>/)[1],context);
 const state={caseId:'SYN-XREPO-001',runId:'OCR-synthetic-pdf',revision:0,reviews:[],initial:{bindings:{pdf:'fixture'},sourceVersions:{pdf:{sha256:source},image:{sha256:createHash('sha256').update(bytes).digest('hex')}},candidate:{source:{pdf_page_1based:1,pdf_sha256:source,image_sha256:createHash('sha256').update(bytes).digest('hex'),width:256,height:256},recognizer:{},text_lines:[{line_index:0,text:'SYNTHETIC LINE',bbox:[0,0,2,1]}]}}};
 vm.runInContext('state='+JSON.stringify(state)+";context=state.caseId;el('case').value=context;el('run').value=state.runId;render();",context);
 return {state,setFetch:f=>fetcher=f,context,draws,requests,document:window.document,run:s=>vm.runInContext(s,context),load:()=>vm.runInContext("el('show-pdf').onclick()",context)};
}
test('actual HTML derived view hides OCR lines, old selection, and guards retained locate callback',async t=>{
 const h=await harness(t);assert.equal(h.document.getElementById('show-pdf').hidden,true); // default off HTML
 h.run("el('lines').firstChild.classList.add('selected');el('lines').querySelector('[aria-pressed]').setAttribute('aria-pressed','true')");
 await h.load();assert.equal(h.requests.length,1);assert.equal(h.document.getElementById('lines').hidden,true);
 assert.equal(h.run("preview.inputKind"),'pdf-derived-page');assert.equal(h.document.querySelector('[aria-pressed]').getAttribute('aria-pressed'),'false');
 const before=h.draws.length;h.document.querySelector('[aria-pressed]').onclick();assert.equal(h.draws.length,before);assert.equal(h.draws.includes('box'),false);
 assert.equal(h.requests[0].options.method,'POST');assert.deepEqual(JSON.parse(h.requests[0].options.body),{expectedRevision:0});
 h.run("el('clear-image').onclick()");assert.equal(h.document.getElementById('lines').hidden,false);assert.equal(h.run('preview.inputKind'),'registered-original');
});
for(const field of ['caseId','runId','revision','sourceSha256','physicalPage']){
 test('wrong response '+field+' clears without draw',async t=>{
  const d=reply();if(field in d)d[field]=field==='revision'?1:'wrong';else d.description[field]=field==='physicalPage'?2:'0'.repeat(64);
  const h=await harness(t,async()=>d);await h.load();assert.equal(h.draws.length,0);assert.equal(h.run('preview.inputKind'),'registered-original');assert.match(h.document.getElementById('status').textContent,/绑定不符/);
 });
}
for(const control of ['case','run']){
 test(control+' switch away/back rejects delayed HTTP result',async t=>{
  let resolve;const h=await harness(t,()=>new Promise(r=>resolve=r));const pending=h.load();
  const old=h.document.getElementById(control).value;h.document.getElementById(control).value="OTHER";h.run("el('"+control+"').dispatchEvent(new window.Event('input'))");h.document.getElementById(control).value=old;h.run("el('"+control+"').dispatchEvent(new window.Event('input'))");
  resolve(reply());await pending;assert.equal(h.draws.length,0);assert.equal(h.run('preview.inputKind'),'registered-original');
 });
}
test('current revision changed while response held does not draw',async t=>{
 let resolve;const h=await harness(t,()=>new Promise(r=>resolve=r));const pending=h.load();h.run('state.revision=1');resolve(reply());await pending;assert.equal(h.draws.length,0);
});
test('failure clears a previously displayed page and permits explicit retry',async t=>{
 let fail=false;const h=await harness(t,async()=>{if(fail)throw Error('synthetic transport failure');return reply()});
 await h.load();fail=true;await h.load();assert.equal(h.run('preview.inputKind'),'registered-original');assert.equal(h.run('state'),null);fail=false;h.setFetch(async()=>h.state);await h.run("el('load').onclick()");h.setFetch(async()=>reply());await h.load();assert.equal(h.run('preview.inputKind'),'pdf-derived-page');
});

for(const control of ['case','run']){
 test(control+' invalidates retained download/save even A-B-A; reread restores PNG only for fresh callbacks',async t=>{
  const h=await harness(t);
  const oldDownload=h.document.querySelector('#source button').onclick;
  const oldSave=h.document.querySelector('[data-ocr-review]').onclick;
  await h.load();const n=h.requests.length;
  const input=h.document.getElementById(control),original=input.value;
  input.value='OTHER';h.run("el('"+control+"').dispatchEvent(new window.Event('input'))");
  await oldDownload();await oldSave();assert.equal(h.requests.length,n);
  assert.equal(h.document.getElementById('source').children.length,0);
  assert.equal(h.document.getElementById('lines').children.length,0);
  input.value=original;h.run("el('"+control+"').dispatchEvent(new window.Event('input'))");
  h.run("el('clear-image').onclick()");await oldDownload();await oldSave();assert.equal(h.requests.length,n);
  h.setFetch(async()=>h.state);await h.run("el('load').onclick()");assert.equal(h.requests.length,n+1);
  await oldDownload();await oldSave();assert.equal(h.requests.length,n+1);
  h.setFetch(async()=>({ok:true,arrayBuffer:async()=>bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),headers:{get:()=>createHash('sha256').update(bytes).digest('hex')}}));
  await h.run("el('show-image').onclick()");assert.equal(h.requests.length,n+2);assert.equal(h.run('preview.inputKind'),'registered-original');
  h.document.querySelector('[aria-pressed]').onclick();assert.equal(h.draws.includes('box'),true);
 });
}
test('same active context clear after derived restores PNG without a review reread',async t=>{
 const h=await harness(t);await h.load();h.run("el('clear-image').onclick()");
 h.setFetch(async()=>({ok:true,arrayBuffer:async()=>bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),headers:{get:()=>createHash('sha256').update(bytes).digest('hex')}}));
 await h.run("el('show-image').onclick()");assert.equal(h.requests.length,2);h.document.querySelector('[aria-pressed]').onclick();assert.equal(h.draws.includes('box'),true);
});

test('reread new revision permanently invalidates old callbacks',async t=>{
 const h=await harness(t);const download=h.document.querySelector('#source button').onclick,save=h.document.querySelector('[data-ocr-review]').onclick;
 await h.load();h.setFetch(async()=>({...h.state,revision:1}));await h.run("el('load').onclick()");const n=h.requests.length;
 await download();await save();assert.equal(h.requests.length,n);assert.equal(h.run('state.revision'),1);
});
