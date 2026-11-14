"""Independent W7.5 API/state safety checks with fictional temporary SQLite."""
import json
import sys
from pathlib import Path

import pytest
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'service'))
from tests.test_recommendation_body_edit import client, seeded_client, get, save, lines, RID, URL
from tests.test_recommendations import H
from tests.conftest import C, CASE
from mcis_service.audit import service as audit
from mcis_service.recommendations import body_edit
from mcis_service.recommendations.models import RecommendationRow
from mcis_service.db import get_doc, put_doc
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy


@pytest.mark.parametrize('change', [{'baseVersion':'invalid'}, {'before':'x'*20001}, {'causeNodeIds':[]}, {'after':'\ud800'}])
def test_malformed_recent_body_history_fails_closed(client, change):
    base=get(client)
    history={'schemaVersion':1,'status':body_edit.STATUS,'before':'old','after':'new','causeNodeIds':['N1'],'baseVersion':base['version'],**change}
    with client.app.state.db.session() as session:
        audit.append(session,case_id=CASE,operator='independent fictional test',role='LeadInvestigator',action=body_edit.ACTION,category='SafetyRec',command='malformed historical fixture',entity_type='recommendation',entity_id=RID,reason=json.dumps(history))
    before=lines(client)
    with client.app.state.db.session() as session:
        current=get_doc(session,RecommendationRow,CASE,RID)
        token=body_edit.version(session,current)
    attempted=client.put(URL,json={'expectedVersion':token,'body':'must not write'},headers=H())
    assert attempted.status_code==409, attempted.text[:300]
    with client.app.state.db.session() as session:
        assert get_doc(session,RecommendationRow,CASE,RID)==current
    assert lines(client)==before
    response=client.get(URL,headers=H())
    assert response.status_code==409, response.text[:300]
    assert response.json()['code']=='safetyrec_history_invalid'
    assert lines(client)==before


def test_21_versions_latest20_but_all_full_records_retained(client):
    base=get(client)
    for i in range(21):
        response=save(client,base,f'fictional version {i} '+('原文'*250))
        assert response.status_code==200
        base=response.json()
    assert len(base['versions'])==20
    assert base['versions'][0]['after'].startswith('fictional version 20 ')
    assert base['versions'][-1]['after'].startswith('fictional version 1 ')
    history=[json.loads(line) for line in lines(client) if json.loads(line)['action']==body_edit.ACTION]
    assert len(history)==21 and json.loads(history[0]['reason'])['before']=='旧正文'
    assert audit.verify_chain(lines(client))['valid']


def test_permission_revocation_hides_current_and_full_history(client):
    base=get(client);assert save(client,base,'private historical body').status_code==200
    policy=default_policy();policy['matrix']['LeadInvestigator']['evidence']='Deny'
    with client.app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',policy)
    before=lines(client)
    for method in ['get','put']:
        kwargs={'headers':H()}
        if method=='put':kwargs['json']={'expectedVersion':base['version'],'body':'attempt'}
        response=getattr(client,method)(URL,**kwargs)
        assert response.status_code==403 and 'private historical body' not in response.text
        assert response.headers['cache-control']=='no-store'
    assert before==lines(client)


def test_second_view_failure_after_audit_rolls_back_everything(client,monkeypatch):
    base=get(client);before=lines(client);real=body_edit.view;calls=0
    def fail_after_write(*args):
        nonlocal calls
        calls+=1
        if calls==2:raise RuntimeError('private sentinel')
        return real(*args)
    monkeypatch.setattr(body_edit,'view',fail_after_write)
    response=save(client,base,'candidate')
    assert response.status_code==500 and 'sentinel' not in response.text
    monkeypatch.setattr(body_edit,'view',real)
    assert get(client)==base and lines(client)==before


def test_noop_current_version_after_revocation_still_denied(client):
    base=get(client);policy=default_policy();policy['matrix']['LeadInvestigator']['recommendations']='ReadOnly'
    with client.app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',policy)
    before=lines(client)
    assert save(client,base,base['body']).status_code==403
    assert lines(client)==before


def test_unrelated_entity_audit_does_not_invalidate_token(client):
    base=get(client)
    with client.app.state.db.session() as session:
        audit.append(session,case_id=CASE,operator='test',role='LeadInvestigator',action='test.unrelated',category='Case',command='fictional unrelated',entity_type='case',entity_id=CASE)
    assert get(client)['version']==base['version']
    assert save(client,base,'new body').status_code==200


@pytest.mark.parametrize('kind', ['duplicate','nonfinite','oversize'])
def test_strict_history_parser_rejects_before_any_write(client,kind):
    base=get(client)
    history={'schemaVersion':1,'status':body_edit.STATUS,'before':'old','after':'new','causeNodeIds':['N1'],'baseVersion':base['version']}
    reason=json.dumps(history)
    if kind=='duplicate':reason=reason.replace('"schemaVersion": 1','"schemaVersion":1,"schemaVersion":1')
    if kind=='nonfinite':reason=reason.replace('"schemaVersion": 1','"schemaVersion":NaN')
    if kind=='oversize':reason=' '* (512*1024+1)+reason
    with client.app.state.db.session() as session:
        audit.append(session,case_id=CASE,operator='test',role='LeadInvestigator',action=body_edit.ACTION,category='SafetyRec',command='malformed historical fixture',entity_type='recommendation',entity_id=RID,reason=reason)
        doc=get_doc(session,RecommendationRow,CASE,RID);token=body_edit.version(session,doc)
    before=lines(client)
    assert client.get(URL,headers=H()).status_code==409
    assert client.put(URL,json={'expectedVersion':token,'body':'must not write'},headers=H()).status_code==409
    with client.app.state.db.session() as session:assert get_doc(session,RecommendationRow,CASE,RID)==doc
    assert lines(client)==before


@pytest.mark.parametrize('status',['Issued','Responded','Implemented','NotAdopted','Closed'])
def test_every_non_draft_state_rejects_even_with_current_token(client,status):
    with client.app.state.db.session() as session:
        rec=get_doc(session,RecommendationRow,CASE,RID);rec['status']=status;put_doc(session,RecommendationRow,CASE,RID,rec)
    base=get(client);before=lines(client)
    result=save(client,base,'must not change published body')
    assert result.status_code==409 and result.json()['code']=='safetyrec_not_draft'
    assert get(client)==base and lines(client)==before
