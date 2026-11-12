"""Synthetic-only persistence, concurrency and access tests; no confirmed findings."""
import copy
import hashlib
import importlib
import json
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,func,update,delete,event
from sqlalchemy.exc import IntegrityError
from .conftest import H,make_settings
from mcis_service.main import create_app
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.evidence.models import EvidenceRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.hfacs_drafts.models import HfacsWorksheetRow,HfacsAuditRow,HfacsRequestRow

api=importlib.import_module('mcis_service.hfacs_drafts.router')
CASE='CASE-SYNTHETIC-HFACS'
BASE=f'/api/v1/cases/{CASE}/human-factors/hfacs:'


@pytest.fixture(scope='module')
def taxonomy(): return api.run_core({'action':'taxonomy'})


def body(code):
    return {'requestId':str(uuid.uuid4()),'expectedDigest':None,'draft':{'scope':'Synthetic task context',
        'entries':[{'id':'entry1','categoryCode':code,'description':'Hypothetical work condition','rationale':'Manual hypothesis, not confirmed'}]},'expectedSources':[]}


def source(db,case_id=CASE,**changes):
    doc=dict(evidenceId='EV-981',caseId=case_id,title='Synthetic supporting source',sha256='a'*64,confidentiality='Normal',source='private field')
    doc.update(changes)
    with db.session() as s: put_doc(s,EvidenceRow,case_id,doc['evidenceId'],doc)
    return {k:doc[k] for k in ('evidenceId','title','sha256')}


def policy(db,**changes):
    pol=default_policy()
    for key,value in changes.items(): pol['matrix']['Investigator'][key]=value
    with db.session() as s: put_doc(s,AccessPolicyRow,CASE,'policy',pol)


@pytest.fixture()
def env(tmp_path,taxonomy):
    app=create_app(make_settings(tmp_path,seed=False))
    with TestClient(app) as client:
        with app.state.db.session() as s: put_doc(s,CaseRow,CASE,CASE,{'caseId':CASE,'title':'Synthetic','isFictionalDemo':True})
        source(app.state.db)
        yield client,app.state.db,taxonomy['categories'][0]['code']


def counts(db):
    with db.session() as s: return tuple(s.scalar(select(func.count()).select_from(model)) for model in (HfacsWorksheetRow,HfacsAuditRow,HfacsRequestRow))


def test_real_context_and_empty_draft(env):
    client,db,code=env
    response=client.get(BASE+'context',headers=H()); assert response.status_code==200,response.text
    data=response.json(); assert len(data['categories'])==32 and data['taxonomyVersion']=='mcis-hfacs-project/1'
    assert data['writeAllowed'] is True and data['identityMode']=='local-role-header'
    assert response.headers['cache-control']=='no-store'
    result=client.get(BASE+'draft',headers=H()).json()
    assert result['document'] is None and result['persisted'] is False and result['sourceStatus']=='none'
    assert counts(db)==(0,0,0)


def test_save_reopen_update_atomic_audit_digest(env):
    client,db,code=env; payload=body(code); payload['expectedSources']=[source(db)]
    response=client.post(BASE+'save',json=payload,headers=H()); assert response.status_code==200,response.text
    first=response.json()['document']; assert first['revision']==1 and first['status']=='Draft' and first['strength']=='ToBeVerified'
    assert first['classification']['entries'][0]['categoryCode']==code
    assert first['classification']['entries'][0]['reviewStatus']=='Draft'
    expected={k:first[k] for k in ('caseId','revision','draft','sources','classification')}
    assert first['digest']==hashlib.sha256(api.canonical(expected)).hexdigest()
    assert client.get(BASE+'draft',headers=H()).json()['document']==first
    second=body(code);second['expectedDigest']=first['digest']; second['draft']['scope']='Changed synthetic scope'
    response=client.post(BASE+'save',json=second,headers=H()); assert response.status_code==200,response.text
    saved=response.json()['document']; assert saved['revision']==2
    assert counts(db)==(1,2,2)
    audit=client.get(BASE+'audit',headers=H()).json()['events']; assert [x['revision'] for x in audit]==[2,1]
    assert audit[0]['prevHash']==audit[1]['hash'] and audit[1]['prevHash']=='0'*64
    assert 'before' not in audit[0] and 'after' not in audit[0]
    with db.session() as s:
        rows=list(s.scalars(select(HfacsAuditRow).order_by(HfacsAuditRow.revision)))
        assert rows[1].doc['before']==first and rows[1].doc['after']==saved
        for row in rows:
            event_doc=dict(row.doc); stored=event_doc.pop('hash')
            assert stored==hashlib.sha256(api.canonical(event_doc)).hexdigest()


