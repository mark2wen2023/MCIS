import assert from 'node:assert/strict'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { parseAgents, parseDraft, parseDrafts, roleAccess, agentStatus, utc, type Draft } from '../src/agents/model'
let count = 0
function ok(value: unknown, message: string) { assert.ok(value, message); count++ }
function throws(fn: () => unknown, message: string) { assert.throws(fn, undefined, message); count++ }
const caseId='CASE-W202-QA', recordId='IR-90'
const d: Draft={caseId, draftId:'AD-101', agent:'people_ops', kind:'statement_extraction', targetEntityType:'interviewStatements', targetEntityId:recordId,
 payload:{recordId,sourceDigest:'a'.repeat(64),statements:[{kind:'Observation',subject:'vessel.lookout',summary:'<script>literal</script>',claim:{valueType:'Occurrence',occurred:true},round:1,field:'Answer',quote:'发现目标船'}]},
 citations:[{recordId,round:1,quote:'发现目标船'}],model:'controlled-fake-not-real-model',status:'PendingReview',promptDigest:'b'.repeat(64),createdUtc:'2026-11-12T03:00:00Z'}
const agents=['ships','timeline','environment','people_ops','causes_ecfc','aggregate'].map(agent=>({agent,name:agent,status:agent==='people_ops'?'configured':'not_connected',model:agent==='people_ops'?'test':'none'}))
ok(parseAgents(agents).length===6,'six real registry rows')
ok(agentStatus(parseAgents(agents)[3]).includes('未验证'),'configured does not assert health')
throws(()=>parseAgents([]),'no fabricated defaults for missing registry')
throws(()=>parseAgents([...agents.slice(0,5),agents[0]]),'duplicate registry rejected')
throws(()=>parseAgents(agents.map(a=>({...a,status:'online'}))),'unknown status is not success')
ok(parseDraft(d,caseId,recordId).draftId==='AD-101','valid draft')
throws(()=>parseDraft(d,'other',recordId),'cross case rejected')
throws(()=>parseDraft(d,caseId,'IR-91'),'cross record rejected')
throws(()=>parseDraft({...d,citations:[]},caseId,recordId),'missing citations rejected')
throws(()=>parseDraft({...d,citations:[{recordId,round:2,quote:'发现目标船'}]},caseId,recordId),'wrong round rejected')
throws(()=>parseDraft({...d,status:'Success'},caseId,recordId),'unknown status rejected')
throws(()=>parseDraft({...d,createdUtc:'not a date'},caseId,recordId),'invalid dates rejected')
throws(()=>parseDrafts([d,{...d,caseId:'other'}],caseId,recordId),'whole queue rejects foreign case')
throws(()=>parseDrafts([d,d],caseId,recordId),'duplicate ids rejected')
ok(parseDrafts([d,{caseId,targetEntityType:'statement'}],caseId,recordId).length===1,'legacy draft not mistaken for managed result')
for(const role of ['ExternalExpert','InterestedState','Public'])ok(!roleAccess(role).read&&!roleAccess(role).review,'no private read for '+role)
ok(roleAccess('AgentService').read&&!roleAccess('AgentService').review,'agent cannot review')
ok(roleAccess('Investigator').review&&roleAccess('LeadInvestigator').review,'investigators review')
ok(utc(d.createdUtc).endsWith('UTC'),'timestamps explicit UTC')
async function main(){
 Object.defineProperty(globalThis,'localStorage',{configurable:true,value:{getItem:()=>null,setItem:()=>{}}})
 const { DraftReview }=await import('../src/agents/AgentReviewPanel')
 const html=renderToStaticMarkup(createElement(DraftReview,{draft:d,turns:[],canReview:true,onDecide:()=>{throw Error('render must not mutate')}}))
 ok(html.includes('&lt;script&gt;literal&lt;/script&gt;')&&!html.includes('<script>'),'untrusted summary escaped')
 ok(html.includes('发现目标船')&&html.includes('第 1 问')&&html.includes('回答'),'specific citation visible')
 ok(html.includes('确认以上陈述并写回')&&html.includes('disabled'),'unchecked / missing turn cannot confirm')
 ok(html.includes('原文足以支持该解读'),'semantic check not quote existence alone')
 const reviewed=renderToStaticMarkup(createElement(DraftReview,{draft:{...d,status:'Rejected'},turns:[],canReview:false,onDecide:()=>{}}))
 ok(reviewed.includes('已驳回，未写回')&&!reviewed.includes('确认以上陈述并写回'),'history read-only')
 const api=await import('../src/agents/api')
 const key=api.operationKey(caseId,recordId)
 ok(api.beginOperation(key),'first operation starts')
 ok(!api.beginOperation(key),'sync double-click blocked')
 api.setOperation(key,'unknown');ok(!api.beginOperation(key),'uncertain blocks resend')
 api.setOperation(key,'idle');ok(api.beginOperation(key),'explicit reconciliation unlocks')
 api.setOperation(key,'idle')
 const shared=await import('../src/api')
 ok(!api.uncertain(new shared.ApiError(409,'ALREADY_REVIEWED','',null)),'known conflict is definite')
 ok(!api.uncertain(new shared.ApiError(503,'MODEL_NOT_CONFIGURED','',null)),'unconfigured is not fake inference')
 ok(api.uncertain(new Error('network'))&&api.uncertain(new shared.ApiError(500,'UNKNOWN','',null)),'ambiguous write locked')
 ok(api.agentError(new shared.ApiError(409,'SOURCE_CHANGED','',null)).includes('不能确认旧草稿'),'source drift explained')
 console.log(`W20.2 frontend: ${count} assertions passed`)
}
void main().catch(e=>{console.error(e);process.exitCode=1})
