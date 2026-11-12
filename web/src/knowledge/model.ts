export type Kind = 'Case' | 'Challenge' | 'Method'
export type Status = 'Candidate' | 'Published' | 'Rejected' | 'Withdrawn'
export const KINDS = {Case:'案例卡',Challenge:'疑难卡',Method:'方法卡'}
export const STATUSES = {Candidate:'待人工审批',Published:'已人工批准发布',Rejected:'已驳回',Withdrawn:'已撤回'}
export interface Content {kind:Kind;title:string;summary:string;body:string;tags:string[];applicability:string;source:{type:'Public'|'Synthetic';title:string;locator:string;excerpt:string;rightsNote:string;url?:string}}
export interface Card {cardId:string;status:Status;content:Content;contentDigest:string;createdUtc:string;createdBy?:string;reviewedUtc?:string;reviewedBy?:string;reviewNote?:string}
export interface Page {items:Card[];total:number;limit:number;offset:number}
const obj=(x:unknown):x is Record<string,unknown>=>!!x&&typeof x==='object'&&!Array.isArray(x)
const str=(x:unknown):x is string=>typeof x==='string'&&!!x.trim()
export function parseCard(x:unknown):Card {
 if(!obj(x)||!str(x.cardId)||!/^KC-[a-f0-9]{32}$/.test(x.cardId)||!Object.hasOwn(STATUSES,String(x.status))||!str(x.contentDigest)||!/^[a-f0-9]{64}$/.test(x.contentDigest)||!str(x.createdUtc)||!Number.isFinite(Date.parse(x.createdUtc))||!obj(x.content))throw Error('知识卡响应不符合契约')
 const c=x.content,s=c.source
 if(!Object.hasOwn(KINDS,String(c.kind))||!['title','summary','body','applicability'].every(k=>str(c[k]))||!Array.isArray(c.tags)||!c.tags.length||!c.tags.every(str)||!obj(s)||!['Public','Synthetic'].includes(String(s.type))||!['title','locator','excerpt','rightsNote'].every(k=>str(s[k])))throw Error('知识卡内容或出处缺失')
 if(s.type==='Public'&&(!str(s.url)||!/^https:\/\/[^/]+/i.test(s.url)))throw Error('来源链接不安全')
 if(s.type==='Synthetic'&&s.url!==undefined)throw Error('合成样本不能伪造链接')
 for(const k of ['createdBy','reviewedBy','reviewNote'])if(x[k]!==undefined&&!str(x[k]))throw Error('审核元数据不合法')
 if(x.reviewedUtc!==undefined&&(!str(x.reviewedUtc)||!Number.isFinite(Date.parse(x.reviewedUtc))))throw Error('审核时间不合法')
 return x as unknown as Card
}
export function parsePage(x:unknown,status:Status):Page {
 if(!obj(x)||!Array.isArray(x.items)||!Number.isInteger(x.total)||Number(x.total)<0||!Number.isInteger(x.limit)||Number(x.limit)<1||Number(x.limit)>50||!Number.isInteger(x.offset)||Number(x.offset)<0)throw Error('检索响应不合法')
 const items=x.items.map(parseCard)
 if(items.some(c=>c.status!==status)||new Set(items.map(c=>c.cardId)).size!==items.length||items.length>Number(x.limit)||items.length>Number(x.total))throw Error('检索结果状态或编号不一致')
 return {...x,items} as unknown as Page
}
export const permissions=(role:string)=>({internal:['Investigator','LeadInvestigator'].includes(role),review:role==='LeadInvestigator'})
export const utc=(s:string)=>new Date(s).toISOString().replace('T',' ').replace('.000Z',' UTC')
export const sample:Content={kind:'Method',title:'合成方法卡：区分观测与推断',summary:'仅用于演示知识卡审核，不是真实案件结论。',body:'记录观测材料、列出不确定性，再单独说明推断过程。此内容仅为软件合成样本。',tags:['合成示例','来源核查'],applicability:'仅供软件流程测试，不是正式海事调查指引。',source:{type:'Synthetic',title:'MCIS知识卡合成示例',locator:'演示段落1',excerpt:'列出不确定性，再单独说明推断过程。',rightsNote:'由本软件测试构造，不含真实个人或内网资料。'}}
