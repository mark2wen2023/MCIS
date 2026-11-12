export const MAX_BYTES = 32 * 1024 * 1024
export interface HfacsExtension {version:'MCIS-HFACS-PACKAGE-1';draftCount:0|1;revisionCount:number;receiptCount:number;receiptMode:'archive-only';identityMode:'unverified-self-reported'}
export interface WorkingRecordsExtension {version:'MCIS-WORKING-RECORDS-1'|'MCIS-WORKING-RECORDS-2';trackReceiptCount?:number;interviewCount:number;reportCount:number;reportSnapshotCount:number;manualReceiptCount:number;receiptMode:'archive-only';identityMode:'unverified-self-reported'}
export interface Preview {workingRecordsExtension?:WorkingRecordsExtension|null;packageVersion:'1.0.0'|'1.1.0'|'1.2.0'|'1.3.0';hfacsExtension:HfacsExtension|null;profile:string;caseId:string;title:string;sourceSha256:string;byteLength:number;counts:Record<string,number>;warnings:string[]}
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
  if(!['1.0.0','1.1.0','1.2.0','1.3.0'].includes(v.packageVersion as string))throw Error('不支持的案件包版本')
  if(v.packageVersion==='1.0.0'&&v.hfacsExtension!==null)throw Error('旧包不允许HFACS扩展')
  if(v.packageVersion==='1.1.0'||['1.2.0','1.3.0'].includes(v.packageVersion as string)&&v.hfacsExtension!==null){
    const h=v.hfacsExtension as Record<string,unknown>|null
    if(!h||typeof h!=='object'||Array.isArray(h)||Object.keys(h).sort().join(',')!=='draftCount,identityMode,receiptCount,receiptMode,revisionCount,version'||h.version!=='MCIS-HFACS-PACKAGE-1'||![0,1].includes(h.draftCount as number)||!Number.isSafeInteger(h.revisionCount)||(h.revisionCount as number)<0||!Number.isSafeInteger(h.receiptCount)||(h.receiptCount as number)<0||h.receiptMode!=='archive-only'||h.identityMode!=='unverified-self-reported')throw Error('HFACS扩展摘要无效')
    if((h.revisionCount as number)>256||h.receiptCount!==h.revisionCount)throw Error('HFACS修订与回执计数不一致')
    if(h.draftCount===0&&(h.revisionCount!==0||h.receiptCount!==0)||h.draftCount===1&&(h.revisionCount as number)<1)throw Error('HFACS扩展计数不一致')
  }
  if(v.packageVersion==='1.2.0'||v.packageVersion==='1.3.0'){
    const w=v.workingRecordsExtension as Record<string,unknown>|null
    if(!w||typeof w!=='object'||Array.isArray(w)||Object.keys(w).sort().join(',')!==(v.packageVersion==='1.3.0'?'identityMode,interviewCount,manualReceiptCount,receiptMode,reportCount,reportSnapshotCount,trackReceiptCount,version':'identityMode,interviewCount,manualReceiptCount,receiptMode,reportCount,reportSnapshotCount,version')||w.version!==(v.packageVersion==='1.3.0'?'MCIS-WORKING-RECORDS-2':'MCIS-WORKING-RECORDS-1')||w.receiptMode!=='archive-only'||w.identityMode!=='unverified-self-reported')throw Error('工作记录归档摘要无效')
    if(v.packageVersion==='1.3.0'&&(!Number.isSafeInteger(w.trackReceiptCount)||(w.trackReceiptCount as number)<1||(w.trackReceiptCount as number)>2048))throw Error('航迹历史回执计数无效')
    for(const [key,max] of Object.entries({interviewCount:128,reportCount:256,reportSnapshotCount:1024,manualReceiptCount:2048}))if(!Number.isSafeInteger(w[key])||(w[key] as number)<0||(w[key] as number)>max)throw Error('工作记录计数无效')
  }else if(v.workingRecordsExtension!==undefined&&v.workingRecordsExtension!==null)throw Error('旧版本不允许工作记录扩展')
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
  if(expected.workingRecordsExtension!==undefined){const a=v.workingRecordsExtension,b=expected.workingRecordsExtension;if((a==null)!==(b==null)||a&&b&&(['version','trackReceiptCount','interviewCount','reportCount','reportSnapshotCount','manualReceiptCount','receiptMode','identityMode'] as const).some(k=>a[k]!==b[k]))throw Error('工作记录回执摘要不匹配')}
  return v
}
