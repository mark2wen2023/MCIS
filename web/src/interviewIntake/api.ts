import {contentRequest} from '../interview/contentAccess'
import {casePath} from '../api'
export const manualPath=(caseId:string,path='')=>casePath('/manual-interviews'+path,caseId)
export async function manualRequest(caseId:string,who:string,path='',body?:unknown,signal?:AbortSignal){try{return await contentRequest<unknown>(manualPath(caseId,path),who,body,signal)}catch(e){if(e instanceof SyntaxError)throw new Error('响应格式无法核验，写入结果仍未确认。');throw e}}
export async function sources(caseId:string,who:string,signal:AbortSignal){const v=await contentRequest<unknown>(casePath('/evidence',caseId),who,undefined,signal);if(!Array.isArray(v)||!v.every(x=>x&&typeof x.evidenceId==='string'&&typeof x.title==='string'))throw new Error('登记证据列表结构无效');return v.map(x=>({evidenceId:x.evidenceId as string,title:x.title as string}))}
