import assert from 'node:assert/strict'
import { timelineDomain as domain } from '../src/timeline/domain'
let count=0
function test(name:string,fn:()=>void){fn();count++;console.log('ok '+name)}
test('all source extrema combine without truncation',()=>assert.deepEqual(domain(false,[{timeSec:-100,endTimeSec:1000}],[{timeSec:-300},{timeSec:900}],[{timeSec:-200},{timeSec:1100}]),{min:-300,max:1100}))
test('valid negative duration preserves origin and minimum',()=>assert.deepEqual(domain(true,[{timeSec:-200,endTimeSec:-100}],[],[]),{min:-200,max:780}))
test('invalid start cannot lend validity to its finite end',()=>assert.deepEqual(domain(false,[{timeSec:NaN,endTimeSec:1000},{timeSec:-Infinity,endTimeSec:2000}],[],[]),{min:0,max:60}))
test('nonfinite values in each stream and both interval directions ignored',()=>assert.deepEqual(domain(false,[{timeSec:Infinity,endTimeSec:Infinity},{timeSec:1,endTimeSec:-Infinity}], [{timeSec:NaN},{timeSec:Infinity}], [{timeSec:Infinity},{timeSec:-Infinity}]),{min:0,max:60}))
test('numeric strings and booleans not coerced',()=>{
 const events=[{timeSec:'-100',endTimeSec:1000},{timeSec:false,endTimeSec:2000},{timeSec:1,endTimeSec:'3000'}] as unknown as {timeSec:number;endTimeSec:number}[]
 assert.deepEqual(domain(false,events,[{timeSec:'4000'}] as unknown as {timeSec:number}[],[{timeSec:true}] as unknown as {timeSec:number}[]),{min:0,max:60})
})
test('all arrays and nested records remain unchanged and frozen',()=>{
 const events=Object.freeze([Object.freeze({timeSec:-10,endTimeSec:100})])
 const cpa=Object.freeze([Object.freeze({timeSec:-20})])
 const conflicts=Object.freeze([Object.freeze({timeSec:200})])
 const before=JSON.stringify([events,cpa,conflicts])
 assert.deepEqual(domain(false,events,cpa,conflicts),{min:-20,max:200})
 assert.equal(JSON.stringify([events,cpa,conflicts]),before)
})
test('large event and conflict streams avoid argument limit and preserve extrema',()=>{
 const events=Array.from({length:150000},(_,i)=>({timeSec:-i,endTimeSec:i}))
 const conflicts=Array.from({length:150000},(_,i)=>({timeSec:i+150000}))
 assert.deepEqual(domain(false,events,[],conflicts),{min:-149999,max:299999})
})
test('fractional boundaries are not rounded to fixed ticks',()=>assert.deepEqual(domain(false,[{timeSec:-0.125,endTimeSec:60.125}],[],[]),{min:-0.125,max:60.125}))
console.log(`${count} independent cases passed`)
