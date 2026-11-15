/** Synthetic rendering/error mapping only; service acceptance is independent. */
import {strict as assert} from 'node:assert'
import {createElement} from 'react'
import {renderToStaticMarkup} from 'react-dom/server'
import {MemoryRouter} from 'react-router-dom'
async function run(){
 Object.defineProperty(globalThis,'localStorage',{configurable:true,value:{getItem:()=>null,setItem:()=>{}}})
 const {ApiError}=await import('../src/api');const {packageError}=await import('../src/packages/api')
 const msg=packageError(new ApiError(409,'ARCHIVE_RESTORE_UNSUPPORTED','private server detail',null))
 assert(msg.includes('整个案件包导出已拒绝'));assert(msg.includes('不会成功遗漏'));assert(msg.includes('重试不能解决'));assert(!msg.includes('private server detail'))
 assert(packageError(new ApiError(409,'INTERVIEW_RECEIPTS_BACKUP_UNSUPPORTED','',null)).includes('人工笔录请求回执'))
 const {PackageExport}=await import('../src/packages/PackagePanel')
 const html=renderToStaticMarkup(createElement(PackageExport,{caseId:'SYNTHETIC',title:'synthetic',who:'LeadInvestigator\nTest'}))
 assert(html.includes('不是完整案件备份'));assert(html.includes('未知模块、缺失依赖、预算超限整包拒绝'))
 const {InterviewPage}=await import('../src/pages/InterviewPage')
 const page=renderToStaticMarkup(createElement(MemoryRouter,{initialEntries:['/interview?case=SYNTHETIC']},createElement(InterviewPage)))
 assert(page.includes('笔录仅在匹配版本的受限归档全部校验通过时支持同案号新案恢复'));assert(page.includes('旧包校验成功不等于可以恢复笔录'))
 for(const rendered of [html,page]){
  for(const text of ['无航迹导入历史且无时间线时1.2.0','含航迹导入历史但无时间线时1.3.0','含时间线但无航迹导入历史时1.4.0','两者组合不支持','原始资料须独立保管'])assert(rendered.includes(text),text)
  for(const unsupported of ['1.2.0及以上','1.3.0及以上','1.4.0及以上'])assert(!rendered.includes(unsupported),unsupported)
 }
 assert(page.includes('未知内容整包拒绝'));assert(page.includes('过往签署与确认不代表本次认证'));assert(html.includes('历史回执不可重放'));assert(html.includes('过往确认不是本次审核'))
 console.log('Archive guard UI: 29 assertions passed (synthetic SSR)')
}void run().catch(e=>{console.error(e);process.exitCode=1})
