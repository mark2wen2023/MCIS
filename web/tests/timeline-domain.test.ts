import assert from 'node:assert/strict'
import { timelineDomain as domain } from '../src/timeline/domain'
let n=0
function test(label:string,f:()=>void){f();n++;console.log('ok '+label)}
test('real empty default',()=>assert.deepEqual(domain(false,[],[],[]),{min:0,max:60}))
test('fictional default preserved',()=>assert.deepEqual(domain(true,[],[],[]),{min:0,max:780}))
test('negative event',()=>assert.deepEqual(domain(false,[{timeSec:-1,endTimeSec:0}],[],[]),{min:-1,max:60}))
test('fractional negative preserved',()=>assert.equal(domain(false,[{timeSec:-1e-7}],[],[]).min,-1e-7))
test('positive event extends real',()=>assert.equal(domain(false,[{timeSec:90}],[],[]).max,90))
test('fictional event beyond780 included',()=>assert.equal(domain(true,[{timeSec:800}],[],[]).max,800))
test('negative CPA included',()=>assert.equal(domain(false,[],[{timeSec:-5}],[]).min,-5))
test('negative conflict included',()=>assert.equal(domain(false,[],[],[{timeSec:-10}]).min,-10))
test('conflict max included',()=>assert.equal(domain(false,[],[],[{timeSec:120}]).max,120))
test('valid duration extends max',()=>assert.equal(domain(false,[{timeSec:10,endTimeSec:600}],[],[]).max,600))
test('reverse duration not repaired',()=>assert.deepEqual(domain(false,[{timeSec:5,endTimeSec:-600}],[],[]),{min:0,max:60}))
test('null missing ends unchanged',()=>assert.deepEqual(domain(false,[{timeSec:0,endTimeSec:null},{timeSec:0}],[],[{}]),{min:0,max:60}))
test('nonfinite ignored',()=>assert.deepEqual(domain(false,[{timeSec:NaN},{timeSec:Infinity},{timeSec:0,endTimeSec:Infinity}], [{timeSec:-Infinity}], [{timeSec:NaN}]),{min:0,max:60}))
test('input untouched',()=>{const events=Object.freeze([Object.freeze({timeSec:-2,endTimeSec:0})]);domain(false,events,[],[]);assert.equal(events[0].timeSec,-2)})
test('large series avoids spread argument limit',()=>assert.equal(domain(false,[],Array.from({length:200000},(_,i)=>({timeSec:i-100000})),[]).min,-100000))
console.log(n+' cases passed')
