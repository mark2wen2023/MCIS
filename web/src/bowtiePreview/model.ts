export const PROFILE='MCIS-BOWTIE-PREVIEW-1'
export const kinds=['Threat','PreventionBarrier','MitigationBarrier','Consequence','EscalationFactor'] as const
export type Kind=typeof kinds[number]
export interface Source{evidenceId:string;title:string;sha256:string}
export interface Node{id:string;label:string;kind:Kind;barrierId:string|null}
export interface Model{hazard:string;topEvent:{id:string;label:string};nodes:Node[];edges:{fromId:string;toId:string}[]}
export interface Input{model:Model;sourceEvidenceIds:string[]}
export interface Issue{code:string;elementId:string;message:string;severity?:string}
export interface Preview{profile:string;caseId:string;inputSha256:string;sources:Source[];sourceRole:string;sourceBinding:string;persisted:false;assessment:string;result:{coreVersion:string;mode:string;constructionErrors:Issue[];validationIssues:Issue[];structureValid:boolean;notCheckedRefCount:0;nodeCount:number;edgeCount:number};limitations:string[]}
export const names:Record<string,string>={Threat:'威胁',PreventionBarrier:'预防屏障',MitigationBarrier:'减缓屏障',Consequence:'后果',EscalationFactor:'升级因素',TopEvent:'顶事件'}
const obj=(v:unknown):Record<string,unknown>=>{if(!v||typeof v!=='object'||Array.isArray(v))throw Error('响应格式无效');return v as Record<string,unknown>}
export function validateInput(v:Input){const m=v.model,id=(x:string)=>/^[A-Za-z0-9_-]{1,64}$/.test(x),label=(x:string)=>!!x.trim()&&x===x.trim()&&Array.from(x).length<=500
 if(!label(m.hazard)||!id(m.topEvent.id)||!label(m.topEvent.label))throw Error('危险源及顶事件必填；ID为1至64位ASCII字母数字、下划线或连字符，文字须去首尾空格且不超过500字。')
 if(m.nodes.length>64||m.edges.length>128||v.sourceEvidenceIds.length>8||new Set(v.sourceEvidenceIds).size!==v.sourceEvidenceIds.length)throw Error('最多64节点、128连线、8条不同来源。')
 for(const n of m.nodes)if(!id(n.id)||!label(n.label)||!kinds.includes(n.kind)||(n.kind==='EscalationFactor'?!n.barrierId||!id(n.barrierId):n.barrierId!==null))throw Error('请核对节点ID、名称、类型及升级因素的屏障ID。')
 for(const e of m.edges)if(!id(e.fromId)||!id(e.toId))throw Error('请选择或填写连线两端ID。')
}
function parseSourceList(raw:unknown):Source[]{if(!Array.isArray(raw))throw Error('来源无效');const ids=new Set<string>();for(const x of raw){const s=obj(x);if(typeof s.evidenceId!=='string'||ids.has(s.evidenceId)||typeof s.title!=='string'||typeof s.sha256!=='string'||!/^[a-f0-9]{64}$/i.test(s.sha256))throw Error('来源无效');ids.add(s.evidenceId)}return raw as Source[]}
export function parseSources(raw:unknown,caseId:string){const v=obj(raw);if(v.profile!==PROFILE||v.caseId!==caseId||v.sourceBinding!=='registered-metadata-only'||v.identityMode!=='local-role-header')throw Error('来源上下文不符');return parseSourceList(v.sources)}
export class SourceChangedError extends Error{}
export function parsePreview(raw:unknown,caseId:string,who:string,input:Input,hash:string,selected:Source[]):Preview{const v=obj(raw),r=obj(v.result),ss=parseSourceList(v.sources)
 if(ss.length!==selected.length||selected.some(s=>!ss.some(a=>a.evidenceId===s.evidenceId&&a.title===s.title&&a.sha256===s.sha256)))throw new SourceChangedError('来源登记已变化，请刷新来源重新核对。')
 if(v.profile!==PROFILE||v.caseId!==caseId||v.sourceRole!==who.split('\n')[0]||v.sourceBinding!=='registered-metadata-only'||v.persisted!==false||v.assessment!=='hypothesis-structure-only'||v.inputSha256!==hash||r.coreVersion!=='mcis-bowtie/1'||r.mode!=='hypothesis-structure-only'||typeof r.structureValid!=='boolean'||r.notCheckedRefCount!==0)throw Error('结果绑定不符')
 for(const key of ['constructionErrors','validationIssues']){if(!Array.isArray(r[key]))throw Error('诊断无效');for(const raw of r[key] as unknown[]){const d=obj(raw);if(!['code','elementId','message'].every(k=>typeof d[k]==='string')||!(d.code as string).startsWith('sys_')||key==='validationIssues'&&!['Info','Warning','Error'].includes(d.severity as string))throw Error('诊断无效')}}
 const errors=r.constructionErrors as Issue[],issues=r.validationIssues as Issue[]
 if(r.structureValid!==(errors.length===0&&!issues.some(x=>x.severity==='Error'))||errors.length&&issues.length)throw Error('诊断状态不符')
 if(!Number.isSafeInteger(r.nodeCount)||(r.nodeCount as number)<0||(r.nodeCount as number)>input.model.nodes.length+1||!Number.isSafeInteger(r.edgeCount)||(r.edgeCount as number)<0||(r.edgeCount as number)>input.model.edges.length||!errors.length&&(r.nodeCount!==input.model.nodes.length+1||r.edgeCount!==input.model.edges.length))throw Error('核心计数不符')
 if(!Array.isArray(v.limitations)||!v.limitations.every(x=>typeof x==='string'))throw Error('局限声明无效')
 return v as unknown as Preview
}
const compare=(a:string,b:string)=>{const x=Array.from(a,c=>c.codePointAt(0)!),y=Array.from(b,c=>c.codePointAt(0)!);for(let i=0;i<Math.min(x.length,y.length);i++)if(x[i]!==y[i])return x[i]!-y[i]!;return x.length-y.length}
export function canonicalInput(caseId:string,model:Model,sources:Source[]):string{const sort=(v:unknown):unknown=>Array.isArray(v)?v.map(sort):v!==null&&typeof v==='object'?Object.fromEntries(Object.entries(v).sort(([a],[b])=>compare(a,b)).map(([k,x])=>[k,sort(x)])):v;return JSON.stringify(sort({caseId,model,sources:[...sources].sort((a,b)=>compare(a.evidenceId,b.evidenceId))}))}
export async function inputHash(caseId:string,model:Model,sources:Source[]){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(canonicalInput(caseId,model,sources))))).map(x=>x.toString(16).padStart(2,'0')).join('')}
