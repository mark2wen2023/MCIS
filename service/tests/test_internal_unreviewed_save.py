import copy
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from .conftest import C,CASE,H,make_settings
from .test_source_incarnation import fresh
from .test_registered_align_preview import register,request,RAW
from .test_unreviewed_preflight import result
from .test_archive_generation_boundary import upload
from .test_binding_review_independent import snapshot
from mcis_service.main import create_app
from mcis_service.timeline.evidence_preview import RegisteredPreview
from mcis_service.timeline import align_preview,unreviewed_storage as storage
from mcis_service.audit import service as audit
from mcis_service.audit.models import AuditEventRow

OP='40000000-0000-4000-8000-000000000001'

def ctx(client,operator='save-test',role='LeadInvestigator'):
    return SimpleNamespace(db=client.app.state.db,settings=client.app.state.settings,role=role,operator=operator)

def setup(client,empty_client,monkeypatch):
    target=fresh(client,empty_client);receipt=register(target)
    monkeypatch.setattr(align_preview,'core_run',lambda *args:result(args[2]))
    return target,receipt,RegisteredPreview.model_validate(request(receipt))

def save(target,body,**kwargs):return storage.save_unreviewed(ctx(target,**kwargs),CASE,body,OP)

def counts(target):
    with target.app.state.db.session() as s:
        return (s.scalar(select(func.count()).select_from(storage.UnreviewedRunRow)),
                s.scalar(select(func.count()).select_from(AuditEventRow).where(AuditEventRow.action=='timeline.unreviewed.save')))


def test_real_persistence_replay_and_history_roundtrip(client,empty_client,tmp_path,monkeypatch):
    target,r,body=setup(client,empty_client,monkeypatch)
    first=save(target,body);assert first['saved'] and not first['replayed']
    assert first['declaration']['processing']['coreImplementationVersionStatus']=='not_attested'
    monkeypatch.setattr(align_preview,'core_run',lambda *_:pytest.fail('replay must not recompute'))
    second=save(target,body);assert second['replayed'] and second['runId']==first['runId']
    assert counts(target)==(1,1)
    exported=target.get(C+'/export',headers=H('LeadInvestigator'));assert exported.status_code==200,exported.text
    with TestClient(create_app(make_settings(tmp_path/'restore',seed=False))) as restored:
        imported=upload(restored,exported.content);assert imported.status_code==200,imported.text
        assert counts(restored)==(0,1)
        again=restored.get(C+'/export',headers=H('LeadInvestigator'));assert again.status_code==200,again.text
        with restored.app.state.db.session() as s:
            events=audit.all_lines(s,CASE)
            assert any(storage.canonical(first['declaration']) in json.loads(x).get('snapshot_ref','') for x in events)
        # Old imported sources cannot activate operation replay.
        with pytest.raises(HTTPException):save(restored,body)
        # A newly acquired original belongs to the new local generation and may
        # use the same historical operation ID without restoring old authority.
        new=register(restored,RAW.replace(b',45',b',46'),filename='new.csv')
        monkeypatch.setattr(align_preview,'core_run',lambda *args:result(args[2]))
        newer=save(restored,RegisteredPreview.model_validate(request(new)))
        assert newer['runId']!=first['runId'] and not newer['replayed']
        assert counts(restored)==(1,2)


@pytest.mark.parametrize('change',['request','operator','bytes','review','permission'])
def test_replay_scope_or_current_state_change_refused(client,empty_client,monkeypatch,change):
    target,r,body=setup(client,empty_client,monkeypatch);save(target,body)
    kwargs={}
    if change=='request':body.sources[0].csvMapping.columns[0].kind='CourseOverGround'
    elif change=='operator':kwargs['operator']='another'
    elif change=='bytes':(target.app.state.settings.blob_dir/CASE/r['evidence']['relativePath']).write_bytes(b'changed')
    elif change=='review':assert target.patch(C+'/evidence/'+r['evidenceId'],headers=H(),json={'needsReview':True,'reason':'test'}).status_code==200
    else:
        from mcis_service.redaction.policy import default_policy
        policy=default_policy();policy['matrix']['LeadInvestigator']['timeline']='ReadOnly'
        assert target.put(C+'/access-policy',headers=H('LeadInvestigator'),json=policy).status_code==200
    monkeypatch.setattr(align_preview,'core_run',lambda *_:pytest.fail('must not recalculate'))
    with pytest.raises(HTTPException) as error:save(target,body,**kwargs)
    assert error.value.status_code==(403 if change=='permission' else 409)
    assert counts(target)==(1,1)


@pytest.mark.parametrize('damage',['missing_index','digest','audit_seq'])
def test_corrupted_index_never_repaired_or_replayed(client,empty_client,monkeypatch,damage):
    target,r,body=setup(client,empty_client,monkeypatch);saved=save(target,body)
    with target.app.state.db.session() as s:
        row=s.get(storage.UnreviewedRunRow,(CASE,saved['runId']))
        if damage=='missing_index':s.delete(row)
        elif damage=='digest':row.input_digest='0'*64
        else:row.audit_seq=1
    monkeypatch.setattr(align_preview,'core_run',lambda *_:pytest.fail('no repair/recompute'))
    with pytest.raises(HTTPException) as e:save(target,body)
    assert e.value.status_code==409
    exported=target.get(C+'/export',headers=H('LeadInvestigator'))
    assert exported.status_code==409,exported.text


