// Real api.ts + controller against loopback FastAPI. Synthetic registry only.
import assert from 'node:assert/strict'
import {once} from 'node:events'
import {ObservationEditing} from '../src/timeline/observationEditing'
import {editableRows, type VersionedConflict} from '../src/timeline/conflictEditing'
async function main(){
  const base=process.argv[2], changed=process.argv[3]==='changed'
  assert.match(base,/^http:\/\/127\.0\.0\.1:\d+$/)
  Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null,setItem:()=>{}}})
  const nativeFetch=globalThis.fetch
  const requests:{path:string;status:number}[]=[]
  globalThis.fetch=async(input,init)=>{
    assert.equal(typeof input,'string');assert.ok(String(input).startsWith('/api/v1/cases/CASE-INTAKE/'))
    const response=await nativeFetch(base+input,init)
    requests.push({path:String(input),status:response.status});return response
  }
  const {api,setIdentity}=await import('../src/api')
  setIdentity('LeadInvestigator','Synthetic Recorder')
  const root='/cases/CASE-INTAKE/conflicts'
  const rows=editableRows(await api.get<VersionedConflict[]>(root+':editable'))
  let saved=0
  const editor=new ObservationEditing('CASE-INTAKE',rows[0],api,()=>{saved++})
  await editor.check();assert.equal(editor.state.allowed,true)
  editor.edit('a','Synthetic edited text 中文 12:34')
  await editor.issue();assert.ok(editor.state.receipt,editor.state.error)
  const receiptId=editor.state.receipt.receiptId
  assert.equal(editor.state.receipt.sources['EV-A'].sha256,'a'.repeat(64))
  assert.equal(editor.state.receipt.bytesVerified,false)
  // Parent changes registry only after receipt was actually returned by HTTP.
  process.stdout.write('RECEIPT_READY\n')
  process.stdin.resume();await once(process.stdin,'data');process.stdin.pause()
  const beforeSubmit=requests.length
  await editor.submit()
  assert.equal(requests.length,beforeSubmit+1) // no automatic retry
  assert.equal(editor.state.draft.a.valueText,'Synthetic edited text 中文 12:34')
  assert.equal(editor.state.receipt,null)
  assert.equal(saved,changed?0:1)
  assert.equal(requests.at(-1)?.status,changed?412:201)
  if(changed){assert.ok(editor.state.error.includes('服务端拒绝'));assert.ok(!editor.state.message.includes('已保存'))}
  else {assert.ok(editor.state.message.includes('已保存'));assert.equal(editor.state.error,'')}
  const history=await api.get<any>(root+'/C-01/revisions')
  assert.equal(history.revisions.length,changed?1:2)
  if(!changed){
    const last=history.revisions.at(-1)
    assert.equal(last.sourceReceiptId,receiptId)
    assert.equal(last.after.a.valueText,'Synthetic edited text 中文 12:34')
    assert.equal(last.afterSources.a.bytesVerified,false)
    assert.deepEqual(last.before,history.revisions[0].after)
  }
  console.log(JSON.stringify({result:changed?'source-change-refused':'saved-with-history',receiptId,requests:requests.length}))
}
main().catch(error=>{console.error(error);process.exitCode=1})
