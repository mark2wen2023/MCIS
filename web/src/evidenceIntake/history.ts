import {ApiError,casePath} from '../api'
import {caseIdentity} from '../cases/identity'
import {sha256} from './model'
/** Explicit history access, never a receipt recovery or a replay. */
export async function downloadHistory(caseId:string,evidenceId:string,who:string,signal:AbortSignal){
 if(caseIdentity()!==who||signal.aborted)throw new DOMException('会话已变化','AbortError')
 const [role,...operator]=who.split('\n')
 const r=await fetch('/api/v1'+casePath('/archive-history/evidence/'+encodeURIComponent(evidenceId)+'/content',caseId),{cache:'no-store',signal,headers:{'X-MCIS-Role':role,'X-MCIS-Operator':encodeURIComponent(operator.join('\n'))}})
 if(!r.ok){let code='HISTORY_DOWNLOAD';try{const v=await r.json();if(typeof v.code==='string')code=v.code}catch{}throw new ApiError(r.status,code,'历史原件下载未完成',null)}
 if(!/^attachment(?:;|$)/i.test(r.headers.get('Content-Disposition')||'')||!/(?:^|,)\s*no-store\s*(?:,|$)/i.test(r.headers.get('Cache-Control')||''))throw new Error('历史下载响应不符合附件与缓存边界')
 const sha=r.headers.get('X-Sha256');if(!sha||!/^[0-9a-f]{64}$/.test(sha))throw new Error('历史下载缺少可核对的摘要')
 const reader=r.body?.getReader();if(!reader)throw new Error('历史下载无数据流')
 const chunks:Uint8Array[]=[];let size=0
 try{while(true){const v=await reader.read();if(v.done)break;size+=v.value.byteLength;if(size>16*1024*1024){await reader.cancel();throw new Error('历史下载超过16MiB工程上限')}chunks.push(v.value)}}finally{reader.releaseLock()}
 const joined=new Uint8Array(size);let at=0;for(const part of chunks){joined.set(part,at);at+=part.byteLength}
 if(await sha256(joined.buffer)!==sha)throw new Error('历史原件摘要不一致，未交付文件')
 if(caseIdentity()!==who||signal.aborted)throw new DOMException('会话已变化','AbortError')
 return {bytes:joined.buffer,sha}
}