@pytest.mark.parametrize('fault',['after_audit','index_flush','commit','capacity'])
def test_faults_rollback_audit_and_index(client,empty_client,monkeypatch,fault):
    target,r,body=setup(client,empty_client,monkeypatch);before=snapshot(target)
    with monkeypatch.context() as patch:
        if fault=='after_audit':
            real=audit.append
            def fail(*args,**kwargs):
                answer=real(*args,**kwargs)
                if kwargs.get('action')=='timeline.unreviewed.save':raise RuntimeError('audit failure')
                return answer
            patch.setattr(audit,'append',fail)
        elif fault=='index_flush':
            real=Session.flush
            def fail(self,*args,**kwargs):
                if any(isinstance(x,storage.UnreviewedRunRow) for x in self.new):raise RuntimeError('index failure')
                return real(self,*args,**kwargs)
            patch.setattr(Session,'flush',fail)
        elif fault=='commit':
            real=Session.commit
            def fail(self):
                if self.scalar(select(func.count()).select_from(storage.UnreviewedRunRow)):raise RuntimeError('commit failure')
                return real(self)
            patch.setattr(Session,'commit',fail)
        else:
            from mcis_service.timeline import unreviewed_access
            patch.setattr(unreviewed_access,'MAX_AUDIT_MEMBER_BYTES',1)
        with pytest.raises((RuntimeError,HTTPException)):save(target,body)
    assert snapshot(target)==before and counts(target)==(0,0)
    assert save(target,body)['saved']


@pytest.mark.parametrize('different',[False,True])
def test_concurrent_same_operation_has_one_winner(client,empty_client,monkeypatch,different):
    target,r,body=setup(client,empty_client,monkeypatch);barrier=threading.Barrier(2)
    def core(*args):barrier.wait(timeout=8);return result(args[2])
    monkeypatch.setattr(align_preview,'core_run',core)
    other=body.model_copy(deep=True)
    if different:other.sources[0].csvMapping.columns[0].kind='CourseOverGround'
    def worker(b):
        try:return save(target,b)
        except HTTPException as e:return e.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(worker,body);b=pool.submit(worker,other);answers=[a.result(15),b.result(15)]
    assert counts(target)==(1,1)
    if different:assert sum(x==409 for x in answers)==1
    else:
        assert answers[0]['runId']==answers[1]['runId']
        assert sorted(x['replayed'] for x in answers)==[False,True]


def test_unknown_delivery_same_operation_recovers_saved_run(client,empty_client,monkeypatch):
    target,r,body=setup(client,empty_client,monkeypatch)
    delivered=save(target,body) # simulate caller discarding committed response
    monkeypatch.setattr(align_preview,'core_run',lambda *_:pytest.fail('no repeated compute'))
    recovered=save(target,body)
    assert recovered['runId']==delivered['runId'] and recovered['replayed']
    assert counts(target)==(1,1)


@pytest.mark.parametrize('change',['bytes','review','permission'])
def test_midcompute_state_change_never_saves(client,empty_client,monkeypatch,change):
    target,r,body=setup(client,empty_client,monkeypatch)
    def core(*args):
        if change=='bytes':(target.app.state.settings.blob_dir/CASE/r['evidence']['relativePath']).write_bytes(b'changed')
        elif change=='review':assert target.patch(C+'/evidence/'+r['evidenceId'],headers=H(),json={'needsReview':True,'reason':'test'}).status_code==200
        else:
            from mcis_service.redaction.policy import default_policy
            policy=default_policy();policy['matrix']['LeadInvestigator']['timeline']='ReadOnly'
            assert target.put(C+'/access-policy',headers=H('LeadInvestigator'),json=policy).status_code==200
        return result(args[2])
    monkeypatch.setattr(align_preview,'core_run',core)
    with pytest.raises(HTTPException) as error:save(target,body)
    assert error.value.status_code==(403 if change=='permission' else 409)
    assert counts(target)==(0,0)


def test_save_uses_actual_w2_when_explicitly_configured(client,empty_client):
    import os
    command=os.getenv('MCIS_PREFLIGHT_REAL_CORE')
    if not command:pytest.skip('explicit real core required')
    target=fresh(client,empty_client);r=register(target);target.app.state.settings.core_cmd=command
    answer=save(target,RegisteredPreview.model_validate(request(r)))
    assert answer['declaration']['serverPreview']['result']['stats']['sourcesImported']==1
    assert counts(target)==(1,1)


def test_actor_identity_frozen_across_core_execution(client,empty_client,monkeypatch):
    target,r,body=setup(client,empty_client,monkeypatch);context=ctx(target)
    def core(*args):context.operator='changed';return result(args[2])
    monkeypatch.setattr(align_preview,'core_run',core)
    answer=storage.save_unreviewed(context,CASE,body,OP)
    with target.app.state.db.session() as s:
        row=s.scalars(select(AuditEventRow).where(AuditEventRow.entity_id==answer['runId'])).one()
        assert row.operator=='save-test'


@pytest.mark.parametrize('operator',['bad\u0085actor','bad\u2028actor','bad\u2029actor','bad\ud800actor'])
def test_operator_cannot_break_archive_lines(client,empty_client,monkeypatch,operator):
    target,r,body=setup(client,empty_client,monkeypatch);before=snapshot(target)
    monkeypatch.setattr(align_preview,'core_run',lambda *_:pytest.fail('reject before compute'))
    with pytest.raises(HTTPException) as error:save(target,body,operator=operator)
    assert error.value.status_code==422 and snapshot(target)==before
