import hashlib,json,socket
from copy import deepcopy
import pytest
from research.expert_group.packet import ROLES,_packet,load_packet
from research.expert_meeting.machine import Meeting,MeetingError
from research.expert_meeting import citations as c
@pytest.fixture(autouse=True)
def deny_network(monkeypatch):monkeypatch.setattr(socket.socket,'connect',lambda *a,**k:pytest.fail('network forbidden'))
def first():
    m=Meeting(provider_mode='remote');m.act({'type':'start_round'});t=m.act({'type':'issue_turn','roleId':ROLES[0]})['activeTurn']
    reviews=[dict(itemId=i['itemId'],label='supported',quote='约',rationale='<script>SYNTHETIC</script>',uncertainty='Not verified') for i in _packet(load_packet())['items']]
    m.act(dict(type='submit_provider_response',ticketId=t['ticketId'],contextDigest=t['contextDigest'],reviews=reviews));return m
@pytest.mark.parametrize('outcome',['failed','unknown','stop','deadline'])
def test_partial_terminal_preserves_only_accepted_unverified_reviews(outcome):
    m=first();t=m.act({'type':'issue_turn','roleId':ROLES[1]})['activeTurn']
    if outcome=='stop':m.act({'type':'stop'})
    elif outcome=='deadline':m._clock=lambda:m._started+600;m.act({'type':'tick'})
    else:m.act({'type':'fail_turn','ticketId':t['ticketId'],'outcome':outcome})
    raw=m.export();v=c.citation_view(raw)
    assert len(v['rows'])==3 and {r['roleId'] for r in v['rows']}=={ROLES[0]}
    assert v['phase']==m.snapshot()['phase'] and v['snapshotSha256']==hashlib.sha256(raw).hexdigest()
    for key in ['authenticityVerified','modelExecutionVerified','semanticSupportVerified','factActivated','consensusComputed']:assert v[key] is False
    assert v['sourceDocumentCount']==1
    for row in v['rows']:
        assert row['declaredLabel']=='supported' and row['semanticSupportVerified'] is False and row['reviewStatus']=='unverified'
        assert row['claim']['kind']=='human_authored_test_claim_including_counterexamples'
        assert row['rationale']=='<script>SYNTHETIC</script>' # data; UI must escape
        assert row['reviewerSelectedCitation']['quote']=='约' and row['fixedReportCitation']['quote']!='约'
        assert row['reviewerSelectedCitation']['locationStatus']=='ambiguous_exact_matches'
    assert m.export()==raw

@pytest.mark.parametrize('target',['contextDigest','ticketId','quote'])
def test_unbound_snapshot_rejected_before_source_projection(monkeypatch,target):
    obj=json.loads(first().export());response=obj['state']['rounds'][0]['responses'][ROLES[0]]
    if target=='quote':response['reviews'][0]['quote']='wrong'
    else:response[target]='wrong'
    monkeypatch.setattr(c,'load_packet',lambda:pytest.fail('projection packet read before verification'))
    with pytest.raises(MeetingError):c.citation_view(json.dumps(obj).encode())

def test_codepoints_not_utf16_or_bytes():
    source='🚢海🚢e\u0301尾';q='e\u0301';v=c.locate_quote(source,q)
    assert v['locations']==[{'start':3,'length':2}]
    assert len(source[:3].encode('utf-16-le'))//2==5
    assert v['offsetUnit']=='unicode_codepoints'
    with pytest.raises(MeetingError):c.locate_quote(source,'é')

@pytest.mark.parametrize('count',[32,33,12000])
def test_limit_all_occurrences_counted(count):
    v=c.locate_quote('a'*count,'a');assert v['occurrenceCount']==count and len(v['locations'])==min(count,32)
    assert v['locationsTruncated'] is (count>32)
    assert v['locations']==[{'start':i,'length':1} for i in range(min(count,32))]

def test_overlap_and_repeated_projection_independence():
    assert c.locate_quote('aaaaa','aaa')['locations']==[{'start':0,'length':3},{'start':1,'length':3},{'start':2,'length':3}]
    raw=first().export();one=c.citation_view(raw);before=deepcopy(one)
    one['rows'][0]['source']['locator']['url']='SYNTHETIC';one['rows'][0]['fixedReportCitation']['quote']='changed'
    assert c.citation_view(raw)==before
