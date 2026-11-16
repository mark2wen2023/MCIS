"""Ordinary synthetic contract tests, no processes or write-refusal probes."""
import uuid
import pytest
from research.expert_budget.round_two_view import RoundTwoViewLedger, advance_view, expand_round_two
from research.expert_budget.four_seat_transcript import FourSeatTranscriptLedger, context_for
from research.expert_budget.ledger_v2 import inspect_v2, digest
from research.expert_budget.stable_protocol import ROLES, initial
from research.expert_group.packet import _packet, load_packet, _dump


def op(): return str(uuid.uuid4())

def fill(ledger):
    for role in ROLES:
        ticket = ledger.apply(op(), {'type':'context','context':context_for(role)})['recordedResult']['ticketId']
        reviews = [{'itemId':i['itemId'],'label':'insufficient','rationale':'Synthetic '+role,
                    'uncertainty':'Unverified','quote':i['citation']['quote'][:8]}
                   for i in _packet(load_packet())['items']]
        for n,(name,args) in enumerate([('read_packet',{}),('validate_review',{'reviews':reviews})],1):
            rid = ledger.apply(op(),{'type':'request','ticketId':ticket,'ordinal':n})['recordedResult']['requestId']
            call = {'id':f'tool{n}','name':name,'args':args}
            msg = {'role':'assistant','content':None,'tool_calls':[{'id':call['id'],'type':'function',
                'function':{'name':name,'arguments':_dump(args)}}]}
            ledger.apply(op(),{'type':'response','ticketId':ticket,'requestId':rid,'message':msg})
            result = ledger.apply(op(),{'type':'tool','ticketId':ticket,'requestId':rid,'call':call})
        ledger.apply(op(),{'type':'seal','ticketId':ticket,
                          'candidateDigest':result['recordedResult']['toolResult']['candidateDigest']})


def test_full_view_preserves_every_original_candidate(tmp_path):
    meeting = op(); path = tmp_path/'synthetic.sqlite'; ledger = RoundTwoViewLedger(path,meeting)
    fill(ledger); before = inspect_v2(path,meeting)['state']
    ledger.apply(op(),{'type':'bind_round_two_view'})
    expanded = expand_round_two(path,meeting); view = expanded['view']
    assert expanded['viewDigest'] == digest(view)
    assert [x['reference']['role'] for x in view['previousRoundOpinions']] == list(ROLES)
    for item in view['previousRoundOpinions']:
        ticket = item['reference']['ticketId']
        assert item['candidate'] == before['transcripts'][ticket]['candidate']
    after = inspect_v2(path,meeting)
    assert after['revision'] == 33 and sum(len(t['requests']) for t in after['state']['turns']) == 8
    assert after['state']['transcripts'] == before['transcripts']
    assert not expanded['dispatchAllowed'] and not expanded['restoreReady']


def test_pure_missing_first_round_and_client_content_rejected():
    state = initial(op())
    with pytest.raises(ValueError,match='first_round_not_ready'):
        advance_view(state,{'type':'bind_round_two_view'})
    with pytest.raises(ValueError,match='host_binding_no_client_content'):
        advance_view(state,{'type':'bind_round_two_view','opinions':[]})
    with pytest.raises(ValueError,match='transcript_size'):
        advance_view(state,{'type':'bind_round_two_view','opinions':'中'*700})


def test_view_only_forbids_further_round_actions_in_pure_reducer(tmp_path):
    meeting = op(); path = tmp_path/'synthetic.sqlite'; ledger = RoundTwoViewLedger(path,meeting)
    fill(ledger); ledger.apply(op(),{'type':'bind_round_two_view'})
    state = inspect_v2(path,meeting)['state']
    with pytest.raises(ValueError,match='view_only_no_more_operations'):
        advance_view(state,{'type':'context','context':context_for(ROLES[0])})
    with pytest.raises(ValueError,match='first_round_not_ready'):
        advance_view(state,{'type':'bind_round_two_view'})


def test_old_revision_and_unbound_new_revision_remain_unknown(tmp_path):
    meeting = op(); old = tmp_path/'old.sqlite'; fresh = tmp_path/'fresh.sqlite'
    FourSeatTranscriptLedger(old,meeting); RoundTwoViewLedger(fresh,meeting)
    assert expand_round_two(old,meeting)['status'] == 'unknown_or_legacy'
    result = expand_round_two(fresh,meeting)
    assert result['status'] == 'unknown_missing_or_inconsistent'
    assert 'view' not in result and not result['dispatchAllowed']
