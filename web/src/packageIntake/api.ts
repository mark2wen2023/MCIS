import { ApiError,getRole,getOperator } from '../api'
import { caseIdentity } from '../cases/identity'
import { canUsePackages } from '../packages/model'
export async function request(who:string,path:string,signal:AbortSignal,body?:unknown):Promise<unknown> {
  if(caseIdentity()!==who||!canUsePackages(getRole())||signal.aborted)throw Error('身份或请求已失效')
  const commit=path===':commit'
  const response=await fetch('/api/v1/packages/intakes'+path,{method:body===undefined?'GET':'POST',headers:{'X-MCIS-Role':getRole(),'X-MCIS-Operator':encodeURIComponent(getOperator()),...(body===undefined?{}:{'Content-Type':'application/json'})},signal:commit?undefined:signal,body:body===undefined?undefined:JSON.stringify(body)})
  if(!response.ok)throw new ApiError(response.status,'PACKAGE_INTAKE','案件包请求未完成',null)
  return response.json()
}
export function errorText(error:unknown):string {
  if(error instanceof ApiError){
    if(error.status===403)return '当前身份无权导入或读取回执。'
    if(error.status===404)return '暂未查到导入回执。这不证明写入未发生；请稍后只读回查，勿重发。'
    if(error.status===409)return '案号冲突或包绑定不符；不会覆盖已有案件。'
    if(error.status===413)return '案件包超过服务安全资源上限。'
    if([400,422].includes(error.status))return '包未通过安全或基础资料范围校验；未知内容不会被丢弃导入。'
  }
  return '请求失败或响应无法核验。'
}
