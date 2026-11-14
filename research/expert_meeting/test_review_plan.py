import json
import pytest
from research.expert_group.packet import _packet,load_packet,ROLES
from research.expert_meeting.machine import Meeting,MeetingError
from research.expert_meeting.review_plan import review_plan
from research.expert_meeting.citation_html import render


def submit(m,role,label):
    t=m.act({'type':'issue_turn','roleId':role})['activeTurn']
    reviews=[dict(itemId=i['itemId'],label=label,quote='约',rationale='合成理由',uncertainty='仍有不确定性') for i in _packet(load_packet())['items']]
    m.act(dict(type='submit_provider_response',ticketId=t['ticketId'],contextDigest=t['contextDigest'],reviews=reviews))


def test_ready_tasks_are_pending_not_synthetic_answers():
    m=Meeting();plan=review_plan(m.export())
    assert len(plan['tasks'])==3 and plan['currentRound']==0
    for task in plan['tasks']:
        assert task['missingRoles']==list(ROLES) and not task['opinions']
        assert task['status']=='pending_human_review'
        assert task['reasonCodes']==['no_current_opinion','human_review_required']


def test_failed_partial_retains_absence_and_uncertainty():
    m=Meeting(provider_mode='remote');m.act({'type':'start_round'});submit(m,ROLES[0],'insufficient')
    t=m.act({'type':'issue_turn','roleId':ROLES[1]})['activeTurn']
    m.act({'type':'fail_turn','ticketId':t['ticketId'],'outcome':'unknown'})
    plan=review_plan(m.export());assert plan['phase']=='stopped_unknown'
    for task in plan['tasks']:
        assert task['missingRoles']==[ROLES[1]]
        assert task['reasonCodes']==['missing_role','declared_insufficient','human_review_required']
        assert task['opinions'][0]['uncertainty']=='仍有不确定性'


def test_new_round_does_not_reuse_previous_answers():
    m=Meeting(provider_mode='remote');m.act({'type':'start_round'})
    submit(m,ROLES[0],'supported');submit(m,ROLES[1],'conflicted')
    old=review_plan(m.export())
    assert all('different_labels' in t['reasonCodes'] for t in old['tasks'])
    m.act({'type':'start_round'});new=review_plan(m.export())
    assert new['currentRound']==2
    assert all(not t['opinions'] and t['missingRoles']==list(ROLES) for t in new['tasks'])
    assert set(t['taskId'] for t in old['tasks']).isdisjoint(t['taskId'] for t in new['tasks'])


def test_complete_same_labels_never_complete_human_review():
    m=Meeting(provider_mode='remote')
    for _ in range(2):
        m.act({'type':'start_round'})
        for role in ROLES:submit(m,role,'supported')
    raw=m.export();plan=review_plan(raw)
    assert plan['phase']=='completed_unverified' and plan['status']=='pending_human_review'
    assert all(t['reasonCodes']==['human_review_required'] and not t['factActivated'] for t in plan['tasks'])
    assert not plan['modelExecutionVerified'] and not plan['identityAuthenticated']
    assert review_plan(raw)==plan
    html=render(raw)
    assert '人工复核问题清单（全部待复核）' in html and '不等于已完成人工审查' in html
    assert '<input' not in html
    plan['tasks'][0]['sourceLocator']['pdfPage']=999
    assert review_plan(raw)['tasks'][0]['sourceLocator']['pdfPage']==28


def test_forged_snapshot_rejected():
    m=Meeting();raw=json.loads(m.export());raw['state']['phase']='completed_unverified'
    with pytest.raises(MeetingError):review_plan(json.dumps(raw).encode())
