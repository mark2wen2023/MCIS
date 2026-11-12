/** Synthetic transport boundaries, not backend acceptance. */
import {strict as assert} from 'node:assert'
import {createReportApi} from '../src/reports/api'
async function run(){
 let active=true, options:RequestInit|undefined
 const api=createReportApi({role:'LeadInvestigator',operator:'synthetic'},()=>active)
 globalThis.fetch=async (_,init)=>{options=init;return Response.json({caseId:'CASE-A',reports:[]})}
 await api.list('CASE-A');assert.equal(options?.cache,'no-store');assert.equal((options?.headers as Record<string,string>)['X-MCIS-Role'],'LeadInvestigator')
 for(const body of [{caseId:'OTHER',reports:[]},{reports:[]},{caseId:'CASE-A',reports:[{caseId:'OTHER'}]}]){globalThis.fetch=async()=>Response.json(body);await assert.rejects(api.list('CASE-A'))}
 globalThis.fetch=async()=>Response.json({caseId:'CASE-A',reportId:'OTHER'});await assert.rejects(api.get('CASE-A','R1'))
 for(const reportId of [null,'OTHER']){globalThis.fetch=async()=>Response.json([{reportId}]);await assert.rejects(api.audit('CASE-A','R1'))}
 globalThis.fetch=async()=>({ok:true,json:async()=>{active=false;return {caseId:'CASE-A',reports:[]}}}) as Response
 await assert.rejects(api.list('CASE-A'),{name:'AbortError'})
 active=true
 globalThis.fetch=async()=>({ok:true,headers:new Headers(),blob:async()=>{active=false;return new Blob(['synthetic'])}}) as Response
 await assert.rejects(api.export('CASE-A','R1','pdf','zh'),{name:'AbortError'})
 active=true
 globalThis.fetch=async()=>({ok:false,status:403,json:async()=>{active=false;return {code:'FORBIDDEN'}}}) as Response
 await assert.rejects(api.list('CASE-A'),{name:'AbortError'})
 console.log('W16.2 fixed identity, no-store, case/report/audit binding, stale JSON/error/blob suppression passed (synthetic)')
}void run().catch(e=>{console.error(e);process.exitCode=1})
