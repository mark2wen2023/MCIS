import {strict as assert} from 'node:assert'
import {parseContent,parseHistory} from '../../web/src/recommendationReview/model'
const c='SYNTHETIC',id='SR-2026-01',utc='2026-11-01T00:00:00Z'
const d={caseId:c,id,title:'Synthetic',addressee:'Synthetic recipient',status:'Draft',causeNodeIds:['N'],createdUtc:utc,dueUtc:utc,body:'<img src=x onerror=alert(1)>',responses:Array.from({length:12},(_,i)=>({party:'P'+i,text:'T'+i,utc}))}
assert.equal(parseContent(d,c,id).responses.length,12)
assert.equal(parseContent(d,c,id).body,d.body)
assert.throws(()=>parseContent({...d,responses:[...d.responses,{party:'BAD',text:42,utc}]},c,id))
for(const patch of [{caseId:'OTHER'},{id:'SR-2026-99'},{createdUtc:'2026-02-29T00:00:00Z'},{dueUtc:'2026-11-31T00:00:00Z'},{responses:null},{body:null}])assert.throws(()=>parseContent({...d,...patch},c,id))
assert.equal(parseContent({...d,body:'',responses:[]},c,id).body,'')
const e={caseId:c,entityId:id,entityType:'recommendation',category:'SafetyRec',seq:1,utc,operator:'op',action:'safetyrec.update',command:'cmd',before:'before',after:'after',line:'NEVER_RAW',snapshotRef:'NEVER_REF'}
assert(!JSON.stringify(parseHistory([e],c,id)).includes('NEVER'))
for(const patch of [{seq:0},{seq:NaN},{caseId:'OTHER'},{entityId:'SR-2026-99'},{entityType:'report'},{category:'Consultation'},{before:{}},{operator:5}])assert.throws(()=>parseHistory([e,{...e,seq:2,...patch}],c,id))
assert.throws(()=>parseHistory([e,e],c,id))
assert.deepEqual(parseHistory([{...e,seq:2},e],c,id).map(e=>e.seq),[1,2])
console.log('W74 independent projection: all replies validated, invalid whole-batch rejected, empty semantics, case/id/history binding, safe projection passed')
