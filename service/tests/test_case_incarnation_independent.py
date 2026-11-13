"""Independent incarnation binding tests; no saved-run authority asserted."""
from concurrent.futures import ThreadPoolExecutor
import threading
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from .conftest import C,CASE,H,make_settings
from .test_case_incarnation import identity
from .test_archive_generation_boundary import source,upload
from .test_registered_align_preview import request,URL
from mcis_service.main import create_app
from mcis_service.cases.incarnation import CaseIncarnationRow,current


def create(client,target,**extra):
    return target.post('/api/v1/cases',headers=H(),json={**client.get(C,headers=H()).json(),**extra})


def test_modern_working_archive_two_restores_never_activates_old_id(client,empty_client,tmp_path):
    receipt,original=source(client,empty_client);ids=[identity(empty_client)]
    for n in range(2):
        with TestClient(create_app(make_settings(tmp_path/str(n),seed=False))) as target:
            r=upload(target,original);assert r.status_code==200,r.text
            ids.append(identity(target));assert len(set(ids))==len(ids)
            r=target.post(URL,headers=H('LeadInvestigator'),json=request(receipt))
            assert r.status_code==409 and r.json()['code']=='ARCHIVE_HISTORY_ONLY'
            exported=target.get(C+'/export',headers=H('LeadInvestigator'));assert exported.status_code==200,exported.text
            original=exported.content


def test_metadata_route_keeps_identity(client,empty_client):
    assert create(client,empty_client).status_code==201;before=identity(empty_client)
    version=empty_client.get(C+'/metadata',headers=H()).json()['revision']
    r=empty_client.patch(C+'/metadata',headers=H(),json={'expectedRevision':version,'operationId':'review-independent-1','sourceLabel':'manual','changeReason':'title update','changes':{'title':'new title'}})
    assert r.status_code==200,r.text
    assert identity(empty_client)==before

@pytest.mark.parametrize('field,value',[('incarnation','00000000-0000-4000-8000-000000000000'),('localCaseIncarnation',{'approved':True})])
def test_caller_cannot_choose_identity(client,empty_client,field,value):
    response=create(client,empty_client,**{field:value})
    assert response.status_code==422,response.text
    with empty_client.app.state.db.session() as s:assert s.get(CaseIncarnationRow,CASE) is None

@pytest.mark.parametrize('field,value',[('audit_seq',999),('created_utc','2000-01-01T00:00:00Z'),('incarnation','not-a-uuid')])
def test_binding_corruption_rejects_read_and_export(client,empty_client,field,value):
    assert create(client,empty_client).status_code==201
    with empty_client.app.state.db.session() as s:setattr(s.get(CaseIncarnationRow,CASE),field,value)
    with pytest.raises(HTTPException) as e:identity(empty_client)
    assert e.value.detail['code']=='CASE_INCARNATION_INTEGRITY'
    assert empty_client.get(C+'/export',headers=H('LeadInvestigator')).status_code==409


def test_deleted_identity_does_not_backfill_or_use_audit_marker(client,empty_client):
    assert create(client,empty_client).status_code==201
    with empty_client.app.state.db.session() as s:s.delete(s.get(CaseIncarnationRow,CASE))
    with pytest.raises(HTTPException) as e:identity(empty_client)
    assert e.value.detail['code']=='CASE_INCARNATION_MISSING'
    with empty_client.app.state.db.session() as s:assert s.get(CaseIncarnationRow,CASE) is None


def test_parallel_create_one_identity_bound_to_winner(client,empty_client):
    body=client.get(C,headers=H()).json();barrier=threading.Barrier(3)
    def run(i):
        barrier.wait(timeout=5);return empty_client.post('/api/v1/cases',headers=H(),json={**body,'title':str(i)})
    with ThreadPoolExecutor(max_workers=3) as pool:responses=list(pool.map(run,range(3)))
    assert sorted(r.status_code for r in responses)==[201,409,409]
    before=identity(empty_client)
    with empty_client.app.state.db.session() as s:assert len(s.scalars(select(CaseIncarnationRow)).all())==1
    assert identity(empty_client)==before


def test_persist_failure_rolls_back_identity_case_audit(client,empty_client,monkeypatch):
    from mcis_service.cases import incarnation
    original=incarnation.persist;observed=[]
    def bad(s,value,event):
        original(s,value,event);observed.append(s.get(CaseIncarnationRow,CASE).incarnation)
        raise RuntimeError('after identity persisted')
    with monkeypatch.context() as patch:
        patch.setattr(incarnation,'persist',bad)
        try:
            r=create(client,empty_client);assert r.status_code==500
        except RuntimeError as e:assert str(e)=='after identity persisted'
    assert len(observed)==1
    from .test_case_create_independent import counts
    assert counts(empty_client)==(0,0)
    with empty_client.app.state.db.session() as s:assert s.get(CaseIncarnationRow,CASE) is None
    assert create(client,empty_client).status_code==201
    assert identity(empty_client)!=observed[0]


def test_audit_claim_alone_is_history_not_current_identity(client,empty_client,tmp_path):
    from mcis_service.db import put_doc
    from mcis_service.cases.models import CaseRow
    from mcis_service.cases.incarnation import marker
    from mcis_service.audit import service as audit
    body=client.get(C,headers=H()).json();claim='00000000-0000-4000-8000-000000000000'
    with empty_client.app.state.db.session() as s:
        put_doc(s,CaseRow,CASE,CASE,body)
        audit.append(s,case_id=CASE,operator='untrusted historical name',role='LeadInvestigator',action='case.create',category='Case',command='historical claim',entity_type='case',entity_id=CASE,snapshot_ref=marker({'version':1,'caseId':CASE,'incarnation':claim,'origin':'created','createdUtc':'2026-01-01T00:00:00Z'}))
    with pytest.raises(HTTPException) as e:identity(empty_client)
    assert e.value.detail['code']=='CASE_INCARNATION_MISSING'
    exported=empty_client.get(C+'/export',headers=H('LeadInvestigator'));assert exported.status_code==200,exported.text
    with TestClient(create_app(make_settings(tmp_path/'claim',seed=False))) as target:
        assert upload(target,exported.content).status_code==200
        assert identity(target)!=claim
        with target.app.state.db.session() as s:assert claim in '\n'.join(audit.all_lines(s,CASE))


def test_corruption_does_not_preempt_export_authorization(client,empty_client):
    assert create(client,empty_client).status_code==201
    from .test_registered_align_preview import register
    register(empty_client)
    assert empty_client.get(C+'/export',headers=H('Investigator')).status_code==403
    with empty_client.app.state.db.session() as s:s.get(CaseIncarnationRow,CASE).incarnation='corrupt'
    response=empty_client.get(C+'/export',headers=H('Investigator'))
    assert response.status_code==403,response.text
    assert response.json()['code']!='CASE_INCARNATION_INTEGRITY'
