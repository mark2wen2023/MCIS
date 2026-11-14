import { ApiError,casePath,getRole,getOperator } from '../api'
import { caseIdentity } from '../cases/identity'
import { MAX_FILE_BYTES } from './model'
export interface Download {bytes:ArrayBuffer;sha:string|null}
export async function intakeRequest(caseId:string,who:string,path:string,signal:AbortSignal,body?:unknown,raw=false):Promise<unknown>{
  if(caseIdentity()!==who)throw Error('身份已变化')
  if(signal.aborted)throw new DOMException('Request cancelled before dispatch','AbortError')
  const headers:Record<string,string>={'X-MCIS-Role':getRole(),'X-MCIS-Operator':encodeURIComponent(getOperator())}
  if(body!==undefined)headers['Content-Type']='application/json'
  // Once dispatched, a confirmed commit is not cancelled by UI read-controller reset.
  // Generation guards still suppress late UI results. This is not a delivery guarantee
  // across browser termination/network loss; do not use keepalive for an 8 MiB file.
  const requestSignal=path==='/evidence-intakes:commit'&&body!==undefined?undefined:signal
  const r=await fetch('/api/v1'+casePath(path,caseId),{cache:'no-store',method:body===undefined?'GET':'POST',headers,signal:requestSignal,body:body===undefined?undefined:JSON.stringify(body)})
  if(!r.ok){let code='EVIDENCE_INTAKE';try{const data=await r.json();if(typeof data.code==='string')code=data.code}catch{/* Do not display response internals. */}throw new ApiError(r.status,code,'登记请求未完成',null)}
  if(!raw)return r.json()
  const reader=r.body?.getReader();let total=0;const chunks:Uint8Array[]=[]
  if(reader){try{while(true){const part=await reader.read();if(part.done)break;total+=part.value.byteLength;if(total>MAX_FILE_BYTES){await reader.cancel();throw Error('Download exceeds budget')}chunks.push(part.value)}}finally{reader.releaseLock()}}
  const joined=new Uint8Array(total);let at=0;for(const chunk of chunks){joined.set(chunk,at);at+=chunk.byteLength}
  return {bytes:joined.buffer,sha:r.headers.get('X-Sha256')}
}
export function intakeError(e:unknown):string {
  if(e instanceof ApiError){if(e.status===409&&e.code==='ARCHIVE_HISTORY_ONLY')return '此登记属于只读恢复历史，不是当前请求成功回执，不能重放。可在明确历史状态后单独调阅历史原件。';if(e.status===409&&e.code==='ARCHIVE_HISTORY_INTEGRITY')return '历史原件完整性或关联无法核验，已停止；不会自动修复。';if(e.status===403)return '当前身份或案件策略不允许访问受限登记原件。';if(e.status===404)return '未找到案件或本片登记回执；旧证据不会自动迁移为本片登记。';if(e.status===409)return '登记记录、原件完整性或请求绑定不一致，已停止操作；不会覆盖或自动修复。';if(e.status===413)return '超过本片 8 MiB 原件 / 12 MiB 请求工程上限，不代表证据无效。';if([400,422].includes(e.status))return '输入被拒绝。请核对文件名、字段限额及已知 UTC 整秒提取时间；未自动重试。'}
  return '请求失败或响应无法核对。请核查服务与登记记录。'
}

// Only exact errors known to occur before registration in this endpoint qualify.
// A rejection of a later attempt never resolves an earlier unknown outcome.
const BEFORE_REGISTRATION:Record<string,number>={
  INTAKE_FIELDS:422,INTAKE_METADATA:422,INTAKE_CONFIRM:422,INTAKE_BASE64:422,
  INTAKE_JSON:422,INTAKE_OPERATOR:422,CASE_ID:422,CONTENT_TYPE:415,
  INTAKE_FILE_LIMIT:413,INTAKE_REQUEST_LIMIT:413,INTAKE_STALE:409,
  FORBIDDEN:403,READ_ONLY:403,CASE_NOT_FOUND:404,
}
export function commitFailure(e:unknown,previouslyUncertain:boolean):{locked:boolean;message:string}{
  if(!previouslyUncertain&&e instanceof ApiError&&BEFORE_REGISTRATION[e.code]===e.status){
    return {locked:false,message:'本次请求在登记前被拒绝，可核对输入或权限后重新预览；这不证明同内容没有历史登记。 '+intakeError(e)}
  }
  if(e instanceof ApiError&&e.status===409){
    return {locked:true,message:'登记存在冲突或完整性待核查；不能认定未保存。原请求保持锁定，请只读核查回执、证据清单与保管链，不要另建重复登记或覆盖原件。 '+intakeError(e)}
  }
  return {locked:true,message:'登记结果未确认，服务器可能已经保存。原请求保持锁定，请只读核查；后续拒绝或未找到回执不能证明原请求未提交，不要重新提交或另建重复登记。 '+intakeError(e)}
}
