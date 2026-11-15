import assert from 'node:assert/strict'
import { appendBlankSource, blankSource, previewPayload } from '../src/align/model'
import type { PreviewSource } from '../src/align/types'
const ready=(sourceId:string):PreviewSource=>({sourceId,text:'utc,cog\n2026-01-01T00:00:00Z,45',csvMapping:{timeColumn:'utc',columns:[{column:'cog',kind:'CourseOverGround'}]}})
// Synthetic CSV declarations only; no actual alignment, identity inference or model.
const original=[ready('SOURCE-1'),ready('SOURCE-3')]
const serialized=JSON.stringify(original)
const result=appendBlankSource(original)
assert.deepEqual(result.map(s=>s.sourceId),['SOURCE-1','SOURCE-3','SOURCE-2'])
assert.equal(result[0],original[0]);assert.equal(result[1],original[1])
assert.equal(JSON.stringify(original),serialized)
assert.deepEqual(result[2],blankSource(2))
assert.throws(()=>previewPayload(result),/文本须非空/) // new source is not fabricated CSV
const filled=[...result.slice(0,2),ready(result[2]!.sourceId)]
assert.deepEqual(previewPayload(filled).sources.map(s=>s.sourceId),['SOURCE-1','SOURCE-3','SOURCE-2'])
for(const removed of [0,1,2,3]){
 const old=[1,2,3,4].map(n=>ready(`SOURCE-${n}`)).filter((_,i)=>i!==removed)
 const next=appendBlankSource(old)
 assert.equal(next.length,4);assert.equal(new Set(next.map(s=>s.sourceId)).size,4)
 for(let i=0;i<old.length;i++)assert.equal(next[i],old[i])
}
const custom=[ready('manual-source'),ready('SOURCE-1'),ready('source-2')]
assert.equal(appendBlankSource(custom)[3]!.sourceId,'SOURCE-2') // case-sensitive server contract
assert.deepEqual(appendBlankSource([]),[blankSource(1)])
let sequence:PreviewSource[]=[]
for(let i=0;i<12;i++)sequence=appendBlankSource(sequence)
assert.equal(sequence.length,4)
assert.equal(appendBlankSource(sequence),sequence)
const duplicates=[ready('manual-source'),ready('manual-source')]
assert.throws(()=>previewPayload([...appendBlankSource(duplicates).slice(0,2)]),/不能重复/) // never silently repair user claims
console.log('CSV source numbering regression passed: remove/add, reserved names, bounds, preserved declarations; no browser/core invocation')
