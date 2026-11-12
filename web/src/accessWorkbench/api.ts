import { ApiError,getRole,getOperator,casePath } from '../api'
import { caseIdentity } from '../cases/identity'
import { parseWorkbench } from './model'
export async function loadWorkbench(caseId:string,who:string,signal:AbortSignal){
 if(signal.aborted||caseIdentity()!==who)throw Error('Stale identity')
 const r=await fetch('/api/v1'+casePath('/access-workbench',caseId),{method:'GET',cache:'no-store',headers:{'X-MCIS-Role':getRole(),'X-MCIS-Operator':encodeURIComponent(getOperator())},signal})
 if(!r.ok)throw new ApiError(r.status,'ACCESS_WORKBENCH','权限工作台读取失败',null)
 return parseWorkbench(await r.json(),caseId)
}
export function accessError(e:unknown){return e instanceof ApiError&&e.status===403?'当前身份不是调查组，或本案策略不允许完整读取审计。未展示权限配置。':e instanceof ApiError&&e.status===404?'案件不存在，请返回大厅选择案件。':'无法核验权限工作台响应，请检查服务后重试。'}
