// Only real inline callbacks in synthetic DOM; memory json, no fetch/media/application.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
for(const kind of ['audio','image'])test(kind+' unknown survives editing, cancelled read and accepted read',async()=>{
 const script=fs.readFileSync('service/mcis_service/'+kind+'_review/review.html','utf8').split('<script>')[1].split('</script>')[0];
 class Element{constructor(){this.children=[];this.events={};this.value='';this.textContent=''}addEventListener(n,f){(this.events[n]??=[]).push(f)}fire(n){this['on'+n]?.();for(const f of this.events[n]||[])f()}setAttribute(){}removeAttribute(){}load(){}pause(){}append(...v){this.children.push(...v)}replaceChildren(){this.children=[]}}
 const elements={},requests=[],prompts=[];let accept=false,fetches=0;
 const fixture=kind==='audio'?{caseId:'SYNTHETIC',runId:'AR-A',revision:0,humanRevisions:[],initial:{audio:{frames:8000,sampleRateHz:8000},machineDraft:{transcript:{segments:[{id:'s1',text:'synthetic',startMs:0,endMs:500}],unlocatedSegments:[]}}}}:{caseId:'SYNTHETIC',runId:'OCR-A',revision:0,reviews:[],initial:{candidate:{source:{},recognizer:{},text_lines:[{line_index:0,text:'synthetic',bbox:[0,0,10,10]}]}}};
 const ctx=vm.createContext({document:{getElementById:id=>elements[id]??(elements[id]=new Element()),createElement:()=>new Element()},window:{addEventListener(){}},URL:{revokeObjectURL(){}},OcrPagePreview:{create:()=>({clear(){}})},confirm:m=>{prompts.push(m);return accept},fetch(){fetches++;throw Error('fetch forbidden')},memoryRequest:(path,body)=>new Promise((resolve,reject)=>requests.push({body,resolve,reject}))});
 vm.runInContext(script,ctx);ctx.fixture=fixture;vm.runInContext("json=memoryRequest;state=fixture;context=state.caseId;el('case').value=context;el('run').value=state.runId;render()",ctx);
 const row=()=>elements[kind==='audio'?'segments':'lines'].children[0],ti=kind==='audio'?1:2,ri=kind==='audio'?5:4,si=kind==='audio'?7:5;
 function edit(v){row().children[ti].value=v;row().children[ti].fire('input');row().children[ri].value='synthetic reason';row().children[ri].fire('input')}
 edit('submitted');const save=row().children[si].onclick();requests[0].reject(Error('synthetic communication'));await save;
 const guidance=()=>elements['save-unknown'].textContent;
 assert.match(guidance(),/先复制草稿并人工核对/);assert.match(guidance(),/再次保存可能追加修订/);assert.match(guidance(),new RegExp(fixture.runId));edit('later draft');const warning=guidance();
 await elements.load.onclick();assert.equal(requests.length,1);assert.equal(row().children[ti].value,'later draft');assert.equal(vm.runInContext('dirty',ctx),true);assert.match(prompts[0],/不能证明原请求结果/);assert.equal(guidance(),warning);
 accept=true;const read=elements.load.onclick();assert.equal(requests.length,2);assert.equal(requests[1].body,undefined);requests[1].resolve(JSON.parse(JSON.stringify(fixture)));await read;
 assert.equal(row().children[ti].value,'synthetic');assert.equal(vm.runInContext('dirty',ctx),false);assert.equal(guidance(),warning);assert.match(guidance(),/仅在当前页面内存/);assert.equal(fetches,0);
});
