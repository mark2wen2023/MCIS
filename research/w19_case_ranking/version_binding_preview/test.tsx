import {strict as assert} from 'node:assert'
import {createElement} from 'react'
import {renderToStaticMarkup} from 'react-dom/server'
import {KnowledgeCard as Before} from 'w19-baseline-page'
import {KnowledgeCard as After} from '../../../web/src/pages/KnowledgePage'
import {VersionBindingPreview} from './Preview'
import {sample,type Card} from '../../../web/src/knowledge/model'
import fixed from '../version_binding/results.json'

let n=0
function check(name:string,fn:()=>void){fn();n++;console.log('PASS '+name)}
const render=(C:any,props:any)=>renderToStaticMarkup(createElement(C,props))
const noActions=(html:string)=>assert(!/<(?:a|button|input|form|textarea|select|script)\b|\shref=|\son\w+=/i.test(html))
for(const status of ['Candidate','Published','Rejected','Withdrawn'] as const)
 for(const publicSource of [false,true])for(const canReview of [false,true]){
 check('product SSR outside declared review entry preserved '+status+'/'+publicSource+'/'+canReview,()=>{
 const c:Card={cardId:'KC-'+'a'.repeat(32),status,content:structuredClone(sample),contentDigest:'b'.repeat(64),createdUtc:'2030-06-04T00:00:00Z',reviewedUtc:'2030-06-04T00:01:00Z',reviewedBy:'合成审核者',reviewNote:'仅合成属性'}
 c.content.title='<script>synthetic</script>'
 if(publicSource)c.content.source={...c.content.source,type:'Public',url:'https://example.invalid/synthetic'}
 const props={card:c,canReview,onReview:()=>{throw Error('SSR must not act')}}
 const after=render(After,props)
 const preserved=after.replace('<summary>进入待审核查（正文、出处与适用限制）</summary>','<summary>正文、出处与适用限制</summary>').replace(/<section aria-label="待审卡人工核查步骤">[\s\S]*?<\/section>/,'')
 assert.equal(preserved,render(Before,props))
 if(status==='Candidate'){
  assert(after.includes('进入待审核查')&&after.includes('待人工核查 · 未确认'))
  assert(!/<details[^>]*\sopen(?:[= >])/.test(after))
 }else assert(!after.includes('待审卡人工核查步骤'))
 })}
const html=render(VersionBindingPreview,{receipt:fixed})
check('three original states, no support upgrade',()=>{
 for(const s of ['LOCATED','SOURCE_VERSION_MISMATCH','BINDING_MISSING'])assert(html.includes(s))
 assert.equal((html.match(/支持未评估 · 因果未评估 · 待人工复核/g)||[]).length,3)
 assert(html.includes('当前合成字节定位一致')&&html.includes('旧版本拒绝')&&html.includes('缺少绑定'))
})
check('preview has no links, controls or credential fields',()=>{noActions(html);assert(!/createdUtc|reviewedBy|password|token|authorization/i.test(html))})
check('renders both exact fixed synthetic times',()=>{assert(html.includes('2030-06-04 00:01'));assert(html.includes('2030-06-03 23:58'))})
for(const [name,mutate] of [
 ['confirmed',(x:any)=>x.receipts[0].review='CONFIRMED'],
 ['supported',(x:any)=>x.receipts[0].support='SUPPORTED'],
 ['authenticated',(x:any)=>x.receipts[0].authenticatedReview=true],
 ['stale promoted',(x:any)=>x.receipts[1].traceability='LOCATED'],
 ['actionable source',(x:any)=>x.receipts[1].binding.url='https://example.invalid/stale'],
 ['identity mismatch',(x:any)=>x.receipts[0].cardId='OTHER'],
 ['missing receipt',(x:any)=>x.receipts.pop()],
] as const)check('reject '+name,()=>{
 const x=structuredClone(fixed);mutate(x)
 const h=render(VersionBindingPreview,{receipt:x})
 assert(h.includes('整份拒绝'));assert(!h.includes('source-records.txt'));noActions(h)
})
for(const value of [undefined,null])check('unconfigured clears displayed content '+String(value),()=>{
 const next=render(VersionBindingPreview,{receipt:value})
 assert(next.includes('未配置'));assert(!next.includes('SYN-CURRENT'));assert(!next.includes('00:01'));noActions(next)
})
check('replacement valid -> invalid -> valid has no retained source',()=>{
 const invalid=render(VersionBindingPreview,{receipt:{}})
 assert(!invalid.includes('2030-06-04'));assert.equal(render(VersionBindingPreview,{receipt:fixed}),html)
})
console.log('W19 shared presentation: '+n+' checks passed; SSR only')

for(const [id,task] of [
 ['SYN-CURRENT','核对定位摘录是否支持卡内陈述'],
 ['SYN-STALE','先核对 v1 与当前 v2 的时间及版本差异'],
 ['SYN-UNBOUND','先补齐原件版本、摘要和记录身份'],
])check('card-specific pending manual task '+id,()=>{
 const card=html.split('<article aria-label="'+id+'">')[1]?.split('</article>')[0]
 assert(card&&card.includes(task))
 assert(card.includes('核查尚未完成')&&card.includes('不是相似度评分'))
 assert(card.includes('待人工复核'));noActions(card)
})
console.log('W19 manual review tasks: total '+n+' SSR checks passed')

for(const canReview of [false,true])check('actual Candidate read-only entry '+canReview,()=>{
 const card:Card={cardId:'KC-'+'c'.repeat(32),status:'Candidate',content:structuredClone(sample),contentDigest:'d'.repeat(64),createdUtc:'2030-06-04T00:00:00Z'}
 const page=render(After,{card,canReview,onReview:()=>{throw Error('opening must not approve')}})
 const section=page.match(/<section aria-label="待审卡人工核查步骤">[\s\S]*?<\/section>/)?.[0]
 assert(section);noActions(section)
 assert(section.includes('不读取新原件')&&section.includes('不记录核查完成'))
 assert(page.includes(card.content.source.excerpt))
 assert.equal(page.includes('批准发布到公开资料库'),canReview)
})
console.log('W19 product entry: '+n+' SSR checks passed')
