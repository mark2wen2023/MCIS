import {strict as assert} from 'node:assert'
import {renderToStaticMarkup} from 'react-dom/server'
import {createElement} from 'react'
import {parseCard,parsePage,permissions,sample,utc,type Card} from '../src/knowledge/model'
let n=0;const ok=(x:unknown)=>{assert(x);n++};const bad=(fn:()=>unknown)=>{assert.throws(fn);n++}
const c:Card={cardId:'KC-'+'a'.repeat(32),status:'Candidate',content:structuredClone(sample),contentDigest:'b'.repeat(64),createdUtc:'2026-11-12T00:00:00Z'}
ok(parseCard(c).status==='Candidate');ok(utc(c.createdUtc).endsWith('UTC'))
for(const role of ['Public','AgentService','ExternalExpert','InterestedState'])ok(!permissions(role).internal&&!permissions(role).review)
ok(permissions('Investigator').internal&&!permissions('Investigator').review);ok(permissions('LeadInvestigator').review)
for(const x of [{...c,status:'Trusted'},{...c,contentDigest:'bad'},{...c,createdUtc:'bad'},{...c,content:{...c.content,source:{...c.content.source,type:'Private'}}},{...c,content:{...c.content,source:{...c.content.source,type:'Public',url:'javascript:evil()'}}}])bad(()=>parseCard(x))
bad(()=>parsePage({items:[c],total:1,limit:20,offset:0},'Published'));bad(()=>parsePage({items:[c,c],total:2,limit:20,offset:0},'Candidate'))
ok(parsePage({items:[c],total:1,limit:20,offset:0},'Candidate').items.length===1)
Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null}})
async function main(){const {KnowledgeCard}=await import('../src/pages/KnowledgePage');const d={...c,content:{...c.content,title:'<script>alert(1)</script>'}}
 const html=renderToStaticMarkup(createElement(KnowledgeCard,{card:d,canReview:true,onReview:()=>{throw Error('render writes')}}));ok(html.includes('&lt;script&gt;')&&!html.includes('<script>'));ok(html.includes('批准发布到公开资料库')&&html.includes('disabled'));ok(html.includes('合成样本，非真实事故'));ok(html.includes('使用权说明'));ok(html.includes('SHA-256'));ok(html.includes('我明确批准把这份内容向全部知识库角色公开'))
 const ro=renderToStaticMarkup(createElement(KnowledgeCard,{card:d,canReview:false,onReview:()=>{}}));ok(!ro.includes('批准发布到公开资料库'));ok(!ro.includes('驳回，不公开'));const api=await import('../src/knowledge/api');const win=Object.assign(new EventTarget(),{location:{hash:'#/knowledge',href:'http://127.0.0.1/#/knowledge'}});Object.defineProperty(globalThis,'window',{configurable:true,value:win});Object.defineProperty(globalThis,'document',{configurable:true,value:new EventTarget()});let notified=0;const off=api.subscribe(()=>notified++);const before=api.context();win.dispatchEvent(new Event('hashchange'));win.dispatchEvent(new Event('hashchange'));ok(api.context()!==before);ok(notified===2);const current=api.context();off();win.dispatchEvent(new Event('hashchange'));ok(api.context()===current);console.log(`W19.1 ${n} assertions passed`)}
void main().catch(e=>{console.error(e);process.exitCode=1})
