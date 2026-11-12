import { getRole,getOperator,casePath,ApiError } from '../api'
import { caseIdentity } from '../cases/identity'
import type { ImportBody } from './model'
export async function importRequest(caseId:string,who:string,path:string,signal:AbortSignal,body?:ImportBody&{previewDigest?:string;confirmed?:boolean},raw=false):Promise<unknown>{
  if(caseIdentity()!==who)throw Error('身份已变化')
  const headers:Record<string,string>={'X-MCIS-Role':getRole(),'X-MCIS-Operator':encodeURIComponent(getOperator())}
  if(body)headers['Content-Type']='application/json'
  const r=await fetch('/api/v1'+casePath('/track-imports'+path,caseId),{method:body?'POST':'GET',headers,signal,body:body?JSON.stringify(body):undefined})
  if(!r.ok){let code='TRACK_INPUT';try{const data=await r.json();if(typeof data.code==='string')code=data.code}catch{/* do not expose response internals */}throw new ApiError(r.status,code,'请求未完成',null)}
  return raw?r.arrayBuffer():r.json()
}
export function inputError(e:unknown):string {
  if(e instanceof ApiError){if(e.status===403)return '当前身份或案件权限不允许此操作。';if(e.status===404)return '未找到案件、船舶或导入回执。';if(e.status===409)return '案件纪元、预览或船舶现状已变化；已有航迹不会被覆盖。请重新读取并核查。';if(e.status===413)return '文件或请求超过服务端预算。仅支持最多 1 MiB、10000 行。';if(e.status===422||e.status===400)return '服务拒绝此输入。请核对固定列、UTF-8、字段状态、来源和完整 UTC。没有自动重试。'}
  return '请求失败或响应无法核对，请检查服务后重试。'
}