def test_retry_same_request_returns_original_without_core_or_duplicate_audit(env,monkeypatch):
    client,db,code=env; payload=body(code)
    first=client.post(BASE+'save',json=payload,headers=H()).json()
    def forbidden(_): raise AssertionError('retry must not recompute')
    monkeypatch.setattr(api,'run_core',forbidden)
    response=client.post(BASE+'save',json=payload,headers=H()); assert response.status_code==200 and response.json()==first
    assert counts(db)==(1,1,1)
    changed=copy.deepcopy(payload);changed['draft']['scope']='different'
    assert client.post(BASE+'save',json=changed,headers=H()).status_code==409
    assert client.post(BASE+'save',json=payload,headers=H(operator='other operator')).status_code==409
    assert counts(db)==(1,1,1)


def test_stale_updates_and_duplicate_creation_conflict(env):
    client,db,code=env; first=client.post(BASE+'save',json=body(code),headers=H()).json()['document']
    assert client.post(BASE+'save',json=body(code),headers=H()).status_code==409
    payload=body(code);payload['expectedDigest']='a'*64
    assert client.post(BASE+'save',json=payload,headers=H()).status_code==409
    assert counts(db)==(1,1,1)


@pytest.mark.parametrize('role',['Public','ExternalExpert','InterestedState','AgentService'])
def test_denial_no_case_details(env,role):
    client,_,_=env
    for suffix in ('context','draft','audit'):
        a=client.get(BASE+suffix,headers=H(role)); b=client.get((BASE+suffix).replace(CASE,'MISSING'),headers=H(role))
        assert a.status_code==b.status_code==403 and a.json()==b.json() and a.headers['cache-control']=='no-store'
    assert client.post(BASE+'save',content=b'bad',headers=H(role)).status_code==403


@pytest.mark.parametrize('category',['personal','evidence_meta','agent_drafts'])
@pytest.mark.parametrize('level',['Deny','Redacted',None])
def test_read_permission_gates(env,category,level):
    client,db,code=env; policy(db,**{category:level})
    for suffix in ('context','draft','audit'): assert client.get(BASE+suffix,headers=H()).status_code==403
    assert client.post(BASE+'save',json=body(code),headers=H()).status_code==403


def test_readonly_agent_draft_and_separate_audit_gate(env):
    client,db,code=env; policy(db,agent_drafts='ReadOnly',audit='Deny')
    assert client.get(BASE+'context',headers=H()).json()['writeAllowed'] is False
    assert client.get(BASE+'draft',headers=H()).status_code==200
    assert client.post(BASE+'save',json=body(code),headers=H()).status_code==403
    assert client.get(BASE+'audit',headers=H()).status_code==403


def test_source_changed_status_and_stale_selection_rejected(env):
    client,db,code=env; payload=body(code); payload['expectedSources']=[source(db)]
    first=client.post(BASE+'save',json=payload,headers=H()).json()['document']
    source(db,title='New metadata')
    got=client.get(BASE+'draft',headers=H()).json(); assert got['sourceStatus']=='changed' and got['document']==first
    assert client.post(BASE+'save',json=payload,headers=H()).status_code==409
    changed=body(code);changed['expectedDigest']=first['digest'];changed['expectedSources']=[source(db,title='New metadata')]
    assert client.post(BASE+'save',json=changed,headers=H()).status_code==200


def test_hidden_historical_sources_deny_draft_retry_and_audit(env):
    client,db,code=env; payload=body(code);payload['expectedSources']=[source(db)]
    first=client.post(BASE+'save',json=payload,headers=H()).json()['document']
    next_body=body(code);next_body['expectedDigest']=first['digest']
    assert client.post(BASE+'save',json=next_body,headers=H()).status_code==200
    source(db,confidentiality='Restricted');policy(db,testimony='Deny')
    # Current source-free worksheet is readable; history still references hidden sources.
    assert client.get(BASE+'draft',headers=H()).status_code==200
    assert client.get(BASE+'audit',headers=H()).status_code==403
    assert client.post(BASE+'save',json=payload,headers=H()).status_code==403


def test_missing_or_cross_case_sources_rejected(env):
    client,db,code=env; snap=source(db,'OTHER-CASE',evidenceId='EV-982'); payload=body(code);payload['expectedSources']=[snap]
    assert client.post(BASE+'save',json=payload,headers=H()).status_code==403
    assert counts(db)==(0,0,0)


