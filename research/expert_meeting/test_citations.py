import json
import pytest
from research.expert_group.packet import _packet, load_packet, ROLES
from research.expert_meeting.machine import Meeting, MeetingError
from research.expert_meeting.citations import locate_quote, citation_view


def meeting(mode='scripted'):
    m=Meeting(provider_mode=mode);m.act({'type':'start_round'})
    t=m.act({'type':'issue_turn','roleId':ROLES[0]})['activeTurn']
    reviews=[dict(itemId=i['itemId'],label='supported',rationale='合成意见，非能力证据',uncertainty='未核实',quote='约') for i in _packet(load_packet())['items']]
    m.act(dict(type='submit_simulated' if mode=='scripted' else 'submit_provider_response',ticketId=t['ticketId'],contextDigest=t['contextDigest'],reviews=reviews))
    return m


@pytest.mark.parametrize('mode',['scripted','remote'])
def test_projection_never_promotes_supported_label_or_execution(mode):
    m=meeting(mode);m.act({'type':'stop'});raw=m.export();v=citation_view(raw)
    assert v['phase']=='stopped_by_operator' and len(v['rows'])==3
    assert v['sourceDocumentCount']==1 and not v['modelExecutionVerified']
    for row in v['rows']:
        assert row['declaredLabel']=='supported' and not row['semanticSupportVerified']
        assert row['claim']['kind']=='human_authored_test_claim_including_counterexamples'
        assert row['fixedReportCitation']['quote']!=row['reviewerSelectedCitation']['quote']
        assert row['reviewerSelectedCitation']['locationStatus']=='ambiguous_exact_matches'
        assert row['source']['locator']['pdfPage']==28
        assert not row['source']['publicnessVerified'] and not row['factActivated']
    assert not v['authenticityVerified'] and not v['consensusComputed']
    assert m.export()==raw and citation_view(raw)==v
    v['rows'][0]['source']['locator']['pdfPage']=0
    assert citation_view(raw)['rows'][0]['source']['locator']['pdfPage']==28


def test_exact_unicode_no_normalization():
    v=locate_quote('海🚢e\u0301中','🚢e\u0301')
    assert v['locations']==[{'start':1,'length':3}]
    with pytest.raises(MeetingError):locate_quote('e\u0301','é')


def test_overlapping_and_capped_locations():
    assert locate_quote('aaaa','aa')['occurrenceCount']==3
    v=locate_quote('a'*100,'a')
    assert len(v['locations'])==32 and v['occurrenceCount']==100 and v['locationsTruncated']


@pytest.mark.parametrize('quote',['', '  ', 'not in source',None,False,'a'*2001])
def test_invalid_quote(quote):
    with pytest.raises(MeetingError):locate_quote('abc',quote)


def test_snapshot_tamper_rejected_before_projection():
    m=meeting();data=json.loads(m.export());data['state']['rounds'][0]['responses'][ROLES[0]]['reviews'][0]['quote']='unbound'
    with pytest.raises(MeetingError):citation_view(json.dumps(data).encode())


def test_absent_opinions_not_fabricated():
    m=Meeting();v=citation_view(m.export())
    assert v['rows']==[] and v['phase']=='ready'
