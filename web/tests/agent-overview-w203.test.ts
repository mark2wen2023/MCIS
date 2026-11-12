import {strict as assert} from 'node:assert'
import {parseQueue,interviewLink,DRAFT_STATUS} from '../src/agentOverview/model'
import {navigationForCase,caseForLocation} from '../src/caseContext'
const d={draftId:'AD-001',caseId:'synthetic',agent:'people_ops',kind:'statement_extraction',targetEntityType:'interviewStatements',targetEntityId:'IR-01',payload:{recordId:'IR-01',secret:'Never render'},citations:[{quote:'synthetic'}],status:'PendingReview',model:'controlled-synthetic-not-inference',createdUtc:'2026-11-12T00:00:00Z'}
const out=parseQueue([d],'synthetic')[0]
assert.equal(out.recordId,'IR-01');assert(!('payload' in out));assert(!JSON.stringify(out).includes('Never render'))
assert.deepEqual(parseQueue([],'synthetic'),[])
for(const patch of [{caseId:'other'},{draftId:'bad'},{agent:'coordinator'},{kind:'task'},{status:'Running'},{payload:[]},{citations:[]},{model:'x\n'},{createdUtc:'bad'},{targetEntityId:'IR-02'}])assert.throws(()=>parseQueue([{...d,...patch}],'synthetic'))
assert.throws(()=>parseQueue([d,d],'synthetic'))
for(const status of Object.keys(DRAFT_STATUS))assert.equal(parseQueue([{...d,status}],'synthetic')[0].status,status)
assert.equal(parseQueue([{...d,targetEntityType:'statement'}],'synthetic')[0].recordId,null)
assert.equal(interviewLink('case & x','record/?'),'/interview?case=case+%26+x&record=record%2F%3F')
assert.equal(navigationForCase('agents','case & x','fallback'),'/agents?case=case%20%26%20x');assert.equal(caseForLocation('/agents','case=synthetic','fallback'),'synthetic')
console.log('W20.3 metadata projection/binding/status/no-payload and route-context guards passed')

for(const c of [null,{}, {quote:42},{quote:'q',evidenceId:'bad'},{quote:'q',round:0},{quote:'q',page:1.5},{quote:'q',recordId:3},{quote:'q',extra:true}])assert.throws(()=>parseQueue([{...d,citations:[c]}],'synthetic'))
assert.equal(parseQueue([{...d,citations:[{quote:'',evidenceId:'EV-001',recordId:'IR-01',round:1,page:2}]}],'synthetic')[0].citations,1)
