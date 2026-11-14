export type BodyVersion={seq:number;utc:string;before:string;after:string;causeNodeIds:string[];baseVersion:string}
export type BodyView={caseId:string;id:string;body:string;causeNodeIds:string[];status:string;version:string;versions:BodyVersion[]}
const hash=(x:unknown):x is string=>typeof x==='string'&&/^[0-9a-f]{64}$/.test(x)
const text=(x:unknown):x is string=>typeof x==='string'&&[...x].length<=20000&&!/[\uD800-\uDFFF]/u.test(x)
const links=(x:unknown):x is string[]=>Array.isArray(x)&&x.length>0&&x.every(v=>typeof v==='string')
const object=(x:unknown):Record<string,unknown>=>{if(!x||typeof x!=='object'||Array.isArray(x))throw Error('shape');return x as Record<string,unknown>}
export function parseBodyView(raw:unknown,caseId:string,id:string):BodyView{
 const r=object(raw)
 if(r.caseId!==caseId||r.id!==id||!text(r.body)||!links(r.causeNodeIds)||!hash(r.version)||!['Draft','Issued','Responded','Implemented','NotAdopted','Closed'].includes(String(r.status))||!Array.isArray(r.versions)||r.versions.length>20)throw Error('view')
 let prior=Infinity
 const versions=r.versions.map(value=>{const v=object(value)
  if(typeof v.seq!=='number'||!Number.isSafeInteger(v.seq)||v.seq<1||v.seq>=prior||typeof v.utc!=='string'||!Number.isFinite(Date.parse(v.utc))||!text(v.before)||!text(v.after)||!links(v.causeNodeIds)||!hash(v.baseVersion))throw Error('version')
  prior=v.seq;return {seq:v.seq,utc:v.utc,before:v.before,after:v.after,causeNodeIds:v.causeNodeIds,baseVersion:v.baseVersion}
 })
 return {caseId,id,body:r.body,causeNodeIds:r.causeNodeIds,status:r.status as string,version:r.version,versions}
}
