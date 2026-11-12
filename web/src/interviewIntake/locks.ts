/** Only non-content recovery metadata is stored. Never persist a request body or transcript. */
export interface Recovery {caseId:string;recordId:string|null;requestId:string;operation:'create'|'append'}
const KEY='mcis.manual-interview.pending.v1'
export function readRecoveries():Recovery[]{
 const raw=sessionStorage.getItem(KEY)
 if(!raw)return []
 const value:unknown=JSON.parse(raw)
 if(!Array.isArray(value)||!value.every(v=>v&&typeof v.caseId==='string'&&(v.recordId===null||typeof v.recordId==='string')&&typeof v.requestId==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v.requestId)&&['create','append'].includes(v.operation)&&Object.keys(v).every(k=>['caseId','recordId','requestId','operation'].includes(k))))throw new Error('本页恢复记录不可读取，不能安全发起新写入。请核查服务器回执。')
 return value
}
export function rememberRecovery(value:Recovery){
 const all=readRecoveries();if(all.some(r=>r.caseId===value.caseId&&r.requestId!==value.requestId))throw new Error('当前案件存在未核验写入，请先查询原请求回执。')
 const next=[...all.filter(r=>r.requestId!==value.requestId),{caseId:value.caseId,recordId:value.recordId,requestId:value.requestId,operation:value.operation}];sessionStorage.setItem(KEY,JSON.stringify(next))
}
export function forgetRecovery(requestId:string){sessionStorage.setItem(KEY,JSON.stringify(readRecoveries().filter(r=>r.requestId!==requestId)))}
