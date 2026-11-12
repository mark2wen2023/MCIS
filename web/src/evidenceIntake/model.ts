export const PROFILE='mcis-evidence-intake-v1' as const
export const MAX_FILE_BYTES=8*1024*1024
export const CATEGORIES=['VDR','AIS','ECDIS','EngineLog','Testimony','Photo','Document','Other'] as const
export type Category=typeof CATEGORIES[number]
export interface Metadata {title:string;source:string;extractedBy:string;extractedUtc:string;category:Category;confidentiality:'Restricted';note:string}
export interface IntakeBody extends Metadata {profile:typeof PROFILE;fileName:string;contentBase64:string}
export interface Preview {profile:typeof PROFILE;caseId:string;requestDigest:string;sourceSha256:string;fileName:string;byteLength:number;metadata:Metadata;warnings:string[]}
export interface Receipt {caseId:string;evidenceId:string;requestDigest:string;sourceSha256:string;fileName:string;byteLength:number;metadata:Metadata;registeredUtc:string;registeredBy:string;registeredRole:string;evidence:{caseId:string;evidenceId:string;status:string;accessCount:number;[key:string]:unknown};replayed:boolean}
export const META_KEYS=['title','source','extractedBy','extractedUtc','category','confidentiality','note'] as const
const obj=(v:unknown):v is Record<string,unknown>=>!!v&&typeof v==='object'&&!Array.isArray(v)
const hash=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v)
const size=(v:unknown):v is number=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=0&&v<=MAX_FILE_BYTES
export function utcSeconds(s:string):boolean{return /^[1-9]\d{3}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(s)&&Number.isFinite(Date.parse(s))&&new Date(s).toISOString().replace('.000Z','Z')===s}
export function fileNameValid(s:string):boolean{return !!s&&s.length<=128&&s!=='.'&&s!=='..'&&![...s].some(c=>c==='/'||c===':'||c==='\\'||c.charCodeAt(0)<32||c.charCodeAt(0)===127)}
export function validateMetadata(m:Metadata):void {
  for(const [key,max] of [['title',1000],['source',1000],['extractedBy',200]] as const)if(typeof m[key]!=='string'||!m[key].trim()||m[key].length>max)throw Error('标题、来源/取得方式和提取人必填，且不能超过字段限额。')
  if(!utcSeconds(m.extractedUtc))throw Error('请输入已知的 UTC 整秒提取时间，如 2026-01-01T00:00:00Z；未知时间暂不支持，不会自动补造。')
  if(!CATEGORIES.includes(m.category)||m.confidentiality!=='Restricted'||typeof m.note!=='string'||m.note.length>2000)throw Error('类别、受限标记或备注不符合本片输入要求。')
}
export function intakeBody(fileName:string,contentBase64:string,metadata:Metadata):IntakeBody {
  if(!fileNameValid(fileName))throw Error('文件名须为不含目录和控制字符的 1–128 字符名称。')
  validateMetadata(metadata);return {profile:PROFILE,fileName,...metadata,contentBase64}
}
function metadata(v:unknown):v is Metadata {if(!obj(v)||Object.keys(v).length!==META_KEYS.length||!META_KEYS.every(k=>typeof v[k]==='string'))return false;try{validateMetadata(v as unknown as Metadata);return true}catch{return false}}
export function sameMetadata(a:Metadata,b:Metadata){return META_KEYS.every(k=>a[k]===b[k])}
export function parsePreview(v:unknown,caseId:string,body:IntakeBody,local:{sha:string;size:number}):Preview {
  if(!obj(v)||v.profile!==PROFILE||v.caseId!==caseId||!hash(v.requestDigest)||!hash(v.sourceSha256)||v.sourceSha256!==local.sha||!size(v.byteLength)||v.byteLength!==local.size||v.fileName!==body.fileName||!metadata(v.metadata)||!sameMetadata(v.metadata,body)||!Array.isArray(v.warnings)||v.warnings.length>30||!v.warnings.every(w=>typeof w==='string'))throw Error('服务预览与本次原件/声明不一致，未允许登记。')
  return v as unknown as Preview
}
export function parseReceipt(v:unknown,caseId:string,expected?:Preview,evidenceId?:string):Receipt {
  if(!obj(v)||v.caseId!==caseId||typeof v.evidenceId!=='string'||!/^EV-\d+$/.test(v.evidenceId)||!hash(v.requestDigest)||!hash(v.sourceSha256)||typeof v.fileName!=='string'||!fileNameValid(v.fileName)||!size(v.byteLength)||!metadata(v.metadata)||typeof v.registeredUtc!=='string'||!utcSeconds(v.registeredUtc)||typeof v.registeredBy!=='string'||!v.registeredBy||typeof v.registeredRole!=='string'||!['Investigator','LeadInvestigator'].includes(v.registeredRole)||typeof v.replayed!=='boolean'||!obj(v.evidence))throw Error('登记回执格式无法核对。')
  const e=v.evidence,m=v.metadata
  if(e.caseId!==caseId||e.evidenceId!==v.evidenceId||e.sha256!==v.sourceSha256||e.confidentiality!=='Restricted'||typeof e.status!=='string'||!['Unverified','Verified','Mismatch','NeedsReview'].includes(e.status)||typeof e.accessCount!=='number'||!Number.isSafeInteger(e.accessCount)||e.accessCount<0||!(['title','source','extractedBy','extractedUtc','category'] as const).every(k=>e[k]===m[k]))throw Error('回执与证据快照不一致。')
  if(evidenceId&&v.evidenceId!==evidenceId)throw Error('返回了其他证据的回执。')
  if(expected&&(v.requestDigest!==expected.requestDigest||v.sourceSha256!==expected.sourceSha256||v.fileName!==expected.fileName||v.byteLength!==expected.byteLength||!sameMetadata(m,expected.metadata)))throw Error('回执与本次预览不一致。')
  return v as unknown as Receipt
}
export function encodeBytes(bytes:Uint8Array):string{let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(binary)}
export async function sha256(bytes:ArrayBuffer):Promise<string>{return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(x=>x.toString(16).padStart(2,'0')).join('')}
export function downloadBytes(bytes:ArrayBuffer,name:string){const url=URL.createObjectURL(new Blob([bytes],{type:'application/octet-stream'}));const a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}
