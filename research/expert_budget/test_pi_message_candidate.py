"""New ordinary synthetic protocol workflows, never a Pi/provider run."""
import json
import uuid
import pytest
from research.expert_budget.pi_message_adapter import SimulatedPiMessages
from research.expert_group.packet import _digest


def oid(): return str(uuid.uuid4())
def wire(value): return (json.dumps(value,ensure_ascii=False)+'\n').encode()
def setup(tmp_path): return SimulatedPiMessages(tmp_path/'synthetic.sqlite',oid(),oid())


def response(a,name,args,callid):
    request=a.from_runner(oid(),wire({'op':'model'}))
    msg={'role':'assistant','content':None,'tool_calls':[{'id':callid,'type':'function',
         'function':{'name':name,'arguments':json.dumps(args,ensure_ascii=False)}}]}
    returned=a.simulated_response(oid(),request['requestId'],wire(msg))
    return request,msg,returned


def read(a):
    response(a,'read_packet',{},'call1')
    return a.from_runner(oid(),wire({'op':'tool','id':'call1','name':'read_packet','args':{}}))


def test_model_request_and_response_digest_bind_to_ledger(tmp_path):
    a=setup(tmp_path); op=oid()
    request=a.from_runner(op,wire({'op':'model'}))
    msg={'role':'assistant','content':'SIMULATED response, not an expert opinion'}
    returned=a.simulated_response(oid(),request['requestId'],wire(msg))
    view=a.host.inspect()
    assert request['operationId']==op and request['ticketId']==a.ticket
    assert returned['receiptDigest']==_digest(msg)
    assert view['state']['turns'][0]['requests'][0]['receiptDigest']==_digest(msg)
    assert view['state']['turns'][0]['status']=='active'
    assert not returned['dispatchAllowed'] and not returned['executionVerified']


def test_read_packet_tool_uses_fixed_source_and_context(tmp_path):
    a=setup(tmp_path); result=read(a)
    assert result['result']['packet']==a.packet
    assert result['result']['contextDigest']==a.context_digest
    assert result['result']['meetingContext']['previousRoundOpinions']=={}
    assert not result['dispatchAllowed']


def test_review_tool_keeps_unverified_candidate_and_third_request_stops(tmp_path):
    a=setup(tmp_path); read(a)
    args={'reviews':[{'itemId':i['itemId'],'label':'insufficient','rationale':'SIMULATED',
                      'uncertainty':'SIMULATED; no model judgement','quote':i['citation']['quote']}
                     for i in a.packet['items']]}
    response(a,'validate_review',args,'call2')
    candidate=a.from_runner(oid(),wire({'op':'tool','id':'call2','name':'validate_review','args':args}))
    assert candidate['result']['status']=='validated_unverified'
    stopped=a.from_runner(oid(),wire({'op':'model'}))
    assert stopped['status']=='stopped' and a.blocked
    view=a.host.inspect()
    assert view['state']['stopReason']=='budget_exhausted'
    assert len(view['state']['turns'][0]['requests'])==2


def test_mismatched_tool_message_blocks_without_completion(tmp_path):
    a=setup(tmp_path); response(a,'read_packet',{},'call1')
    with pytest.raises(ValueError,match='tool_binding'):
        a.from_runner(oid(),wire({'op':'tool','id':'different','name':'read_packet','args':{}}))
    assert a.blocked and a.host.blocked
    assert a.host.inspect()['state']['turns'][0]['status']=='active'


def test_response_digest_never_accepts_done_by_itself(tmp_path):
    a=setup(tmp_path); r=a.from_runner(oid(),wire({'op':'model'}))
    a.simulated_response(oid(),r['requestId'],wire({'role':'assistant','content':'COMPLETED:synthetic'}))
    with pytest.raises(ValueError,match='completion_not_validated'):
        a.from_runner(oid(),wire({'op':'done','text':'COMPLETED:synthetic'}))
    assert a.host.inspect()['state']['turns'][0]['status']=='active'
