export const MAX_FILE_BYTES=1024*1024
export const TEMPLATE='utc,latDeg,lonDeg,sogKn,sogStatus,cogDeg,cogStatus,hdgDeg,hdgStatus\r\n'
export interface ImportBody {profile:'mcis-utc-v1';vesselId:string;fileName:string;source:string;timeBasis:string;contentBase64:string}
export interface Issue {row:number;field:string;code:string;message:string}
export interface PreviewPoint {vesselId:string;utc:string;timeSec:number;latDeg:number;lonDeg:number;sogKn:number;cogDeg:number;hdgDeg?:number|null}
export interface Preview {profile:'mcis-utc-v1';caseId:string;vesselId:string;caseEpochUtc:string;previewDigest:string;sourceSha256:string;rowCount:number;canCommit:boolean;issues:Issue[];issuesTotal:number;issuesTruncated:boolean;samplePoints:PreviewPoint[];warnings:string[];existingTrackCount:number;fileName:string;source:string;timeBasis:string;timeRange:{firstUtc:string;lastUtc:string;fromSec:number;toSec:number}|null}
export interface Receipt {caseId:string;vesselId:string;previewDigest:string;sourceSha256:string;pointCount:number;sourceEvidenceId:string;reportEvidenceId:string;committedUtc:string;replayed:boolean;reportSha256?:string}
const obj=(v:unknown):v is Record<string,unknown>=>!!v&&typeof v==='object'&&!Array.isArray(v)
const hash=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v)
const integer=(v:unknown):v is number=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=0
const finite=(v:unknown):v is number=>typeof v==='number'&&Number.isFinite(v)
const string=(v:unknown):v is string=>typeof v==='string'
export function parsePreview(v:unknown,caseId:string,body:ImportBody):Preview {
  if(!obj(v)||v.profile!==body.profile||v.caseId!==caseId||v.vesselId!==body.vesselId||!hash(v.previewDigest)||!hash(v.sourceSha256)||!string(v.caseEpochUtc)||!integer(v.rowCount)||v.rowCount>10000||typeof v.canCommit!=='boolean'||!integer(v.issuesTotal)||!integer(v.existingTrackCount)||typeof v.issuesTruncated!=='boolean'||v.fileName!==body.fileName||v.source!==body.source||v.timeBasis!==body.timeBasis)throw Error('预览响应不匹配，未允许保存。')
  if(!Array.isArray(v.issues)||v.issues.length>200||!v.issues.every(i=>obj(i)&&integer(i.row)&&string(i.field)&&string(i.code)&&string(i.message))||v.issues.length>v.issuesTotal||!Array.isArray(v.warnings)||!v.warnings.every(string))throw Error('预览诊断无效，未允许保存。')
  if(!Array.isArray(v.samplePoints)||v.samplePoints.length>100||!v.samplePoints.every(p=>obj(p)&&p.vesselId===body.vesselId&&string(p.utc)&&['timeSec','latDeg','lonDeg','sogKn','cogDeg'].every(k=>finite(p[k]))&&(p.hdgDeg==null||finite(p.hdgDeg))))throw Error('预览点格式无效，未允许保存。')
  if(v.timeRange!==null&&(!obj(v.timeRange)||!string(v.timeRange.firstUtc)||!string(v.timeRange.lastUtc)||!finite(v.timeRange.fromSec)||!finite(v.timeRange.toSec)))throw Error('时间范围无效，未允许保存。')
  if(v.canCommit&&(v.rowCount===0||v.issuesTotal>0||v.existingTrackCount>0))throw Error('预览状态矛盾，未允许保存。')
  return v as unknown as Preview
}
export function parseReceipt(v:unknown,caseId:string,vesselId:string,expected?:{previewDigest:string;sourceSha256:string;rowCount:number}):Receipt {
  if(!obj(v)||v.caseId!==caseId||v.vesselId!==vesselId||!hash(v.previewDigest)||!hash(v.sourceSha256)||!integer(v.pointCount)||v.pointCount===0||!string(v.sourceEvidenceId)||!v.sourceEvidenceId||!string(v.reportEvidenceId)||!v.reportEvidenceId||!string(v.committedUtc)||typeof v.replayed!=='boolean'||(v.reportSha256!==undefined&&!hash(v.reportSha256)))throw Error('保存回执无法核对。')
  if(expected&&(v.previewDigest!==expected.previewDigest||v.sourceSha256!==expected.sourceSha256||v.pointCount!==expected.rowCount))throw Error('保存回执与本次预览不一致。')
  return v as unknown as Receipt
}
export function importBody(vesselId:string,fileName:string,source:string,timeBasis:string,contentBase64:string):ImportBody {
  if(!vesselId)throw Error('请选择本案已登记船舶。')
  if(!fileName||!contentBase64)throw Error('请选择非空 UTF-8 CSV 文件。')
  if(!source.trim()||source.trim().length>1000||!timeBasis.trim()||timeBasis.trim().length>1000)throw Error('请填写来源和 UTC 时间依据，各不超过 1000 字。')
  return {profile:'mcis-utc-v1',vesselId,fileName,source:source.trim(),timeBasis:timeBasis.trim(),contentBase64}
}
export function encodeBytes(bytes:Uint8Array):string {let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(binary)}
export async function sha256(bytes:ArrayBuffer):Promise<string>{return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(x=>x.toString(16).padStart(2,'0')).join('')}
export function downloadBytes(data:Blob,name:string){const url=URL.createObjectURL(data);const a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}
