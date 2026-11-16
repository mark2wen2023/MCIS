"""New ordinary nodes only; actual candidate APIs, generated audio, stub recognizer.
No permission/write-refusal probes, paused nodes, real speech or model execution.
"""
from types import SimpleNamespace
import json
import pytest
from mcis_service.db import WRITE_LOCK, put_doc
from mcis_service.reports.access import begin
from mcis_service.audio_review import archive_candidate as adapter, tasks
from mcis_service.recommendations.models import RecommendationRow
from .test_audio_review_candidate import local, BASE, CID, revision, prepared
from .test_audio_sensevoice_tasks import configured


def extract(app,settings):
    ctx=SimpleNamespace(role='LeadInvestigator',operator='Synthetic archive',settings=settings,db=app.state.db)
    with WRITE_LOCK,app.state.db.session() as session:
        begin(session)
        return adapter.build_candidate(ctx,session,CID)


def start(configured):
    client,app,settings,body,calls=configured
    response=client.post(BASE+'/audio-asr-tasks',json=body)
    assert response.status_code==201,response.text
    return client,app,settings,body,calls,response.json()


def test_native_v3_revisions_raw_and_audit_are_preserved(configured):
    c,app,settings,_,calls,task=start(configured)
    url=BASE+'/audio-reviews/'+task['runId']
    for number,text in enumerate(('Synthetic first','Synthetic second')):
        response=c.post(url+'/revisions',json=revision(expectedRevision=number,segmentId='sv-1',text=text,startMs=None,endMs=None))
        assert response.status_code==200,response.text
    native=c.get(url).json();result=extract(app,settings);run=result['index']['runs'][0]
    assert [r['revision'] for r in run['revisions']]==[0,1,2]
    assert json.loads(result['payloads'][run['initialMember']])==native['initial']
    for entry,saved in zip(run['revisions'][1:],native['humanRevisions']):
        assert json.loads(result['payloads'][entry['member']])==saved
    assert json.loads(result['payloads'][run['rawMember']])==native['initial']['machineDraft']['recognizerResult']
    assert result['checks']['source_bytes_match'] is True
    assert result['export_allowed'] is False and result['restore_ready'] is False and len(calls)==1
    assert result['index']['tasks'][0]['executionPolicy']=='never'


def test_two_runs_share_single_registered_byte_read(configured,monkeypatch):
    c,app,settings,body,calls,_=start(configured)
    response=c.post(BASE+'/audio-asr-tasks',json={**body,'taskId':'2'*32});assert response.status_code==201
    original=adapter.load_receipt;seen=[]
    def counted(ctx,s,cid,digest):
        seen.append(digest);return original(ctx,s,cid,digest)
    monkeypatch.setattr(adapter,'load_receipt',counted)
    result=extract(app,settings)
    assert seen==[body['audioReceipt']] and len(result['index']['sources'])==1
    assert len(result['index']['runs'])==2 and len(calls)==2


def test_imported_v2_is_refused_without_inventing_raw_result(local):
    c,app,settings=local
    _,_,body=prepared(c);assert c.post(BASE+'/audio-reviews',json=body).status_code==201
    with pytest.raises(ValueError,match='local audio-v3'):extract(app,settings)


def test_failed_task_not_omitted_or_reexecuted(configured,monkeypatch):
    c,app,settings,body,calls=configured
    def failed(*args):calls.append('synthetic-failure');raise ValueError('synthetic worker failure')
    monkeypatch.setattr(tasks,'execute',failed)
    assert c.post(BASE+'/audio-asr-tasks',json=body).status_code==409
    with pytest.raises(ValueError):extract(app,settings)
    assert calls==['synthetic-failure']


def test_unsupported_business_record_blocks_component(configured):
    _,app,settings,_,_,_=start(configured)
    with app.state.db.session() as s:
        put_doc(s,RecommendationRow,CID,'SYNTHETIC',{'title':'Synthetic unsupported state'})
    with pytest.raises(ValueError,match='unsupported case state'):extract(app,settings)


def test_missing_receipt_result_refuses_no_partial_component(configured,monkeypatch):
    _,app,settings,_,_,_=start(configured)
    monkeypatch.setattr(adapter,'load_receipt',lambda *args:None)
    with pytest.raises(ValueError,match='missing registered source'):extract(app,settings)


def test_duplicate_matching_audit_is_ambiguous_not_guessed(configured):
    from sqlalchemy import select
    from mcis_service.audit.models import AuditEventRow
    from mcis_service.audit import service as audit
    _,app,settings,_,_,task=start(configured)
    # Append a second synthetic event via normal helper; no protected row is changed/deleted.
    with WRITE_LOCK,app.state.db.session() as s:
        begin(s)
        old=s.scalars(select(AuditEventRow).where(AuditEventRow.case_id==CID,AuditEventRow.action=='asr.task.succeeded')).one()
        audit.append(s,case_id=CID,operator=old.operator,role=old.role,action=old.action,
                     category=old.category,command=old.command,entity_id=old.entity_id)
    with pytest.raises(ValueError,match='ambiguous'):extract(app,settings)


def test_unknown_task_is_retained_without_dispatch(configured,monkeypatch):
    import subprocess
    c,app,settings,body,calls=configured
    def timeout(*args):calls.append('synthetic-timeout');raise subprocess.TimeoutExpired('synthetic',120)
    monkeypatch.setattr(tasks,'execute',timeout)
    assert c.post(BASE+'/audio-asr-tasks',json=body).status_code==409
    with pytest.raises(ValueError):extract(app,settings)
    status=c.get(BASE+'/audio-asr-tasks/'+body['taskId']).json()
    assert status['status']=='interrupted_unknown' and calls==['synthetic-timeout']


def test_extraction_reuses_session_and_leaves_audit_unchanged(configured,monkeypatch):
    from sqlalchemy import select
    from mcis_service.audit.models import AuditEventRow
    _,app,settings,_,_,_=start(configured)
    ctx=SimpleNamespace(role='LeadInvestigator',operator='Synthetic archive',settings=settings,db=app.state.db)
    original=adapter.load_receipt;seen=[]
    with WRITE_LOCK,app.state.db.session() as s:
        begin(s)
        before=[(r.seq,r.line) for r in s.scalars(select(AuditEventRow).where(AuditEventRow.case_id==CID).order_by(AuditEventRow.seq))]
        def same_session(context,session,cid,digest):
            seen.append(session is s)
            return original(context,session,cid,digest)
        monkeypatch.setattr(adapter,'load_receipt',same_session)
        adapter.build_candidate(ctx,s,CID)
        after=[(r.seq,r.line) for r in s.scalars(select(AuditEventRow).where(AuditEventRow.case_id==CID).order_by(AuditEventRow.seq))]
        assert before==after and seen==[True]
