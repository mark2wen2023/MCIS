import {strict as assert} from 'node:assert'
import {reviewedSuggestion} from '../src/knowledge/sourceReview'
import {sample} from '../src/knowledge/model'
import {PROFILE,type Suggestion} from '../src/knowledge/suggestionModel'
const input={kind:sample.kind,source:structuredClone(sample.source)}
const r:Suggestion={profile:PROFILE,provider:'template-stub-v1',modelUsed:false,persisted:false,reviewRequired:true,inputDigest:'a'.repeat(64),content:{...structuredClone(sample),body:sample.source.excerpt,tags:['合成待审']},warnings:['not model']}
let n=0
for (const key of ['title','locator','excerpt','rightsNote'] as const) {assert.equal(reviewedSuggestion(r,{...input,source:{...input.source,[key]:'different'}},r.inputDigest),null);n++}
assert.equal(reviewedSuggestion(r,{...input,kind:'Case'},r.inputDigest),null);n++
assert.equal(reviewedSuggestion({...r,inputDigest:'b'.repeat(64)},input,r.inputDigest),null);n++
const p={...input,source:{...input.source,type:'Public' as const,url:'https://example.test/report'}}
const pr={...r,content:{...r.content,source:p.source,tags:['公开待审']}}
assert.deepEqual(reviewedSuggestion(pr,p,pr.inputDigest),pr.content);n++
const copy=reviewedSuggestion(r,input,r.inputDigest)!; copy.tags.push('bad');assert.deepEqual(r.content.tags,['合成待审']);n++
assert.equal(reviewedSuggestion(r,input,null),null);n++
console.log(n+' independent current-source/digest/public/clone checks passed')
