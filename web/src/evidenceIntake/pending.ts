/** Session-only recovery metadata, never file bytes or human declarations. */
export interface PendingIntake {caseId:string;requestDigest:string;sourceSha256:string;byteLength:number}
const PREFIX='mcis.evidence-intake.pending.v1:'
const HEX=/^[a-f0-9]{64}$/
const keys=['caseId','requestDigest','sourceSha256','byteLength']
const key=(caseId:string)=>PREFIX+encodeURIComponent(caseId)
export function readPending(caseId:string):PendingIntake|null{
 const raw=sessionStorage.getItem(key(caseId));if(raw===null)return null
 const v:unknown=JSON.parse(raw)
 if(!v||typeof v!=='object'||Array.isArray(v))throw Error('登记恢复标识损坏，禁止新登记；请核查服务记录。')
 const x=v as Record<string,unknown>
 if(Object.keys(x).length!==keys.length||!keys.every(k=>Object.hasOwn(x,k))||x.caseId!==caseId||typeof x.requestDigest!=='string'||!HEX.test(x.requestDigest)||typeof x.sourceSha256!=='string'||!HEX.test(x.sourceSha256)||typeof x.byteLength!=='number'||!Number.isSafeInteger(x.byteLength)||x.byteLength<0||x.byteLength>8*1024*1024)throw Error('登记恢复标识损坏，禁止新登记；请核查服务记录。')
 return x as unknown as PendingIntake
}
export function rememberPending(value:PendingIntake){
 if(readPending(value.caseId)!==null)throw Error('当前案件仍有待核查登记，不能另发请求。')
 // Copy only declared recovery fields; never serialize the whole Preview.
 const v={caseId:value.caseId,requestDigest:value.requestDigest,sourceSha256:value.sourceSha256,byteLength:value.byteLength}
 sessionStorage.setItem(key(v.caseId),JSON.stringify(v))
 const stored=readPending(v.caseId)
 if(!stored||!samePending(stored,v))throw Error('恢复标识未可靠保存，未发送登记。')
 return v
}
export function samePending(a:PendingIntake,b:PendingIntake){return keys.every(k=>a[k as keyof PendingIntake]===b[k as keyof PendingIntake])}
export function forgetPending(value:PendingIntake){
 const current=readPending(value.caseId)
 if(!current||!samePending(current,value))throw Error('恢复标识已变化，保留待核查状态。')
 sessionStorage.removeItem(key(value.caseId))
 if(readPending(value.caseId)!==null)throw Error('恢复标识无法清除，保留待核查状态。')
}
