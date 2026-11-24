// Local stdin receiver of the pinned synthetic host, NOT an authority/provider.
'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {create}=require(process.argv[2]);
async function main(){
 const bytes=fs.readFileSync(0);assert(bytes.length<3*1024*1024);
 const input=JSON.parse(bytes);assert.equal(input.kind,'synthetic-local-derived-pages');assert.equal(input.frames.length,2);
 const ops=[],controls={read:{disabled:false},review:{disabled:false}},context={clearRect(){ops.push('clear');},drawImage(){ops.push('draw');},strokeRect(){ops.push('box');}};
 const page={width:1,height:1,getContext:()=>context},crop={...page},message={textContent:''};let closes=0;
 // Actual PNG/Pillow decoding already occurred in the trusted Python fixture.
 // This is the existing controller's test decoder/canvas boundary, not browser.
 const decode=async blob=>{const b=Buffer.from(await blob.arrayBuffer());assert.equal(b.toString('ascii',12,16),'IHDR');return {width:b.readUInt32BE(16),height:b.readUInt32BE(20),close(){closes++;}};};
 const view=create({page,crop,message,decode,controls:()=>({originalRead:[controls.read],ocrReview:[controls.review]})});
 let previous=null;
 for(const [i,frame] of input.frames.entries()){
  const data=Buffer.from(frame.pngBase64,'base64');assert.equal(frame.description.physicalPage,i+1);
  assert.equal(crypto.createHash('sha256').update(data).digest('hex'),frame.description.pageSha256);
  if(previous)assert.notEqual(previous,frame.description.pageSha256);previous=frame.description.pageSha256;
  assert.equal(await view.loadDerived(data,frame.description),true);
  assert.equal(view.inputKind,'pdf-derived-page');assert.equal(page.width,256);assert.equal(page.height,256);
  assert(message.textContent.includes('物理页 '+(i+1)));assert(message.textContent.includes(frame.description.pageSha256));
  assert.equal(controls.read.disabled,true);assert.equal(controls.review.disabled,true);assert.throws(()=>view.assertOriginalAction());
  view.select(i,[64,64,128,128]);assert(message.textContent.includes('声明区域 '+i));assert.equal(crop.width,88);assert.equal(crop.height,88);
 }
 assert.equal(closes,1);assert.equal(ops.filter(x=>x==='box').length,2);
 // Corrupt only in-memory transport, never the registered original or disk.
 const bad=Buffer.from(input.frames[1].pngBase64,'base64');bad[bad.length-1]^=1;
 const draws=ops.filter(x=>x==='draw').length;
 await assert.rejects(view.loadDerived(bad,input.frames[1].description),/摘要不符/);
 assert.equal(ops.filter(x=>x==='draw').length,draws);assert.equal(page.width,1);assert.equal(controls.read.disabled,true);
 assert.throws(()=>view.assertOriginalAction());view.clear();assert.equal(controls.read.disabled,false);assert.equal(controls.review.disabled,false);
 console.log(JSON.stringify({passed:true,derivedPages:2,rejectedDigest:1,blockedActions:true,canvasDecoder:'synthetic-spy',browser:false}));
}
main().catch(()=>{console.error('synthetic controller handoff failed');process.exitCode=1;});
