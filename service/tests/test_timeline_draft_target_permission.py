"""Target permission must be checked in the same review/write transaction."""
import pytest
from mcis_service.db import get_doc, put_doc
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from .conftest import C, CASE, H

PAYLOAD={'timeSec':610,'title':'权限回归（虚构）','kind':'Event'}


def make_draft(client):
    body={'agent':'timeline','kind':'timeline_anchor','targetEntityType':'timelineEvent',
          'payload':PAYLOAD,'citations':[{'evidenceId':'EV-003','quote':'AIS'}]}
    r=client.post(C+'/agents/drafts',json=body,headers=H('AgentService'))
    assert r.status_code==201,r.text
    return r.json()['draftId']


def set_timeline(client,role,level):
    with client.app.state.db.session() as s:
        policy=get_doc(s,AccessPolicyRow,CASE,'policy') or default_policy()
        policy['matrix'][role]['timeline']=level
        put_doc(s,AccessPolicyRow,CASE,'policy',policy)


@pytest.mark.parametrize('role',['Investigator','LeadInvestigator'])
@pytest.mark.parametrize('level',['ReadOnly','Redacted','Deny'])
@pytest.mark.parametrize('decision',['Confirmed','Modified'])
def test_review_cannot_bypass_target_write_permission(client,role,level,decision):
    did=make_draft(client)
    set_timeline(client,role,level)
    # Read snapshots before restriction via direct DB avoids privileging a role.
    from mcis_service.timeline.models import TimelineEventRow
    from mcis_service.audit.models import AuditEventRow
    from mcis_service.agents.models import AgentDraftRow
    from sqlalchemy import select,func
    with client.app.state.db.session() as s:
        before_events=s.scalar(select(func.count()).select_from(TimelineEventRow))
        before_audit=s.scalar(select(func.count()).select_from(AuditEventRow))
    body={'decision':decision}
    if decision=='Modified':body['payload']={**PAYLOAD,'title':'修改后的虚构事件'}
    r=client.post(C+'/agents/drafts/'+did+'/review',json=body,headers=H(role))
    assert r.status_code==403,r.text
    assert r.json()['code']==('FORBIDDEN' if level=='Deny' else 'READ_ONLY')
    with client.app.state.db.session() as s:
        assert get_doc(s,AgentDraftRow,CASE,did)['status']=='PendingReview'
        assert s.scalar(select(func.count()).select_from(TimelineEventRow))==before_events
        assert s.scalar(select(func.count()).select_from(AuditEventRow))==before_audit


def test_rejection_allowed_without_target_write_because_it_creates_no_event(client):
    did=make_draft(client);set_timeline(client,'Investigator','Deny')
    r=client.post(C+'/agents/drafts/'+did+'/review',json={'decision':'Rejected'},headers=H())
    assert r.status_code==200 and r.json()['status']=='Rejected'


@pytest.mark.parametrize('decision',['Confirmed','Modified'])
def test_authorized_review_preserves_existing_behavior(client,decision):
    did=make_draft(client)
    before=client.get(C+'/timeline',headers=H()).json()['events']
    body={'decision':decision}
    if decision=='Modified':body['payload']={**PAYLOAD,'title':'允许的修改（虚构）'}
    r=client.post(C+'/agents/drafts/'+did+'/review',json=body,headers=H())
    assert r.status_code==200 and r.json()['status']==decision
    after=client.get(C+'/timeline',headers=H()).json()['events']
    assert len(after)==len(before)+1
