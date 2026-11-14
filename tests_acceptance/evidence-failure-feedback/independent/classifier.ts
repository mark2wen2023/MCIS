import assert from 'node:assert/strict'
Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null,setItem:()=>{}}})
async function run(){
 const {ApiError}=await import('../../../web/src/api')
 const {commitFailure}=await import('../../../web/src/evidenceIntake/api')
 const known:Record<string,number>={INTAKE_FIELDS:422,INTAKE_METADATA:422,INTAKE_CONFIRM:422,INTAKE_BASE64:422,INTAKE_JSON:422,INTAKE_OPERATOR:422,CASE_ID:422,CONTENT_TYPE:415,INTAKE_FILE_LIMIT:413,INTAKE_REQUEST_LIMIT:413,INTAKE_STALE:409,FORBIDDEN:403,READ_ONLY:403,CASE_NOT_FOUND:404}
 let checks=0
 for(const [code,status] of Object.entries(known)){
  assert.equal(commitFailure(new ApiError(status,code,'',null),false).locked,false);checks++
  assert.equal(commitFailure(new ApiError(status,code,'',null),true).locked,true);checks++
  assert.equal(commitFailure(new ApiError(500,code,'',null),false).locked,true);checks++
  assert.equal(commitFailure(new ApiError(status,code.toLowerCase(),'',null),false).locked,true);checks++
 }
 for(const code of ['INTAKE_INTEGRITY','INTAKE_BLOB_EXISTS','INTAKE_PATH','ARCHIVE_HISTORY_ONLY','ARCHIVE_HISTORY_INTEGRITY','UNKNOWN']){
  for(const previous of [false,true]){assert(commitFailure(new ApiError(409,code,'',null),previous).locked);checks++}
 }
 for(const error of [null,{},new Error('network'),new SyntaxError('bad receipt'),new ApiError(404,'INTAKE_NOT_FOUND','',null),new ApiError(500,'INTAKE_CLEANUP_FAILED','',null)]){
  assert(commitFailure(error,false).locked);assert(commitFailure(error,true).locked);checks+=2
 }
 console.log(`${checks} independent classifier assertions passed; synthetic error inputs only`)
}
void run()
