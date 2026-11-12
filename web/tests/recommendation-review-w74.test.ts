import assert from 'node:assert/strict'
import {parseContent,parseHistory} from '../src/recommendationReview/model'
const base={id:'SR-2026-01',caseId:'SYNTHETIC',title:'建议',body:'<script>not HTML</script>\n原文',addressee:'虚构单位',causeNodeIds:['SYNTHETIC-N1'],dueUtc:'2026-12-01T00:00:00Z',createdUtc:'2026-11-01T00:00:00Z',status:'Draft',responses:[{party:'合成回复方',text:'first',utc:'2026-11-01T01:00:00Z'},{party:'合成回复方',text:'second',utc:'2026-11-02T00:00:00Z'}]}
const c=parseContent({...base,privateExtra:'not projected'},base.caseId,base.id)
assert.equal(c.body,base.body);assert.equal(c.responses.length,2);assert.ok(!('privateExtra' in c));assert.equal(c.updatedUtc,null)
for(const changes of [{id:'SR-2026-99'},{caseId:'OTHER'},{body:42},{status:'toString'},{responses:[null]},{responses:[{party:'p',text:'x',utc:'bad'}]},{responses:42},{updatedUtc:'bad'},{updatedUtc:'2026-02-31T00:00:00Z'},{causeNodeIds:[]},{title:''}])assert.throws(()=>parseContent({...base,...changes},base.caseId,base.id))
assert.equal(parseContent({...base,body:undefined,responses:undefined},base.caseId,base.id).responses.length,0)
const event={seq:1,caseId:base.caseId,entityId:base.id,entityType:'recommendation',category:'SafetyRec',utc:base.createdUtc,operator:'合成操作员',action:'safetyrec.create',command:'创建',before:'',after:'摘要',line:'RAW SECRET',snapshotRef:'SECRET'}
assert.equal(parseHistory([event],base.caseId,base.id)[0].after,'摘要');assert.ok(!('line' in parseHistory([event],base.caseId,base.id)[0]));assert.ok(!('snapshotRef' in parseHistory([event],base.caseId,base.id)[0]))
for(const changes of [{caseId:'OTHER'},{entityId:'SR-2026-99'},{entityType:'report'},{category:'Report'},{seq:0},{seq:1.5},{after:null},{utc:'bad'}])assert.throws(()=>parseHistory([{...event,...changes}],base.caseId,base.id))
assert.throws(()=>parseHistory([event,event],base.caseId,base.id));assert.throws(()=>parseHistory(Array.from({length:201},(_,i)=>({...event,seq:i+1})),base.caseId,base.id))
assert.deepEqual(parseHistory([],base.caseId,base.id),[])
console.log('W7.4 content/history binding, optional legacy empty fields, whole-batch rejection, projection and plain-text values passed')
