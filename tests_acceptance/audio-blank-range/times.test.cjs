// Only the actual page's local pure times() body is executed, with handmade values.
// No page initialization, Save, DOM, fetch, backend or media.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync('service/mcis_service/audio_review/review.html','utf8');
const matches=html.match(/^function times\(\)\{[^\n]+\}$/gm);
assert.equal(matches?.length,1,'extract exactly the existing single-line parser, fail if its shape changes');
function parse(start,end){return vm.runInNewContext(matches[0]+';times()', {start:{value:start},end:{value:end},state:{initial:{audio:{sampleRateHz:8000,frames:8000}}}});}
for(const blank of [' ','\t','\n','\u00a0','\u3000'])test('nonempty whitespace is not a time '+JSON.stringify(blank),()=>{
 assert.throws(()=>parse(blank,'500'),/只有空白/);
 assert.throws(()=>parse('0',blank),/只有空白/);
 assert.throws(()=>parse(blank,blank),/只有空白/);
});
for(const [a,b,want] of [['','',[null,null]],['0','500',[0,500]],[' 0 ','500',[0,500]],['100','1000',[100,1000]]])test('existing valid range '+JSON.stringify([a,b]),()=>{assert.deepEqual(Array.from(parse(a,b)),want);});
for(const [a,b] of [['','500'],['0',''],['500','100'],['-1','500'],['0','1001'],['1.5','500']])test('existing invalid range '+JSON.stringify([a,b]),()=>{assert.throws(()=>parse(a,b),/有效范围/);});
