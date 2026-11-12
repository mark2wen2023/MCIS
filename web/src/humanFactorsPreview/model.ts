export const PROFILE='MCIS-REST-PREVIEW-1'
export interface Source {evidenceId:string;title:string;sha256:string}
export interface Interval {startUtc:string;endUtc:string;kind:'Watch'|'OtherWork'|'Rest'}
export interface Input {recordStartUtc:string;recordEndUtc:string;intervals:Interval[];sourceEvidenceIds:string[]}
export interface Finding {rule:string;windowStartUtc:string;windowEndUtc:string;actualHours:number;limitHours:number;violatingFromUtc:string;violatingToUtc:string;clause:string;detail:string}
export interface Preview {profile:typeof PROFILE;caseId:string;inputSha256:string;sources:Source[];sourceBinding:'registered-metadata-only';persisted:false;assessment:'technical-preview-only';result:{coreVersion:'mcis-rest/1';mode:'rest-baseline-no-exceptions';totals:{restHours:number;workHours:number;unknownHours:number};coverage:{recordHours:number;has24hWindow:boolean;has7dWindow:boolean;unknownHours:number};findings:Finding[];insufficientData:Finding[];assumptions:string[]};limitations:string[]}
const obj=(v:unknown):Record<string,unknown>=>{if(!v||typeof v!=='object'||Array.isArray(v))throw Error('响应格式无效');return v as Record<string,unknown>}
const strings=(v:unknown):v is string[]=>Array.isArray(v)&&v.every(x=>typeof x==='string')
const finite=(v:unknown):v is number=>typeof v==='number'&&Number.isFinite(v)&&v>=0
export function utcSeconds(v:string):boolean{return Number(v.slice(0,4))>=1900&&Number(v.slice(0,4))<=2100&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(v)&&Number.isFinite(Date.parse(v))&&new Date(v).toISOString()===v.slice(0,-1)+'.000Z'}
export function validateInput(v:Input):void {
 if(!utcSeconds(v.recordStartUtc)||!utcSeconds(v.recordEndUtc))throw Error('记录起止须为 UTC 整秒，例如 2026-11-12T08:00:00Z。')
 const start=Date.parse(v.recordStartUtc),end=Date.parse(v.recordEndUtc)
 if(end<=start||end-start>14*86400000)throw Error('记录范围须大于零且不超过14天。')
 if(v.intervals.length<1||v.intervals.length>256)throw Error('请录入1至256个时段。')
 if(v.sourceEvidenceIds.length<1||v.sourceEvidenceIds.length>8||new Set(v.sourceEvidenceIds).size!==v.sourceEvidenceIds.length)throw Error('请选择1至8条不同来源登记。')
 const ordered=[...v.intervals].sort((a,b)=>a.startUtc.localeCompare(b.startUtc));let last=start
 for(const i of ordered){if(!utcSeconds(i.startUtc)||!utcSeconds(i.endUtc)||!['Watch','OtherWork','Rest'].includes(i.kind))throw Error('时段须填写有效UTC整秒与类型。');const a=Date.parse(i.startUtc),b=Date.parse(i.endUtc);if(a<last||b<=a||b>end)throw Error('时段不得重叠、倒序或超出记录范围。');last=b}
}
function sources(v:unknown):Source[]{if(!Array.isArray(v))throw Error('来源格式无效');const ids=new Set<string>();for(const x of v){const s=obj(x);if(typeof s.evidenceId!=='string'||!s.evidenceId||ids.has(s.evidenceId)||typeof s.title!=='string'||typeof s.sha256!=='string'||!/^[a-f0-9]{64}$/i.test(s.sha256))throw Error('来源格式无效');ids.add(s.evidenceId)}return v as Source[]}
export function parseSources(raw:unknown,caseId:string):Source[]{const v=obj(raw);if(v.profile!==PROFILE||v.caseId!==caseId||v.sourceBinding!=='registered-metadata-only')throw Error('来源上下文不符');return sources(v.sources)}
export function parsePreview(raw:unknown,caseId:string,input:Input,expectedHash:string,expectedSources:Source[]):Preview {
 const v=obj(raw),r=obj(v.result),t=obj(r.totals),c=obj(r.coverage)
 if(v.profile!==PROFILE||v.caseId!==caseId||v.persisted!==false||v.assessment!=='technical-preview-only'||v.sourceBinding!=='registered-metadata-only'||typeof v.inputSha256!=='string'||!/^[a-f0-9]{64}$/.test(v.inputSha256)||r.coreVersion!=='mcis-rest/1'||r.mode!=='rest-baseline-no-exceptions')throw Error('预览上下文不符')
 const ss=sources(v.sources);verifySourceSnapshot(ss,expectedSources);
 if(v.inputSha256!==expectedHash)throw Error('输入摘要不匹配');if(ss.length!==input.sourceEvidenceIds.length||ss.some(s=>!input.sourceEvidenceIds.includes(s.evidenceId)))throw Error('来源绑定不符')
 for(const k of ['restHours','workHours','unknownHours'])if(!finite(t[k]))throw Error('小时数无效')
 if(!finite(c.recordHours)||!finite(c.unknownHours)||typeof c.has24hWindow!=='boolean'||typeof c.has7dWindow!=='boolean')throw Error('覆盖率无效')
 const hours=(Date.parse(input.recordEndUtc)-Date.parse(input.recordStartUtc))/3600000
 if(Math.abs((c.recordHours as number)-hours)>1e-6||Math.abs((t.restHours as number)+(t.workHours as number)+(t.unknownHours as number)-hours)>1e-6||Math.abs((c.unknownHours as number)-(t.unknownHours as number))>1e-6||c.has24hWindow!==(hours>=24)||c.has7dWindow!==(hours>=168))throw Error('覆盖范围不符')
 for(const key of ['findings','insufficientData']){if(!Array.isArray(r[key]))throw Error('结果列表无效');for(const f0 of r[key] as unknown[]){const f=obj(f0);if(!['Rest24h','Rest7d','RestSplit','LongestRest','RestInterval'].includes(f.rule as string)||!finite(f.actualHours)||!finite(f.limitHours)||typeof f.clause!=='string'||typeof f.detail!=='string')throw Error('规则结果无效');for(const k of ['windowStartUtc','windowEndUtc','violatingFromUtc','violatingToUtc'])if(typeof f[k]!=='string'||!Number.isFinite(Date.parse(f[k] as string)))throw Error('规则时间无效')}}
 if(!strings(r.assumptions)||!strings(v.limitations))throw Error('局限声明无效')
 return v as unknown as Preview
}

