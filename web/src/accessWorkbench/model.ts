export const permissions=['ReadWrite','ReadOnly','Redacted','Deny'] as const
export type Permission=typeof permissions[number]
export interface FieldRule {ruleId:string;field:string;method:string;appliesTo:string[];description?:string}
export interface Policy {version?:string;categories?:string[];matrix:Record<string,Record<string,Permission>>;fieldRules:FieldRule[]}
export interface PolicyEvent {seq:number;caseId?:string|null;utc:string;operator:string;role?:string;action:string;category:string;command:string;before:string;after:string;prevHash:string}
export interface Workbench {caseId:string;policy:Policy;policySource:'default'|'saved';policyAudit:{events:PolicyEvent[];limit:50;hasMore:boolean};identityMode:'local-role-header';readOnly:true}
function obj(v:unknown):Record<string,unknown>{if(!v||typeof v!=='object'||Array.isArray(v))throw Error('Invalid object');return v as Record<string,unknown>}
const strings=(v:unknown):v is string[]=>Array.isArray(v)&&v.every(x=>typeof x==='string')
export function parseWorkbench(raw:unknown,caseId:string):Workbench {
 const v=obj(raw),p=obj(v.policy),a=obj(v.policyAudit)
 if(v.caseId!==caseId||!['default','saved'].includes(v.policySource as string)||v.identityMode!=='local-role-header'||v.readOnly!==true)throw Error('Invalid context')
 if(p.version!==undefined&&typeof p.version!=='string'||p.categories!==undefined&&!strings(p.categories))throw Error('Invalid policy')
 for(const row of Object.values(obj(p.matrix)))for(const value of Object.values(obj(row)))if(!permissions.includes(value as Permission))throw Error('Invalid permission')
 if(!Array.isArray(p.fieldRules))throw Error('Invalid rules')
 for(const rawRule of p.fieldRules){const r=obj(rawRule);if(!['ruleId','field','method'].every(k=>typeof r[k]==='string')||!['RoleCode','Mask','Token','Remove','Generalize'].includes(r.method as string)||!strings(r.appliesTo)||r.description!==undefined&&typeof r.description!=='string')throw Error('Invalid rule')}
 if(a.limit!==50||typeof a.hasMore!=='boolean'||!Array.isArray(a.events)||a.events.length>50)throw Error('Invalid audit')
 const seqs=new Set<number>()
 for(const rawEvent of a.events){const e=obj(rawEvent);if(!Number.isSafeInteger(e.seq)||(e.seq as number)<1||seqs.has(e.seq as number)||e.caseId!==caseId||e.action!=='policy.update'||e.category!=='Access'||e.entityType!=='accessPolicy'||e.entityId!=='policy'||!['utc','operator','category','command','before','after','prevHash'].every(k=>typeof e[k]==='string')||!Number.isFinite(Date.parse(e.utc as string))||!/^[0-9a-f]{64}$/.test(e.prevHash as string)||e.role!==undefined&&typeof e.role!=='string')throw Error('Invalid audit event');seqs.add(e.seq as number)}
 return v as unknown as Workbench
}
export function categories(policy:Policy):string[]{return [...new Set([...(policy.categories??[]),...Object.values(policy.matrix).flatMap(row=>Object.keys(row))])]}
export const permissionNames:Record<Permission,string>={ReadWrite:'读写',ReadOnly:'只读',Redacted:'脱敏读取',Deny:'拒绝'}

const names:Record<string,string>={LeadInvestigator:'首席调查员',Investigator:'调查员',ExternalExpert:'外部专家',InterestedState:'相关国家',AgentService:'智能体服务',Public:'公众',ais_sim:'AIS与仿真',vdr_audio:'VDR音频',testimony:'证言笔录',personal:'个人资料',medical:'医疗资料',report_draft:'报告草稿',evidence_meta:'证据登记',timeline:'时间线',colreg:'避碰规则',recommendations:'安全建议',audit:'审计',agent_drafts:'智能体草稿',RoleCode:'角色代号',Mask:'遮盖',Token:'标记替换',Remove:'移除',Generalize:'概化'}
export const displayName=(key:string)=>Object.hasOwn(names,key)?`${names[key]} (${key})`:key
