import {strict as assert} from 'node:assert'
import {parsePreview,parseReceipt,type Preview} from '../src/packageIntake/model'
import {renderToStaticMarkup} from 'react-dom/server'
Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null,setItem:()=>{}}})
async function main(){
 const base:Preview={profile:'MCIS-BASIC-INTAKE-1',packageVersion:'1.0.0',hfacsExtension:null,caseId:'SYNTHETIC',title:'Synthetic',sourceSha256:'a'.repeat(64),byteLength:12,counts:{},warnings:[]};parsePreview(base)
 const p:Preview={...base,packageVersion:'1.1.0',hfacsExtension:{version:'MCIS-HFACS-PACKAGE-1',draftCount:1,revisionCount:2,receiptCount:2,receiptMode:'archive-only',identityMode:'unverified-self-reported'}};parsePreview(p)
 for(const patch of [{packageVersion:undefined},{hfacsExtension:undefined},{packageVersion:'1.2.0'},{packageVersion:'1.0.0'},{hfacsExtension:{...p.hfacsExtension,receiptMode:'active'}},{hfacsExtension:{...p.hfacsExtension,identityMode:'verified'}},{hfacsExtension:{...p.hfacsExtension,revisionCount:1}},{hfacsExtension:{...p.hfacsExtension,draftCount:0}},{hfacsExtension:{...p.hfacsExtension,revisionCount:257,receiptCount:257}}])assert.throws(()=>parsePreview({...p,...patch}))
 const receipt={...p,importedUtc:'2026-11-12T00:00:00Z',replayed:false};parseReceipt(receipt,p);assert.throws(()=>parseReceipt({...receipt,hfacsExtension:{...p.hfacsExtension,revisionCount:3,receiptCount:3}},p));assert.throws(()=>parseReceipt({...receipt,packageVersion:'1.0.0',hfacsExtension:null},p))
 const {IntakeSummary,HfacsPackageSummary}=await import('../src/packageIntake/PackageIntakePanel');const summary=renderToStaticMarkup(<IntakeSummary preview={p}/>);for(const t of ['1.1.0','当前草稿数','全部修订数','历史请求回执数','archive-only','旧请求ID不能重放','未验证的自报身份','原请求摘要不能独立重算','256个完整修订及对应回执','超限整体拒绝，不截断历史','不是全系统备份'])assert.ok(summary.includes(t),t)
 assert.ok(renderToStaticMarkup(<HfacsPackageSummary extension={null}/>).includes('不含HFACS'))
 const {PackagePanel}=await import('../src/packages/PackagePanel');const {HfacsPanel}=await import('../src/hfacsDrafts/Panel')
 const html=renderToStaticMarkup(<PackagePanel who={'Investigator\n调查员 A'}/>);assert.ok(html.includes('不是完整案件备份'));assert.ok(html.includes('未知或不支持内容整包拒绝，不会成功遗漏'));assert.ok(!html.includes('完整案件包导出'));assert.ok(html.includes('256个完整修订及对应回执'));assert.ok(html.includes('超限整体拒绝，不截断历史'))
 const hf=renderToStaticMarkup(<HfacsPanel caseId="SYNTHETIC" who={'Investigator\n调查员 A'}/>);for(const label of ['.mcase 1.1.0','全部修订历史','回执只归档不激活','未保证识别或保留','不是全系统备份','默认权限','256个完整修订及对应回执','超限整体拒绝，不截断历史'])assert.ok(hf.includes(label),label);assert.ok(!hf.includes('尚未纳入案件包'))
 console.log('W18.6 package model/render/scope tests passed')
}
main().catch(e=>{console.error(e);process.exit(1)})
