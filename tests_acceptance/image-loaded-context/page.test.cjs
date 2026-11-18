// Pure Node; json is an in-memory Promise seam. Real fetch/decode are forbidden.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync('service/mcis_service/image_review/review.html','utf8').split('<script>')[1].split('</script>')[0];
const record=id=>({caseId:'SYNTHETIC',runId:id,revision:0,reviews:[],initial:{candidate:{source:{pdf_page_1based:1,printed_page:null,pdf_sha256:'pdf-'+id,image_sha256:'image-'+id},recognizer:{name:'synthetic'},text_lines:[{line_index:0,text:'text '+id,bbox:[0,0,10,10]}]}}});
function setup(){
 const requests=[];let fetches=0,decodes=0;
 class Element{constructor(){this.children=[];this.events={};this.value='';this.textContent=''}addEventListener(n,f){(this.events[n]??=[]).push(f)}fire(n){this['on'+n]?.();for(const f of this.events[n]||[])f()}setAttribute(){}append(...v){this.children.push(...v)}replaceChildren(){this.children=[]}}
 const elements={},ctx=vm.createContext({document:{getElementById:id=>elements[id]??(elements[id]=new Element()),createElement:()=>new Element()},window:{addEventListener(){}},confirm:()=>true,OcrPagePreview:{create:()=>({clear(){},load(){throw Error('preview forbidden')},select(){throw Error('preview forbidden')}})},createImageBitmap(){decodes++;throw Error('decode forbidden')},fetch(){fetches++;throw Error('fetch forbidden')},memoryRequest:path=>new Promise((resolve,reject)=>requests.push({path,resolve,reject})),fixture:record('OCR-A')});
 vm.runInContext(script,ctx);vm.runInContext("json=memoryRequest;state=fixture;context=fixture.caseId;el('case').value=context;el('run').value=state.runId;el('task').value='TASK';render()",ctx);
 const input=elements.lines.children[0].children[2];input.value='unsaved A';input.fire('input');
 return {elements,requests,read:s=>vm.runInContext(s,ctx),counts:()=>({fetches,decodes})};
}
function retained(s,target){const e=s.elements;assert.match(e.source.children[0].textContent,/pdf-OCR-A/);assert.equal(e.lines.children[0].children[2].value,'unsaved A');assert.equal(s.read('dirty'),true);const notice=e['loaded-context']?.textContent??'';assert.match(notice,/已载入.*OCR-A/);assert.ok(notice.includes(target));assert.match(notice,/未载入/);assert.match(notice,/来源.*草稿.*下载.*已载入运行/);assert.deepEqual(s.counts(),{fetches:0,decodes:0})}
async function selectB(s){const work=s.elements['check-task'].onclick();assert.equal(s.requests.length,1);s.requests[0].resolve({caseId:'SYNTHETIC',taskId:'TASK',status:'succeeded',runId:'OCR-B'});await work;assert.equal(s.elements.run.value,'OCR-B');}
for(const outcome of ['failure','success','late'])test(`task selects B: ${outcome} retains explicit source ownership`,async()=>{
 const s=setup();await selectB(s);retained(s,'OCR-B');const work=s.elements.load.onclick();assert.equal(s.requests.length,2);retained(s,'OCR-B');
 if(outcome==='late'){s.elements.run.value='OCR-C';s.elements.run.fire('input');retained(s,'OCR-C')}
 if(outcome==='failure')s.requests[1].reject(Error('synthetic read failure'));else s.requests[1].resolve(record('OCR-B'));await work;
 if(outcome==='success'){assert.match(s.elements['loaded-context'].textContent,/已载入.*OCR-B/);assert.doesNotMatch(s.elements['loaded-context'].textContent,/未载入/);assert.match(s.elements.source.children[0].textContent,/pdf-OCR-B/);assert.equal(s.elements.lines.children[0].children[2].value,'text OCR-B');assert.equal(s.read('dirty'),false)}else retained(s,outcome==='late'?'OCR-C':'OCR-B');
 assert.deepEqual(s.counts(),{fetches:0,decodes:0});
});
for(const field of ['case','run'])test(`manual ${field} change labels retained source and dirty draft`,()=>{const s=setup();s.elements[field].value='OTHER';s.elements[field].fire('input');retained(s,'OTHER');assert.equal(s.requests.length,0)});
