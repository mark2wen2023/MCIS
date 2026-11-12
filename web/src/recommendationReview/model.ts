export const STATUS:Record<string,string>={Draft:'草拟',Issued:'已发布（本地状态）',Responded:'已回复 · 落实中',Implemented:'已落实',NotAdopted:'未采纳',Closed:'已关闭'}
function object(x:unknown):Record<string,unknown>{if(!x||typeof x!=='object'||Array.isArray(x))throw Error('invalid');return x as Record<string,unknown>}
function text(x:unknown):string{if(typeof x!=='string')throw Error('invalid');return x}
function utc(x:unknown):string{
 const v=text(x),m=/^(\d{4})-(\d{2})-(\d{2})T([01]\d|2[0-3]):([0-5]\d):([0-5]\d)(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/.exec(v)
 if(!m||!Number.isFinite(Date.parse(v)))throw Error('invalid')
 const year=Number(m[1]),month=Number(m[2]),day=Number(m[3]),days=[31,year%4===0&&(year%100!==0||year%400===0)?29:28,31,30,31,30,31,31,30,31,30,31]
 if(month<1||month>12||day<1||day>days[month-1])throw Error('invalid')
 return v
}
export type Content={id:string;caseId:string;title:string;body:string;addressee:string;status:string;updatedUtc:string|null;responses:{party:string;text:string;utc:string}[]}
export function parseContent(value:unknown,caseId:string,id:string):Content{
 const r=object(value)
 if(r.caseId!==caseId||r.id!==id||!/^SR-\d{4}-\d{2,}$/.test(id)||typeof r.status!=='string'||!Object.hasOwn(STATUS,r.status))throw Error('invalid')
 const title=text(r.title),addressee=text(r.addressee)
 if(!title||!addressee||!Array.isArray(r.causeNodeIds)||!r.causeNodeIds.length||!r.causeNodeIds.every(c=>typeof c==='string'))throw Error('invalid')
 utc(r.dueUtc);utc(r.createdUtc)
 if(r.responses!==undefined&&!Array.isArray(r.responses))throw Error('invalid')
 return {id,caseId,title,body:r.body===undefined?'':text(r.body),addressee,status:r.status,updatedUtc:r.updatedUtc===undefined?null:utc(r.updatedUtc),responses:((r.responses??[]) as unknown[]).map(v=>{const a=object(v);return {party:text(a.party),text:text(a.text),utc:utc(a.utc)}})}
}
export type History={seq:number;utc:string;operator:string;action:string;command:string;before:string;after:string}
export function parseHistory(value:unknown,caseId:string,id:string):History[]{
 if(!Array.isArray(value)||value.length>200)throw Error('invalid')
 const seen=new Set<number>()
 return value.map(v=>{const r=object(v)
 if(r.caseId!==caseId||r.entityId!==id||r.entityType!=='recommendation'||r.category!=='SafetyRec'||typeof r.seq!=='number'||!Number.isSafeInteger(r.seq)||r.seq<1||seen.has(r.seq))throw Error('invalid')
 seen.add(r.seq)
 return {seq:r.seq,utc:utc(r.utc),operator:text(r.operator),action:text(r.action),command:text(r.command),before:text(r.before),after:text(r.after)}
 }).sort((a,b)=>a.seq-b.seq)
}