@pytest.mark.parametrize('change,status',[('policy',409),('source',409),('revoke',403)])
def test_context_changes_while_cli_runs_no_write(env,monkeypatch,change,status):
    client,db,code=env; payload=body(code);payload['expectedSources']=[source(db)]; original=api.run_core
    def changed(command):
        output=original(command)
        if change=='source': source(db,title='changed')
        elif change=='revoke': policy(db,agent_drafts='ReadOnly')
        else: policy(db,audit='ReadWrite')
        return output
    monkeypatch.setattr(api,'run_core',changed)
    response=client.post(BASE+'save',json=payload,headers=H()); assert response.status_code==status,response.text
    assert counts(db)==(0,0,0)


def test_audit_failure_rolls_back_document_and_receipt(env,monkeypatch):
    client,db,code=env
    def broken(*args): raise RuntimeError('simulated audit failure')
    monkeypatch.setattr(api,'append_revision',broken)
    response=client.post(BASE+'save',json=body(code),headers=H()); assert response.status_code==503
    assert counts(db)==(0,0,0)


@pytest.mark.parametrize('model',[HfacsAuditRow,HfacsRequestRow])
def test_append_only_database_triggers(env,model):
    client,db,code=env; assert client.post(BASE+'save',json=body(code),headers=H()).status_code==200
    with pytest.raises(IntegrityError):
        with db.session() as s: s.execute(delete(model))
    with pytest.raises(IntegrityError):
        with db.session() as s:
            s.execute(update(model).values(**({'revision':9} if model is HfacsAuditRow else {'operator':'changed'})))
    assert counts(db)==(1,1,1)


def test_concurrent_same_request_one_revision(env):
    client,db,code=env; payload=body(code)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda _:client.post(BASE+'save',json=payload,headers=H()),range(2)))
    assert [r.status_code for r in responses]==[200,200]
    assert responses[0].json()==responses[1].json() and counts(db)==(1,1,1)


@pytest.mark.parametrize('mutation',['unknown','status','empty','duplicate_id','unknown_category','untrimmed','uuid','bad_digest','bad_source'])
def test_strict_input_and_core_taxonomy_rejection(env,mutation):
    client,db,code=env; payload=body(code)
    if mutation=='unknown': payload['x']=True
    elif mutation=='status': payload['draft']['entries'][0]['status']='Confirmed'
    elif mutation=='empty': payload['draft']['entries']=[]
    elif mutation=='duplicate_id': payload['draft']['entries']*=2
    elif mutation=='unknown_category': payload['draft']['entries'][0]['categoryCode']='FAKE_CATEGORY'
    elif mutation=='untrimmed': payload['draft']['scope']=' bad '
    elif mutation=='uuid': payload['requestId']='bad'
    elif mutation=='bad_digest': payload['expectedDigest']='x'
    else: payload['expectedSources']=[{'evidenceId':'bad','title':'x','sha256':'a'*64}]
    assert client.post(BASE+'save',json=payload,headers=H()).status_code==422
    assert counts(db)==(0,0,0)


@pytest.mark.parametrize('raw',[b'NaN',b'1e999',b'{"draft":1,"draft":2}',b'"\\ud800"'])
def test_strict_json(env,raw):
    client,db,_=env
    assert client.post(BASE+'save',content=raw,headers={**H(),'content-type':'application/json'}).status_code==422
    assert counts(db)==(0,0,0)


def test_content_type_size_and_cli_unavailable(env,monkeypatch,tmp_path):
    client,db,code=env
    assert client.post(BASE+'save',content=b'{}',headers=H()).status_code==415
    assert client.post(BASE+'save',content=b' '*(api.MAX_BYTES+1),headers={**H(),'content-type':'application/json'}).status_code==413
    monkeypatch.setattr(api,'CLI',tmp_path/'missing')
    assert client.post(BASE+'save',json=body(code),headers=H()).status_code==503
    assert counts(db)==(0,0,0)


def test_zero_source_saved_status_is_unchanged(env):
    client,db,code=env
    payload=body(code); response=client.post(BASE+'save',json=payload,headers=H())
    assert response.status_code==200 and response.json()['sourceStatus']=='unchanged'
    assert client.get(BASE+'draft',headers=H()).json()['sourceStatus']=='unchanged'
    assert client.post(BASE+'save',json=payload,headers=H()).json()==response.json()


