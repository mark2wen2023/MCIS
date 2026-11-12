export const fields = [['title','案件名称',500],['placeName','海域 / 航道名称',1000],['leadInvestigator','首席调查员',500],['agencyName','调查机构',1000],['summaryNotes','概要 / 工作说明',20000]] as const
export type Field=typeof fields[number][0]
export type CaseDoc={caseId:string;title:string;isFictionalDemo:boolean;[key:string]:unknown}
export type Snapshot={case:CaseDoc;revision:string;lastChange:null|{operationId:string;utc:string;operator:string;sourceLabel:string;changeReason:string;fields:Field[]}}
export type Form=Record<Field,string>&{sourceLabel:string;changeReason:string}
export type Update={operationId:string;expectedRevision:string;changes:Partial<Record<Field,string|null>>;sourceLabel:string;changeReason:string}
export const canEdit=(role:string)=>role==='Investigator'||role==='LeadInvestigator'
const isRecord=(v:unknown):v is Record<string,unknown>=>!!v&&typeof v==='object'&&!Array.isArray(v)
export function parseSnapshot(v:unknown,id:string):Snapshot{
 if(!isRecord(v)||!isRecord(v.case)||v.case.caseId!==id||typeof v.case.title!=='string'||typeof v.case.isFictionalDemo!=='boolean'||typeof v.revision!=='string'||!/^[0-9a-f]{64}$/.test(v.revision)||v.revision.length!==64)throw Error('档案响应格式或案件编号无效')
 for(const [k] of fields)if(v.case[k]!==undefined&&typeof v.case[k]!=='string')throw Error('档案文字字段格式无效')
 if(v.lastChange!==null){const c=v.lastChange;if(!isRecord(c)||['operationId','utc','operator','sourceLabel','changeReason'].some(k=>typeof c[k]!=='string')||!Array.isArray(c.fields)||c.fields.some(k=>!fields.some(([f])=>f===k)))throw Error('修改记录格式无效')}
 return v as Snapshot
}
export function formOf(s:Snapshot):Form{return {...Object.fromEntries(fields.map(([k])=>[k,typeof s.case[k]==='string'?s.case[k]:''])),sourceLabel:'',changeReason:''} as Form}
export function changesOf(f:Form,s:Snapshot):Update['changes']{
 const changes:Update['changes']={};for(const [k,label,max] of fields){const before=typeof s.case[k]==='string'?s.case[k]:'';if(f[k]===before)continue
 if(f[k].length>max)throw Error(`${label}最多 ${max} 字。`)
 if(!f[k].trim()){if(k==='title')throw Error('案件名称不可清空。');changes[k]=null}else changes[k]=f[k]
 }return changes
}
export function buildUpdate(f:Form,s:Snapshot,operationId=crypto.randomUUID()):Update{
 const changes=changesOf(f,s);if(!Object.keys(changes).length)throw Error('没有需要保存的修改。')
 for(const [k,label,max] of [['sourceLabel','资料来源',2000],['changeReason','变更理由',4000]] as const)if(!f[k].trim()||f[k].length>max)throw Error(`${label}须为 1–${max} 字的非空文字。`)
 return {operationId,expectedRevision:s.revision,changes,sourceLabel:f.sourceLabel,changeReason:f.changeReason}
}
export function applyChanges(c:CaseDoc,changes:Update['changes']):CaseDoc{const n={...c};for(const [k,v] of Object.entries(changes)){if(v===null)delete n[k];else n[k]=v}return n}
export function sameValue(a:unknown,b:unknown):boolean{if(a===b)return true;if(!isRecord(a)||!isRecord(b))return false;return Object.keys(a).length===Object.keys(b).length&&Object.keys(a).every(k=>Object.hasOwn(b,k)&&sameValue(a[k],b[k]))}
export function matchesUpdate(s:Snapshot,base:Snapshot,u:Update):boolean{return s.lastChange?.operationId===u.operationId&&s.lastChange.sourceLabel===u.sourceLabel&&s.lastChange.changeReason===u.changeReason&&JSON.stringify([...s.lastChange.fields].sort())===JSON.stringify(Object.keys(u.changes).sort())&&s.revision!==base.revision&&sameValue(s.case,applyChanges(base.case,u.changes))}
export function rebaseForm(f:Form,old:Snapshot,current:Snapshot):Form{const changes=changesOf(f,old);const next=formOf(current);for(const [k,v] of Object.entries(changes))next[k as Field]=v??'';next.sourceLabel=f.sourceLabel;next.changeReason=f.changeReason;return next}
export function display(v:unknown):string{if(v===undefined||v===null||(typeof v==='string'&&!v.trim()))return '未填写';if(typeof v==='boolean')return v?'是':'否';if(typeof v==='object')return JSON.stringify(v);return String(v)}
