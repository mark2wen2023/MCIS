'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict');
const {create}=require(process.argv[2]);
async function main(){
 const input=JSON.parse(fs.readFileSync(0,'utf8'));
 const overlays=[],pageDraws=[],cropDraws=[];
 const page={width:1,height:1,getContext:()=>({clearRect(){},drawImage(...a){pageDraws.push(a);},strokeRect(...a){overlays.push(a);}})};
 const crop={width:1,height:1,getContext:()=>({clearRect(){},drawImage(...a){cropDraws.push(a);}})};
 const bitmap={width:256,height:160,close(){}};
 const controls={read:{disabled:false},review:{disabled:false}};
 const view=create({page,crop,message:{textContent:''},decode:async blob=>{
   const b=Buffer.from(await blob.arrayBuffer());assert.equal(b.readUInt32BE(16),256);assert.equal(b.readUInt32BE(20),160);return bitmap;
 },controls:()=>({originalRead:[controls.read],ocrReview:[controls.review]})});
 assert.equal(await view.loadDerived(Buffer.from(input.pngBase64,'base64'),input.description),true);
 view.select(0,[40,32,92,68]);
 assert.deepEqual(overlays,[[40,32,52,36]]);
 assert.equal(pageDraws.length,2);for(const draw of pageDraws)assert.deepEqual(draw,[bitmap,0,0]);
 assert.deepEqual(cropDraws,[[bitmap,28,20,76,60,0,0,76,60]]);
 assert.equal(crop.width,76);assert.equal(crop.height,60);
 assert.equal(controls.read.disabled,true);assert.equal(controls.review.disabled,true);
 assert.throws(()=>view.assertOriginalAction());
 console.log(JSON.stringify({overlay:[40,32,52,36],source:[28,20,76,60],padding:12,browser:false}));
}
main().catch(()=>{console.error('geometry assertion failed');process.exitCode=1;});
