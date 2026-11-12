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
  const r=await fetch('/api/v1'+casePath(path,caseId),{method:body===undefined?'GET':'POST',headers,signal:requestSignal,body:body===undefined?undefined:JSON.stringify(body)})
  if(!r.ok){let code='EVIDENCE_INTAKE';try{const data=await r.json();if(typeof data.code==='string')code=data.code}catch{/* Do not display response internals. */}throw new ApiError(r.status,code,'登记请求未完成',null)}
  if(!raw)return r.json()
  const reader=r.body?.getReader();let total=0;const chunks:Uint8Array[]=[]
  if(reader){try{while(true){const part=await reader.read();if(part.done)break;total+=part.value.byteLength;if(total>MAX_FILE_BYTES){await reader.cancel();throw Error('Download exceeds budget')}chunks.push(part.value)}}finally{reader.releaseLock()}}
  const joined=new Uint8Array(total);let at=0;for(const chunk of chunks){joined.set(chunk,at);at+=chunk.byteLength}
  return {bytes:joined.buffer,sha:r.headers.get('X-Sha256')}
}
export function intakeError(e:unknown):string {
  if(e instanceof ApiError){if(e.status===403)return '当前身份或案件策略不允许访问受限登记原件。';if(e.status===404)return '未找到案件或本片登记回执；旧证据不会自动迁移为本片登记。';if(e.status===409)return '登记记录、原件完整性或请求绑定不一致，已停止操作；不会覆盖或自动修复。';if(e.status===413)return '超过本片 8 MiB 原件 / 12 MiB 请求工程上限，不代表证据无效。';if([400,422].includes(e.status))return '输入被拒绝。请核对文件名、字段限额及已知 UTC 整秒提取时间；未自动重试。'}
  return '请求失败或响应无法核对。请核查服务与登记记录。'
}
