import {useEffect,useRef,useState,useSyncExternalStore} from 'react'
import {ApiError,onIdentityChange} from '../api'
import {contentIdentity,contentRequest} from '../interview/contentAccess'
import {casePath} from '../api'
export type Kind='interview'|'report'
export interface Provenance {origin:'restored-history';sourceArchiveSha256:string;importedUtc:string;originalDocumentSha256:string;currentDocumentSha256:string;changedSinceImport:boolean}
const object=(v:unknown):v is Record<string,unknown>=>!!v&&typeof v==='object'&&!Array.isArray(v)
const hash=(v:unknown)=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v)
export function parseProvenance(v:unknown,caseId:string,kind:Kind,recordId:string):Provenance|null{
 if(!object(v)||Object.keys(v).sort().join(',')!=='caseId,kind,provenance,recordId'||v.caseId!==caseId||v.kind!==kind||v.recordId!==recordId)throw new Error('恢复来源响应绑定不一致')
 const p=v.provenance;if(p===null)return null
 if(!object(p)||Object.keys(p).sort().join(',')!=='changedSinceImport,currentDocumentSha256,importedUtc,origin,originalDocumentSha256,sourceArchiveSha256'||p.origin!=='restored-history'||!hash(p.sourceArchiveSha256)||!hash(p.originalDocumentSha256)||!hash(p.currentDocumentSha256)||typeof p.importedUtc!=='string'||!Number.isFinite(Date.parse(p.importedUtc))||typeof p.changedSinceImport!=='boolean'||p.changedSinceImport!==(p.originalDocumentSha256!==p.currentDocumentSha256))throw new Error('恢复来源结构不一致')
 return p as unknown as Provenance
}
export function ProvenanceNote({value}:{value:Provenance|null}){return value?<aside className="ic-disclaimer" aria-label="对象恢复历史"><h3>此对象包含恢复历史</h3><p>原有签署、确认和审核为历史工作流字段，不是本次新签署或审核，更不是事实、原始来源或身份认证；恢复后的操作另行留痕。不能因所在案件有归档就推断其他对象也是历史。</p><p>{value.changedSinceImport?'当前文档已不同于导入时原文，不把当前所有状态都称为历史状态。':'服务器摘要显示当前文档与导入时原文一致；这不证明原始真实性。'}</p><dl><dt>最近一次恢复来源归档 SHA-256</dt><dd>{value.sourceArchiveSha256}</dd><dt>导入时间</dt><dd>{value.importedUtc}</dd><dt>导入时文档摘要</dt><dd>{value.originalDocumentSha256}</dd><dt>当前文档摘要</dt><dd>{value.currentDocumentSha256}</dd></dl><p>这里只描述最近一次恢复，不认定最早来源。文档摘要为服务器规范化JSON标识，未在浏览器独立重算。历史回执不可重放，不能解除当前未知写入锁。</p></aside>:<p role="note">服务未返回此对象的本次恢复关联；这不是“从无历史”或真实性认证。</p>}
export function ArchiveProvenance({caseId,kind,recordId,revision,onDenied}:{caseId:string;kind:Kind;recordId:string;revision?:object;onDenied?:()=>void}){
 const version=useRef({value:revision,serial:0});if(version.current.value!==revision)version.current={value:revision,serial:version.current.serial+1}
 const who=useSyncExternalStore(onIdentityChange,contentIdentity,contentIdentity)
 return <Session key={JSON.stringify([caseId,kind,recordId,who,version.current.serial])} caseId={caseId} kind={kind} recordId={recordId} who={who} onDenied={onDenied}/>
}
function Session({caseId,kind,recordId,who,onDenied}:{caseId:string;kind:Kind;recordId:string;who:string;onDenied?:()=>void}){
 const [state,setState]=useState<{status:'loading'}|{status:'error'}|{status:'ready';value:Provenance|null}>({status:'loading'})
 useEffect(()=>{let active=true;const c=new AbortController()
 void contentRequest<unknown>(casePath('/archive-history/provenance/'+kind+'/'+encodeURIComponent(recordId),caseId),who,undefined,c.signal).then(v=>{const p=parseProvenance(v,caseId,kind,recordId);if(active&&who===contentIdentity())setState({status:'ready',value:p})}).catch(e=>{if(active&&who===contentIdentity()){setState({status:'error'});if(e instanceof ApiError&&e.status===403)onDenied?.()}})
 return()=>{active=false;c.abort()}
 },[caseId,kind,recordId,who])
 return state.status==='loading'?<p role="status">正在单独核对当前对象的恢复来源…</p>:state.status==='error'?<p role="alert">此对象恢复来源未能核验。权限拒绝、缺失或异常均不能推断为“没有历史”，也不能据此认定历史状态。</p>:<ProvenanceNote value={state.value}/>
}
