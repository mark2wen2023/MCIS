// Actual inline json/fetch wrapper; only hand-built response and DOM, no network.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const pages=JSON.parse(fs.readFileSync(0,'utf8'));
(async()=>{for(const [mode,html] of Object.entries(pages)){
 const image=mode.startsWith('image'),els={},requests=[],writes=[];
 class E{constructor(){this.value='';this.children=[];this.textContent=''}addEventListener(){}setAttribute(){}removeAttribute(){}pause(){}load(){}append(...v){this.children.push(...v)}replaceChildren(){this.children=[]}}
 const ctx=vm.createContext({document:{getElementById:id=>els[id]??(els[id]=new E()),createElement:()=>new E()},window:{addEventListener(){}},location:{search:''},history:{replaceState(){writes.push(1)}},URL:{revokeObjectURL(){}},confirm:()=>true,OcrPagePreview:{create:()=>({clear(){},select(){throw Error('preview forbidden')}})},fetch:async(path,options)=>{requests.push({path,options});return {ok:false,status:409,json:async()=>({code:image?'OCR_SOURCE_UNAVAILABLE':'AUDIO_SOURCE_UNAVAILABLE',message:'synthetic wrong request digest'})}}});
 vm.runInContext(html.split('<script>')[1].split('</script>')[0],ctx);
 assert.equal(requests.length,0);els.case.value='SYN-RECEIPT';els.ack.checked=true;
 const fields=image?['pdf','image','candidate','raw']:['audio-digest','draft-digest'];
 fields.forEach((id,i)=>els[id].value=String(i+1).repeat(64));
 await els[image?'create':'attach'].onclick();
 assert.equal(requests.length,1);assert.equal(requests[0].path,'/api/v1/cases/SYN-RECEIPT/'+(image?'image-reviews':'audio-reviews'));assert.equal(requests[0].options.method,'POST');
 const expected=image?{bindings:Object.fromEntries(fields.map(id=>[id,els[id].value])),acknowledgeArchiveBlocked:true}:{audioReceipt:els['audio-digest'].value,draftReceipt:els['draft-digest'].value,acknowledgeArchiveBlocked:true};
 assert.deepEqual(JSON.parse(requests[0].options.body),expected);
 assert.equal(vm.runInContext('state',ctx),null);assert.equal(els.run.value,'');assert.equal(writes.length,0);assert.match(els.status.textContent,/synthetic wrong request digest/);
 fields.forEach((id,i)=>assert.equal(els[id].value,String(i+1).repeat(64)));
 console.log(mode+': mapping, synthetic failed import not accepted, inputs/URL retained PASS');
}})().catch(e=>{console.error(e);process.exitCode=1});
