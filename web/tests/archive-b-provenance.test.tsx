import {strict as assert} from 'node:assert'
import {createElement} from 'react'
import {renderToStaticMarkup} from 'react-dom/server'
async function run(){
 Object.defineProperty(globalThis,'localStorage',{configurable:true,value:{getItem:()=>null,setItem:()=>{}}})
 const {parseProvenance,ProvenanceNote,unsupportedProvenance,UnsupportedProvenanceNote}=await import('../src/archiveProvenance/Provenance')
 const p={origin:'restored-history',sourceArchiveSha256:'a'.repeat(64),importedUtc:'2026-11-12T00:00:00Z',originalDocumentSha256:'b'.repeat(64),currentDocumentSha256:'b'.repeat(64),changedSinceImport:false}
 const envelope={caseId:'SYNTHETIC',kind:'interview',recordId:'IR-01',provenance:p}
 assert.deepEqual(parseProvenance(envelope,'SYNTHETIC','interview','IR-01'),p)
 assert.equal(parseProvenance({...envelope,provenance:null},'SYNTHETIC','interview','IR-01'),null)
 for(const v of [{...envelope,caseId:'OTHER'},{...envelope,kind:'report'},{...envelope,recordId:'IR-02'},{...envelope,provenance:{...p,changedSinceImport:true}},{...envelope,provenance:{...p,extra:true}}])assert.throws(()=>parseProvenance(v,'SYNTHETIC','interview','IR-01'))
 const html=renderToStaticMarkup(createElement(ProvenanceNote,{value:p as Parameters<typeof ProvenanceNote>[0]['value']}))
 for(const text of ['不是本次新签署或审核','最近一次恢复','未在浏览器独立重算','不能解除当前未知写入锁'])assert(html.includes(text))
 const changed=renderToStaticMarkup(createElement(ProvenanceNote,{value:{...p,currentDocumentSha256:'c'.repeat(64),changedSinceImport:true} as Parameters<typeof ProvenanceNote>[0]['value']}));assert(changed.includes('不把当前所有状态都称为历史状态'))
 assert(renderToStaticMarkup(createElement(ProvenanceNote,{value:null})).includes('不是“从无历史”'))
 const {ApiError}=await import('../src/api');assert(unsupportedProvenance(new ApiError(409,'ARCHIVE_HISTORY_UNSUPPORTED','',null)));assert(!unsupportedProvenance(new ApiError(409,'ARCHIVE_HISTORY_INTEGRITY','',null)));assert(!unsupportedProvenance(new ApiError(403,'ARCHIVE_HISTORY_UNSUPPORTED','',null)));const unsupported=renderToStaticMarkup(createElement(UnsupportedProvenanceNote));assert(unsupported.includes('未因此丢失或删除'));assert(unsupported.includes('保留原始包'));assert(unsupported.includes('不自动迁移或重新提交'));
 console.log('Archive B provenance:19 synthetic binding/render assertions passed')
}void run().catch(e=>{console.error(e);process.exitCode=1})
