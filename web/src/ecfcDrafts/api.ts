import {ApiError,casePath,getRole,getOperator} from '../api'
import {caseIdentity} from '../cases/identity'
import {strictJson} from '../reportOutput/strictJson'
export async function request(caseId:string,who:string,action:'context'|'draft'|'preview'|'save'|'audit',signal:AbortSignal,body?:unknown):Promise<unknown>{
 if(signal.aborted||caseIdentity()!==who)throw Error('身份失效')
 const response=await fetch('/api/v1'+casePath('/ecfc/'+action,caseId),{method:body===undefined?'GET':'POST',cache:'no-store',signal:action==='save'?undefined:signal,headers:{'X-MCIS-Role':getRole(),'X-MCIS-Operator':encodeURIComponent(getOperator()),...(body===undefined?{}:{'Content-Type':'application/json'})},body:body===undefined?undefined:JSON.stringify(body)})
 if(!response.ok)throw new ApiError(response.status,'ECFC_REQUEST','请求未完成',null)
 if(!response.headers.get('cache-control')?.split(',').map(s=>s.trim()).includes('no-store')||!response.headers.get('content-type')?.toLowerCase().startsWith('application/json'))throw Error('响应头无法核验')
 const reader=response.body?.getReader();if(!reader)throw Error('响应无效');const chunks:Uint8Array[]=[];let size=0
 try{while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>1024*1024)throw Error('响应超过预算');chunks.push(value)}}catch(e){await reader.cancel();throw e}
 const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length}return strictJson(bytes)
}
export function errorText(e:unknown){if(e instanceof ApiError){if(e.status===403)return '当前身份或案件策略不允许读取完整草稿，受限内容已隐藏。默认调查员可能不满足原文权限；请联系有权管理员，不会自动改角色。';if(e.status===409)return '版本、来源或请求标识冲突。未自动覆盖；请重新打开服务端内容核对。';if(e.status===404)return '案件不存在，请返回大厅核对。';if([400,413,415,422].includes(e.status))return '输入或结构未通过工程限制。请核对节点、连线、来源和字数；这不是专业事实判断。'}return '请求失败或响应无法核验。保存结果可能未知，不能认定失败或成功。'}
