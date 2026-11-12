import { ApiError,getRole,getOperator } from '../api'
import { caseIdentity } from '../cases/identity'
import { canUsePackages } from '../packages/model'
export async function request(who:string,path:string,signal:AbortSignal,body?:unknown):Promise<unknown> {
  if(caseIdentity()!==who||!canUsePackages(getRole())||signal.aborted)throw Error('身份或请求已失效')
  const commit=path===':commit'
  const response=await fetch('/api/v1/packages/intakes'+path,{method:body===undefined?'GET':'POST',headers:{'X-MCIS-Role':getRole(),'X-MCIS-Operator':encodeURIComponent(getOperator()),...(body===undefined?{}:{'Content-Type':'application/json'})},signal:commit?undefined:signal,body:body===undefined?undefined:JSON.stringify(body)})
  if(!response.ok){let code='PACKAGE_INTAKE';try{const data=await response.json();if(typeof data.code==='string')code=data.code}catch{/* Never expose private response details. */}throw new ApiError(response.status,code,'案件包请求未完成',null)}
  return response.json()
}
export function errorText(error:unknown):string {
  if(error instanceof ApiError){
    if(error.status===409&&error.code==='ARCHIVE_HISTORY_ONLY')return '这是只读历史回执，不是本次导入的成功凭证；不会重放或解除待核对写入。'
    if(error.status===409&&error.code==='ARCHIVE_HISTORY_INTEGRITY')return '归档原件或历史关联无法核验，已停止读取；不会当作空历史或自动修复。'
    if(error.status===403)return '当前身份无权导入或读取回执。'
    if(error.status===404)return '暂未查到导入回执。这不证明写入未发生；请稍后只读回查，勿重发。'
    if(error.status===409)return '案号冲突或包绑定不符；不会覆盖已有案件。'
    if(error.status===413)return '案件包超过服务安全资源上限。'
    if([400,422].includes(error.status))return '包未通过安全、版本或受限恢复范围校验；未知内容不会被丢弃导入。'
  }
  return '请求失败或响应无法核验。'
}
