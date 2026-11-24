import assert from 'node:assert/strict'
import {sourceReviewInitial,sourceReviewReducer as transition} from '../src/hfacsDrafts/sourceReview'
// Same reducer used by the real Editor. No React effects/DOM or service writes.
let state=sourceReviewInitial('changed')
assert.deepEqual(state,{refreshed:false,acknowledged:false})
state=transition(state,{type:'loaded'})
state=transition(state,{type:'acknowledge',checked:true})
assert.deepEqual(state,{refreshed:true,acknowledged:true})
// A second refresh must revoke the first confirmation immediately.
const before=state
state=transition(state,{type:'refresh'})
assert.deepEqual(state,{refreshed:false,acknowledged:false})
assert.deepEqual(before,{refreshed:true,acknowledged:true})
// Failure dispatches no loaded event; a stale confirmation cannot restore it.
state=transition(state,{type:'acknowledge',checked:true})
assert.deepEqual(state,{refreshed:false,acknowledged:false})
state=transition(state,{type:'loaded'})
assert.deepEqual(state,{refreshed:true,acknowledged:false})
state=transition(state,{type:'acknowledge',checked:true})
assert.deepEqual(state,{refreshed:true,acknowledged:true})
state=transition(state,{type:'acknowledge',checked:false})
assert.deepEqual(state,{refreshed:true,acknowledged:false})
for(const status of ['none','unchanged'] as const){
 const initial=sourceReviewInitial(status)
 assert.deepEqual(initial,{refreshed:true,acknowledged:true})
 assert.deepEqual(transition(initial,{type:'refresh'}),{refreshed:false,acknowledged:false})
}
console.log('HFACS source refresh: second refresh/failure/retry/acknowledgement and legacy initial states passed (pure reducer)')
