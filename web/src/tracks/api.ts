import { ApiError, getOperator, getRole, casePath } from '../api'
import { caseIdentity } from '../cases/identity'
import { parseSnapshot, TrackDataError } from './model'
export async function loadTracks(caseId:string,who:string,query:string,signal:AbortSignal) {
  if(caseIdentity()!==who)throw Error('Identity changed')
  const headers={'X-MCIS-Role':getRole(),'X-MCIS-Operator':encodeURIComponent(getOperator())}
  const get=async(path:string)=>{const r=await fetch('/api/v1'+casePath(path,caseId),{headers,signal});if(!r.ok)throw new ApiError(r.status,'TRACK_READ','读取失败',null);return r.json() as Promise<unknown>}
  const [c,v,t]=await Promise.all([get(''),get('/vessels'),get('/tracks'+query)])
  return parseSnapshot(caseId,c,v,t)
}
export function readError(error:unknown):string {
  if(error instanceof ApiError&&error.status===403)return '当前身份无权读取本案航迹。没有显示先前身份的数据。'
  if(error instanceof ApiError&&error.status===404)return '案件不存在，请返回案件大厅重新选择。'
  if(error instanceof TrackDataError&&error.code==='METADATA_LIMIT')return '船舶或航迹桶数量超过 1000 项界面预算，未显示部分结果。请缩小案件数据范围；这是交互保护，不是海事业务限制。'
  if(error instanceof TrackDataError)return error.code==='LIMIT'?'返回点数超过 50000 点界面预算，请缩小读取时间窗。未显示部分结果。':'返回数据格式、数值或案件/船舶归属不一致，未显示此批数据。'
  return '无法读取航迹，请检查服务连接后重试。未显示旧数据。'
}
