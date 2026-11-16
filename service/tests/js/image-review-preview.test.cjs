// Synthetic decoder/canvas operations: NOT browser rendering or real image decoding.
const test=require('node:test'),assert=require('node:assert/strict');
const {pngSize,rectangle,create}=require('../../mcis_service/image_review/preview.js');
const expected={width:100,height:200};
function png(w=100,h=200){const b=new Uint8Array(33);b.set([137,80,78,71,13,10,26,10]);const v=new DataView(b.buffer);v.setUint32(8,13);b.set([73,72,68,82],12);v.setUint32(16,w);v.setUint32(20,h);return b.buffer;}
function harness(decode=async()=>({width:100,height:200,close(){}})){
 const ops=[],ctx={clearRect(...a){ops.push(['clear',...a]);},drawImage(...a){ops.push(['draw',...a.slice(1)]);},strokeRect(...a){ops.push(['box',...a]);}};
 const page={width:1,height:1,getContext:()=>ctx},crop={...page},message={textContent:''};return {controller:create({page,crop,message,decode}),page,crop,message,ops};
}
test('PNG original dimensions',()=>assert.deepEqual(pngSize(png(),expected),expected));
test('unsupported format, mismatched dimensions, oversized image',()=>{assert.throws(()=>pngSize(new Uint8Array(33),expected));assert.throws(()=>pngSize(png(),{width:200,height:100}));assert.throws(()=>pngSize(png(8192,8192),{width:8192,height:8192}));});
test('fractional box coordinates and ordinary bounds',()=>{assert.deepEqual(rectangle([.5,2,20,30],expected),{x:.5,y:2,width:19.5,height:28});assert.throws(()=>rectangle([0,0,101,20],expected));});
test('one read; selection draws box and context crop',async()=>{const h=harness();let reads=0;await h.controller.load(async()=>{reads++;return png();},expected);h.controller.select(7,[5,10,25,40]);assert.equal(reads,1);assert.deepEqual(h.ops.find(x=>x[0]==='box'),['box',5,10,20,30]);assert.equal(h.crop.width,44);assert.equal(h.crop.height,54);assert.match(h.message.textContent,/行 7/);assert.match(h.message.textContent,/未自动核验/);});
test('decode failure clears; no automatic retry',async()=>{const h=harness(async()=>{throw Error('decode failed');});let reads=0;await assert.rejects(h.controller.load(async()=>{reads++;return png();},expected));assert.equal(reads,1);assert.equal(h.page.width,1);assert.match(h.message.textContent,/未显示页图/);});
test('clear during read prevents late decode/draw',async()=>{let resolve,decoded=0;const h=harness(async()=>{decoded++;return {...expected,close(){}};});const t=h.controller.load(()=>new Promise(r=>resolve=r),expected);h.controller.clear();resolve(png());assert.equal(await t,false);assert.equal(decoded,0);assert.equal(h.ops.length,0);});
test('clear during decode closes late bitmap',async()=>{let resolve,closed=0;const h=harness(()=>new Promise(r=>resolve=r));const t=h.controller.load(async()=>png(),expected);await Promise.resolve();await Promise.resolve();h.controller.clear();resolve({...expected,close(){closed++;}});assert.equal(await t,false);assert.equal(closed,1);assert.equal(h.ops.length,0);});
test('clear releases pixels and selection requires reload',async()=>{let closed=0;const h=harness(async()=>({...expected,close(){closed++;}}));await h.controller.load(async()=>png(),expected);h.controller.clear();assert.equal(closed,1);assert.throws(()=>h.controller.select(0,[0,0,20,20]));});
test('decoder dimensions must match header',async()=>{let closed=0;const h=harness(async()=>({width:200,height:100,close(){closed++;}}));await assert.rejects(h.controller.load(async()=>png(),expected));assert.equal(closed,1);assert.equal(h.page.width,1);});
test('selection redraws original without accumulating marks',async()=>{const h=harness();await h.controller.load(async()=>png(),expected);h.controller.select(0,[0,0,20,20]);h.controller.select(1,[20,20,40,40]);assert.equal(h.ops.filter(x=>x[0]==='clear').length,3);assert.deepEqual(h.ops.filter(x=>x[0]==='box').at(-1),['box',20,20,20,20]);});