export class SourceChangedError extends Error {}
export function verifySourceSnapshot(actual:Source[],selected:Source[]):void {
 if(actual.length!==selected.length||selected.some(s=>!actual.some(a=>a.evidenceId===s.evidenceId&&a.title===s.title&&a.sha256===s.sha256)))throw new SourceChangedError('来源登记已变化，请刷新来源并重新核对后再预览。')
}
function codepointCompare(a:string,b:string):number {
 const left=Array.from(a,x=>x.codePointAt(0)!),right=Array.from(b,x=>x.codePointAt(0)!)
 for(let i=0;i<Math.min(left.length,right.length);i++)if(left[i]!==right[i])return left[i]!-right[i]!
 return left.length-right.length
}
export function canonicalInput(caseId:string,input:Input,selected:Source[]):string {
 const sort=(v:unknown):unknown=>Array.isArray(v)?v.map(sort):v!==null&&typeof v==='object'?Object.fromEntries(Object.entries(v).sort(([a],[b])=>codepointCompare(a,b)).map(([k,x])=>[k,sort(x)])):v
 return JSON.stringify(sort({caseId,schedule:{recordStartUtc:input.recordStartUtc,recordEndUtc:input.recordEndUtc,intervals:input.intervals},sources:[...selected].sort((a,b)=>codepointCompare(a.evidenceId,b.evidenceId))}))
}
export async function inputHash(caseId:string,input:Input,selected:Source[]):Promise<string>{return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(canonicalInput(caseId,input,selected))))).map(x=>x.toString(16).padStart(2,'0')).join('')}
