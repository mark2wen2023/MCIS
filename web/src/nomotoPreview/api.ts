import {ApiError,casePath,getRole,getOperator} from '../api'
import {caseIdentity} from '../cases/identity'
export async function nomotoRequest(caseId:string,who:string,action:'sources'|'preview',signal:AbortSignal,body?:unknown):Promise<unknown>{
 if(signal.aborted||caseIdentity()!==who)throw Error('身份或请求已失效')
 const r=await fetch('/api/v1'+casePath('/whatif/nomoto:'+action,caseId),{method:action==='sources'?'GET':'POST',cache:'no-store',signal,headers:{'X-MCIS-Role':getRole(),'X-MCIS-Operator':encodeURIComponent(getOperator()),...(body===undefined?{}:{'Content-Type':'application/json'})},body:body===undefined?undefined:JSON.stringify(body)})
 if(!r.ok)throw new ApiError(r.status,'NOMOTO_PREVIEW','技术预览未完成',null)
 return r.json()
}
export function nomotoError(e:unknown){if(e instanceof ApiError){if(e.status===503)return '计算核心暂不可用，未生成结果。不会用示例结果代替真实计算。';if(e.status===403)return '当前身份或案件策略不允许读取来源或执行预览。';if(e.status===404)return '案件或来源不存在，请返回大厅核对。';if([400,409,422].includes(e.status))return '输入或来源校验未通过，请核对时段与登记来源后重试。'}return '请求失败或响应无法核验，未展示结果。'}
