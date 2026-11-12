export const MAX_BYTES = 32 * 1024 * 1024
export interface HfacsExtension {version:'MCIS-HFACS-PACKAGE-1';draftCount:0|1;revisionCount:number;receiptCount:number;receiptMode:'archive-only';identityMode:'unverified-self-reported'}
export interface Preview {packageVersion:'1.0.0'|'1.1.0';hfacsExtension:HfacsExtension|null;profile:string;caseId:string;title:string;sourceSha256:string;byteLength:number;counts:Record<string,number>;warnings:string[]}
export interface Receipt extends Omit<Preview,'warnings'> {importedUtc:string;replayed:boolean}
export function fileError(file:Pick<File,'name'|'size'>):string|null {
  if(!/\.mcase$/i.test(file.name))return '请选择 .mcase 案件包。'
  if(file.size<=0 || file.size>MAX_BYTES)return '仅支持非空且不超过 32 MiB 的案件包。'
  return null
}
export function encodeBytes(bytes:Uint8Array):string {
  let result='';for(let i=0;i<bytes.length;i+=8192)result+=String.fromCharCode(...bytes.subarray(i,i+8192))
  return btoa(result)
}
export function parsePreview(input:unknown):Preview {
  if(!input||typeof input!=='object'||Array.isArray(input))throw Error('响应无效')
  const v=input as Record<string,unknown>
  if(v.profile!=='MCIS-BASIC-INTAKE-1'||typeof v.caseId!=='string'||!v.caseId||typeof v.title!=='string'||!v.title||typeof v.sourceSha256!=='string'||!/^[a-f0-9]{64}$/.test(v.sourceSha256)||!Number.isSafeInteger(v.byteLength)||(v.byteLength as number)<=0||(v.byteLength as number)>MAX_BYTES)throw Error('响应无效')
  if(v.packageVersion==='1.0.0'){if(v.hfacsExtension!==null)throw Error('旧包不允许HFACS扩展')}
  else if(v.packageVersion==='1.1.0'){
    const h=v.hfacsExtension as Record<string,unknown>|null
    if(!h||typeof h!=='object'||Array.isArray(h)||Object.keys(h).sort().join(',')!=='draftCount,identityMode,receiptCount,receiptMode,revisionCount,version'||h.version!=='MCIS-HFACS-PACKAGE-1'||![0,1].includes(h.draftCount as number)||!Number.isSafeInteger(h.revisionCount)||(h.revisionCount as number)<0||!Number.isSafeInteger(h.receiptCount)||(h.receiptCount as number)<0||h.receiptMode!=='archive-only'||h.identityMode!=='unverified-self-reported')throw Error('HFACS扩展摘要无效')
    if((h.revisionCount as number)>256||h.receiptCount!==h.revisionCount)throw Error('HFACS修订与回执计数不一致')
    if(h.draftCount===0&&(h.revisionCount!==0||h.receiptCount!==0)||h.draftCount===1&&(h.revisionCount as number)<1)throw Error('HFACS扩展计数不一致')
  }else throw Error('不支持的案件包版本')
  if(!v.counts||typeof v.counts!=='object'||Array.isArray(v.counts)||!Object.values(v.counts).every(x=>Number.isSafeInteger(x)&&(x as number)>=0))throw Error('响应计数无效')
  if(!Array.isArray(v.warnings)||!v.warnings.every(x=>typeof x==='string'))throw Error('响应警告无效')
  return v as unknown as Preview
}
export function parseReceipt(input:unknown,expected:Pick<Preview,'sourceSha256'> & Partial<Preview>):Receipt {
  const v=input as Receipt
  parsePreview({...v,warnings:[]})
  if(typeof v.importedUtc!=='string'||!Number.isFinite(Date.parse(v.importedUtc))||typeof v.replayed!=='boolean'||v.sourceSha256!==expected.sourceSha256)throw Error('回执不匹配')
  for(const key of ['caseId','title','profile','byteLength','packageVersion'] as const)if(expected[key]!==undefined&&v[key]!==expected[key])throw Error('回执不匹配')
  if(expected.counts&&JSON.stringify(Object.entries(v.counts).sort())!==JSON.stringify(Object.entries(expected.counts).sort()))throw Error('回执计数不匹配')
  if(expected.hfacsExtension!==undefined){const a=v.hfacsExtension,b=expected.hfacsExtension;if((a===null)!==(b===null)||a&&b&&(['version','draftCount','revisionCount','receiptCount','receiptMode','identityMode'] as const).some(k=>a[k]!==b[k]))throw Error('HFACS回执摘要不匹配')}
  return v
}
