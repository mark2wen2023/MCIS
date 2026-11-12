import {strict as assert} from 'node:assert'
import {parseQueue,interviewLink} from '../../web/src/agentOverview/model'
const d={caseId:'synthetic',draftId:'AD-001',agent:'people_ops',kind:'statement_extraction',targetEntityType:'interviewStatements',targetEntityId:'IR & /?',payload:{recordId:'IR & /?',secret:'NEVER_RENDER'},citations:[{quote:'NEVER_RENDER_QUOTE'}],status:'PendingReview',model:'synthetic'}
assert.equal(parseQueue([d],'synthetic')[0].citations,1)
assert(!JSON.stringify(parseQueue([d],'synthetic')).includes('NEVER_RENDER'))
for(const citation of [null,{},'quote',{quote:42},{quote:'x',round:0},{quote:'x',page:1.5},{quote:'x',recordId:32},{quote:'x',unexpected:true}])assert.throws(()=>parseQueue([{...d,citations:[citation]}],'synthetic'))
assert.throws(()=>parseQueue([d,{...d,draftId:'AD-002',citations:[null]}],'synthetic'))
assert.throws(()=>parseQueue([{...d,caseId:'OTHER'}],'synthetic'))
assert.throws(()=>parseQueue([d,d],'synthetic'))
assert.equal(interviewLink('c /?','IR & /?'),'/interview?case=c+%2F%3F&record=IR+%26+%2F%3F')
console.log('W203 independent metadata: citation shape, whole-batch reject, no payload projection, case/duplicate binding and encoded links passed')