def test_concurrent_distinct_requests_one_create_wins(env):
    client,db,code=env
    requests=[body(code),body(code)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda p:client.post(BASE+'save',json=p,headers=H()),requests))
    assert sorted(r.status_code for r in responses)==[200,409]
    assert counts(db)==(1,1,1)


def test_request_receipt_failure_rolls_back_already_flushed_audit(env):
    from sqlalchemy.orm import Session
    client,db,code=env
    def reject_receipt(session,flush_context,instances):
        if any(isinstance(row,HfacsRequestRow) for row in session.new): raise RuntimeError('synthetic receipt failure')
    event.listen(Session,'before_flush',reject_receipt)
    try: response=client.post(BASE+'save',json=body(code),headers=H())
    finally: event.remove(Session,'before_flush',reject_receipt)
    assert response.status_code==503 and counts(db)==(0,0,0)


def test_update_audit_failure_preserves_previous_document(env,monkeypatch):
    client,db,code=env
    first=client.post(BASE+'save',json=body(code),headers=H()).json()['document']
    payload=body(code); payload['expectedDigest']=first['digest'];payload['draft']['scope']='Updated'
    def broken(*args): raise RuntimeError('synthetic failure')
    monkeypatch.setattr(api,'append_revision',broken)
    assert client.post(BASE+'save',json=payload,headers=H()).status_code==503
    assert client.get(BASE+'draft',headers=H()).json()['document']==first and counts(db)==(1,1,1)


def test_read_endpoints_make_no_database_writes(env):
    client,db,code=env
    assert client.post(BASE+'save',json=body(code),headers=H()).status_code==200
    statements=[]
    def capture(conn,cursor,statement,parameters,context,executemany): statements.append(statement.strip().split()[0].upper())
    event.listen(db.engine,'before_cursor_execute',capture)
    try:
        for suffix in ('context','draft','audit'): assert client.get(BASE+suffix,headers=H()).status_code==200
    finally: event.remove(db.engine,'before_cursor_execute',capture)
    assert not {'INSERT','UPDATE','DELETE','REPLACE','CREATE','ALTER','DROP'}.intersection(statements)


def test_same_request_id_independent_across_cases(env):
    client,db,code=env; second='CASE-SYNTHETIC-SECOND'
    with db.session() as s: put_doc(s,CaseRow,second,second,{'caseId':second,'title':'Synthetic other','isFictionalDemo':True})
    payload=body(code)
    a=client.post(BASE+'save',json=payload,headers=H());b=client.post((BASE+'save').replace(CASE,second),json=payload,headers=H())
    assert a.status_code==b.status_code==200
    assert a.json()['document']['digest']!=b.json()['document']['digest']
    assert counts(db)==(2,2,2)
    assert all(e['afterDigest']==b.json()['document']['digest'] for e in client.get((BASE+'audit').replace(CASE,second),headers=H()).json()['events'])


def test_retry_old_request_returns_original_revision_after_later_save(env,monkeypatch):
    client,db,code=env; original=body(code)
    first=client.post(BASE+'save',json=original,headers=H()).json()
    second=body(code);second['expectedDigest']=first['document']['digest']
    assert client.post(BASE+'save',json=second,headers=H()).status_code==200
    def never(_): raise AssertionError('must use stored receipt')
    monkeypatch.setattr(api,'run_core',never)
    assert client.post(BASE+'save',json=original,headers=H()).json()==first
    assert counts(db)==(1,2,2)


def test_audit_returns_latest_fifty_summary_records(env,monkeypatch):
    client,db,code=env
    # Real core validates unchanged entries once; test double isolates pagination/transaction tests.
    payload=body(code); classified=api.run_core({'action':'validate','draft':payload['draft']})
    monkeypatch.setattr(api,'run_core',lambda _:copy.deepcopy(classified))
    expected=None
    for revision in range(1,53):
        payload=body(code);payload['expectedDigest']=expected;payload['draft']['scope']=f'Synthetic revision {revision}'
        response=client.post(BASE+'save',json=payload,headers=H());assert response.status_code==200,response.text
        expected=response.json()['document']['digest']
    response=client.get(BASE+'audit',headers=H());assert response.status_code==200
    events=response.json()['events']
    assert len(events)==50 and [e['revision'] for e in events]==list(range(52,2,-1))
    expected_keys={'revision','utc','operator','role','action','requestId','beforeDigest','afterDigest','prevHash','hash'}
    assert all(set(e)==expected_keys for e in events)
    assert counts(db)==(1,52,52)
