// Real production json() parses synthetic fetch responses. No actual network or backend.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync(process.env.IMAGE_PAGE_SOURCE||'service/mcis_service/image_review/review.html','utf8').split('<script>')[1].split('</script>')[0];
const run='OCR-'+'a'.repeat(32),code='OCR_REVISION';
function setup(prior=false){
 const els={},requests=[],writes=[];
 class E{constructor(){this.value='';this.children=[];this.events={};this.textContent=''}addEventListener(k,f){(this.events[k]??=[]).push(f)}fire(k){this['on'+k]?.();for(const f of this.events[k]||[])f()}setAttribute(){}removeAttribute(){}pause(){}load(){}append(...x){this.children.push(...x)}replaceChildren(){this.children=[]}}
 const fixture={caseId:'SYN-1',runId:run,revision:2,reviews:[{lineIndex:1,text:'prior',reason:'prior reason',decision:'pending'}],initial:{candidate:{source:{pdf_page_1based:1,printed_page:null},recognizer:{name:'synthetic'},text_lines:[{line_index:0,text:'synthetic',bbox:[0,0,10,10]},{line_index:1,text:'other',bbox:[0,10,10,20]}]}}};
 const location={search:''};const ctx=vm.createContext({document:{getElementById:id=>els[id]??(els[id]=new E()),createElement:()=>new E()},window:{addEventListener(){}},URL:{revokeObjectURL(){}},OcrPagePreview:{create:()=>({clear(){},select(){throw Error('preview forbidden')}})},location,history:{replaceState(){writes.push('unexpected')}},confirm:()=>true,fixture,fetch:(path,options)=>{assert.equal(options.method,'POST');assert.equal(path,'/api/v1/cases/SYN-1/image-reviews/'+run+'/reviews');return new Promise((resolve,reject)=>requests.push({path,options,resolve,reject}))}});
 vm.runInContext(script,ctx);location.search="?case=SYN-1&run="+run;vm.runInContext("state=fixture;context=fixture.caseId;el('case').value=context;el('run').value=state.runId;render()",ctx);
 const row=els.lines.children[0];row.children[2].value='unsaved correction';row.children[2].fire('input');row.children[4].value='synthetic reason';row.children[4].fire('input');
 if(prior)vm.runInContext("rememberUnknownSave('prior unrelated unknown')",ctx);
 return {els,requests,writes,location,read:s=>vm.runInContext(s,ctx),save:()=>row.children[5].onclick()};
}
function respond(s,status,body){s.requests[0].resolve({status,ok:status>=200&&status<300,json:async()=>body})}

function edit(s,index,value,line=0){const input=s.els.lines.children[line].children[index];input.value=value;input.fire('input');}
function result(s){const d=JSON.parse(s.read('JSON.stringify(state)'));return {...d,revision:3,reviews:[...d.reviews,JSON.parse(s.requests[0].options.body)]};}
for(const kind of ['text','reason','decision','away-back','other-line'])test('matching submitted response preserves subsequent '+kind,async()=>{
 const s=setup(),p=s.save(),d=result(s);let index=2,value='new draft',line=0;
 if(kind==='reason'){index=4;value='new reason'}if(kind==='decision'){index=3;value='unreadable'}if(kind==='other-line')line=1;
 edit(s,index,value,line);if(kind==='away-back'){value='unsaved correction';edit(s,index,value)}
 respond(s,200,d);await p;
 assert.equal(s.read('state.revision'),3);assert.equal(s.read('unknownSaves.size'),0);assert.equal(s.read('dirty'),true);
 assert.equal(s.els.lines.children[line].children[index].value,value);assert.equal(s.read('state.reviews.at(-1).text'),'unsaved correction');
 assert.equal(s.read('dirtyLines.has('+line+')'),true);if(line===1)assert.equal(s.read('dirtyLines.has(0)'),false);
 assert.equal(s.writes.length,0);assert.equal(s.location.search,'?case=SYN-1&run='+run);assert.equal(s.requests.length,1);
 assert.match(s.els.status.textContent,/上次确认保存修订 3/);
});
for(const kind of ['text','reason','decision','lineIndex','revision','runId','caseId','initial','history','missing-history','live-text'])test('mismatch stays unknown: '+kind,async()=>{
 const s=setup(),p=s.save(),d=result(s);edit(s,2,'new draft');
 if(['text','reason','decision','lineIndex'].includes(kind))d.reviews.at(-1)[kind]=kind==='lineIndex'?1:'wrong';
 else if(kind==='live-text')d.reviews.at(-1).text='new draft';
 else if(kind==='initial')d.initial.candidate.source.pdf_page_1based=2;
 else if(kind==='history')d.reviews[0].text='changed';
 else if(kind==='missing-history')d.reviews.shift();
 else d[kind]=kind==='revision'?4:'OTHER';
 respond(s,200,d);await p;assert.equal(s.read('state.revision'),2);assert.equal(s.read('unknownSaves.size'),1);assert.equal(s.els.lines.children[0].children[2].value,'new draft');assert.equal(s.writes.length,0);
});
for(const kind of ['lost','conflict','different-state','case','run'])test('failure or stale context retained: '+kind,async()=>{
 const s=setup(true),p=s.save(),d=result(s);edit(s,2,'new draft');
 if(kind==='different-state')s.read('state={...state,revision:9}');
 if(kind==='case'||kind==='run'){s.els[kind].value='OTHER';s.els[kind].fire('input')}
 s.els.status.textContent='current target';
 if(kind==='lost')s.requests[0].reject(Error('synthetic lost'));else respond(s,kind==='conflict'?412:200,kind==='conflict'?{code,message:'stale'}:d);
 await p;assert.equal(s.read('state.revision'),kind==='different-state'?9:2);assert.equal(s.read('unknownSaves.size'),kind==='conflict'?1:2);assert.equal(s.els.lines.children[0].children[2].value,'new draft');assert.equal(s.writes.length,0);
 if(kind==='conflict')assert.match(s.els.status.textContent,/本次未保存/);
 if(['case','run','different-state'].includes(kind))assert.equal(s.els.status.textContent,'current target');
});
test('single flight, previous unknown retained on confirmed submission',async()=>{const s=setup(true),p=s.save();await s.save();assert.equal(s.requests.length,1);const d=result(s);edit(s,2,'new draft');respond(s,200,d);await p;assert.equal(s.read('state.revision'),3);assert.equal(s.read('unknownSaves.size'),1);assert.equal(s.read('dirty'),true);assert.equal(s.writes.length,0)});
