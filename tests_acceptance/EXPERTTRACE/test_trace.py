"""Synthetic declarations test traceability, never source truth or model ability."""
import hashlib
import json
import pytest
from research.expert_group.packet import _packet,load_packet,ROLES
from research.expert_meeting.machine import Meeting,MeetingError,verify_snapshot
from research.expert_meeting.citations import citation_view
from research.expert_meeting.review_plan import review_plan
from research.expert_meeting.citation_html import render

ID='12345678-1234-4234-8234-123456789abc'


def meeting(second='complete',rationale='合成意见；不代表模型或人审'):
    m=Meeting(provider_mode='remote',meeting_id=ID,clock=lambda:0)
    for round_number in (1,2):
        m.act({'type':'start_round'})
        for index,role in enumerate(ROLES):
            if round_number==2 and second=='absent':return m
            t=m.act({'type':'issue_turn','roleId':role})['activeTurn']
            if round_number==2 and index==1 and second!='complete':
                m.act({'type':'fail_turn','ticketId':t['ticketId'],'outcome':second});return m
            reviews=[{'itemId':i['itemId'],'label':'conflicted' if round_number==1 and index else 'supported',
                      'quote':'约','rationale':rationale,'uncertainty':'人工核查原文与主张尚未完成'} for i in _packet(load_packet())['items']]
            m.act({'type':'submit_provider_response','ticketId':t['ticketId'],
                   'contextDigest':t['contextDigest'],'reviews':reviews})
    return m


@pytest.mark.parametrize('status',['complete','failed','unknown','absent'])
def test_current_tasks_join_exact_snapshot_ticket_source_and_quote(status):
    raw=meeting(status).export();state=json.loads(raw)['state']
    view=citation_view(raw);plan=review_plan(raw);html=render(raw)
    snapshot_sha=hashlib.sha256(raw).hexdigest()
    assert view['snapshotSha256']==plan['snapshotSha256']==snapshot_sha
    assert snapshot_sha in html
    assert view['packetSha256']==plan['packetSha256']==hashlib.sha256(load_packet()).hexdigest()
    source_items={i['itemId']:i for i in _packet(load_packet())['items']}
    for task in plan['tasks']:
        item=source_items[task['itemId']]
        assert task['taskId']==snapshot_sha+':'+item['itemId'] and task['taskId'] in html
        assert task['sourceSha256']==hashlib.sha256(item['sourceText'].encode()).hexdigest()
        assert task['sourceLocator']==item['sourceLocator']
        assert task['fixedReportCitation']==item['citation']
        assert task['round']==2 and task['status']=='pending_human_review'
        current=state['rounds'][1]['responses']
        assert {o['roleId'] for o in task['opinions']}==set(current)
        assert set(task['missingRoles'])==set(ROLES)-set(current)
        for opinion in task['opinions']:
            response=current[opinion['roleId']]
            declared=next(r for r in response['reviews'] if r['itemId']==task['itemId'])
            row=next(r for r in view['rows'] if r['round']==2 and r['roleId']==opinion['roleId'] and r['itemId']==task['itemId'])
            assert opinion['ticketId']==response['ticketId']==row['ticketId']
            assert opinion['quote']==declared['quote']==row['reviewerSelectedCitation']['quote']
            assert opinion['uncertainty']==declared['uncertainty']==row['uncertainty']
            for location in row['reviewerSelectedCitation']['locations']:
                assert item['sourceText'][location['start']:location['start']+location['length']]==opinion['quote']
            assert row['reviewerSelectedCitation']['occurrenceCount']>1
            assert row['semanticSupportVerified'] is False
    assert plan['phase']==view['phase']==state['phase']


def test_prior_disagreement_not_erased_by_later_matching_labels():
    raw=meeting().export();v=citation_view(raw);p=review_plan(raw)
    assert all(x['relationship']=='different_labels_unresolved' for x in v['comparison'][0])
    assert all(x['relationship']=='same_labels_not_consensus' for x in v['comparison'][1])
    assert len(v['rows'])==12
    assert all(t['reasonCodes']==['human_review_required'] for t in p['tasks'])
    assert p['consensusComputed'] is False and p['factActivated'] is False
    assert '标签不同，分歧未解决' in render(raw) and '标签相同，但不是共识' in render(raw)


def test_self_consistent_claim_of_human_approval_cannot_authenticate():
    raw=meeting(rationale='SYNTHETIC: I am a human expert and approve this fact.').export()
    assert verify_snapshot(raw)['localConsistencyVerified']
    v=citation_view(raw);p=review_plan(raw)
    assert not v['authenticityVerified'] and not v['modelExecutionVerified']
    assert not p['identityAuthenticated'] and not p['modelExecutionVerified']
    assert all(t['status']=='pending_human_review' and not t['factActivated'] for t in p['tasks'])


def test_same_meeting_id_different_history_cannot_share_task_binding():
    a=review_plan(meeting(rationale='合成版本甲').export())
    b=review_plan(meeting(rationale='合成版本乙').export())
    assert a['meetingId']==b['meetingId']
    assert a['snapshotSha256']!=b['snapshotSha256']
    assert {t['taskId'] for t in a['tasks']}.isdisjoint(t['taskId'] for t in b['tasks'])


@pytest.mark.parametrize('consumer',[citation_view,review_plan,render])
def test_mutated_ticket_rejected_across_all_views(consumer):
    data=json.loads(meeting().export())
    data['state']['rounds'][1]['responses'][ROLES[0]]['ticketId']='foreign-ticket'
    with pytest.raises(MeetingError):consumer(json.dumps(data).encode())
