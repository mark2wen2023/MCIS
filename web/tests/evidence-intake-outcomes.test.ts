import assert from 'node:assert/strict'
Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null,setItem:()=>{}}})
async function run(){
 const {ApiError}=await import('../src/api')
 const {commitFailure}=await import('../src/evidenceIntake/api')
 let checks=0
 for(const [status,code] of [[409,'INTAKE_INTEGRITY'],[409,'INTAKE_PATH'],[409,'INTAKE_EXISTS'],[409,'ARCHIVE_HISTORY_ONLY'],[500,'INTAKE_CLEANUP_FAILED'],[503,'DB_BUSY'],[403,'UNRECOGNIZED']] as const){
  const r=commitFailure(new ApiError(status,code,'',null),false);assert(r.locked);checks++
 }
 for(const [status,code] of [[422,'INTAKE_BASE64'],[409,'INTAKE_STALE'],[403,'FORBIDDEN'],[413,'INTAKE_FILE_LIMIT']] as const){
  const error=new ApiError(status,code,'',null)
  assert.equal(commitFailure(error,false).locked,false);assert.equal(commitFailure(error,true).locked,true);checks+=2
 }
 for(const error of [new TypeError('network'),new SyntaxError('bad receipt'),new ApiError(404,'INTAKE_NOT_FOUND','',null),new ApiError(500,'INTAKE_FIELDS','',null)]){assert(commitFailure(error,false).locked);checks++}
 console.log(`Evidence outcome classifier: ${checks} checks passed (synthetic error inputs)`)
}
void run()
