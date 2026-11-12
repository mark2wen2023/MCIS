import {AGENTS} from '../agents/model'
export const DRAFT_STATUS={PendingReview:'待人工审核',Confirmed:'已人工确认',Modified:'已人工修改确认',Rejected:'已驳回'} as const
export const DRAFT_KINDS={statement_extraction:'陈述抽取',timeline_anchor:'时间线锚点',colreg_narrative:'规则分析文字',hfacs_suggestion:'人为因素建议',report_section:'报告章节',similar_cases:'相似案例建议',other:'其他'} as const
export interface DraftSummary {draftId:string;agent:typeof AGENTS[number];kind:keyof typeof DRAFT_KINDS;status:keyof typeof DRAFT_STATUS;citations:number;model:string;createdUtc:string|null;reviewedUtc:string|null;recordId:string|null}
const object=(x:unknown):x is Record<string,unknown>=>!!x&&typeof x==='object'&&!Array.isArray(x)
const text=(x:unknown,max=240):x is string=>typeof x==='string'&&x.length>0&&x.length<=max&&!Array.from(x).some(c=>c.charCodeAt(0)<32||c.charCodeAt(0)===127)
const timestamp=(x:unknown)=>x==null||(typeof x==='string'&&/^\d{4}-\d\d-\d\dT/.test(x)&&Number.isFinite(Date.parse(x)))
// Validate the existing common.schema citation shape before counting. Never retain quote text.
function citation(x:unknown):boolean {
 if(!object(x)||typeof x.quote!=='string'||Object.keys(x).some(k=>!['quote','evidenceId','recordId','round','page'].includes(k)))return false
 if(x.evidenceId!==undefined&&(typeof x.evidenceId!=='string'||!/^EV-[0-9]{3,}$/.test(x.evidenceId)))return false
 if(x.recordId!==undefined&&typeof x.recordId!=='string')return false
 return ['round','page'].every(k=>x[k]===undefined||(Number.isInteger(x[k])&&Number(x[k])>=1))
}
export function parseQueue(value:unknown,caseId:string):DraftSummary[]{
 if(!Array.isArray(value))throw Error('草稿队列格式异常')
 const ids=new Set<string>()
 return value.map(d=>{
  if(!object(d)||d.caseId!==caseId||!text(d.draftId)||!/^AD-\d{3,}$/.test(d.draftId)||ids.has(d.draftId)||!AGENTS.includes(d.agent as typeof AGENTS[number])||!Object.hasOwn(DRAFT_STATUS,String(d.status))||!Object.hasOwn(DRAFT_KINDS,String(d.kind))||!Array.isArray(d.citations)||!d.citations.length||!d.citations.every(citation)||!object(d.payload)||(d.model!==undefined&&!text(d.model,200))||!timestamp(d.createdUtc)||!timestamp(d.reviewedUtc))throw Error('草稿队列与案件或契约不一致，未展示任何记录')
  ids.add(d.draftId)
  const supported=d.agent==='people_ops'&&d.kind==='statement_extraction'&&d.targetEntityType==='interviewStatements'
  if(supported&&(!text(d.targetEntityId)||d.payload.recordId!==d.targetEntityId))throw Error('笔录草稿目标不一致')
  return {draftId:d.draftId,agent:d.agent as DraftSummary['agent'],kind:d.kind as DraftSummary['kind'],status:d.status as DraftSummary['status'],citations:d.citations.length,model:d.model as string||'未记录',createdUtc:d.createdUtc as string||null,reviewedUtc:d.reviewedUtc as string||null,recordId:supported?d.targetEntityId as string:null}
 })
}
export function interviewLink(caseId:string,recordId:string){return '/interview?'+new URLSearchParams({case:caseId,record:recordId}).toString()}
export const displayUtc=(v:string|null)=>v?new Date(v).toISOString().replace('T',' ').replace(/\.\d{3}Z$/,' UTC'):'未记录'
