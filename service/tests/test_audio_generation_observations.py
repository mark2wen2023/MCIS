"""New ordinary synthetic transaction tests; no real worker or safety probes."""
from sqlalchemy import select
from .test_audio_review_candidate import local, BASE
from .test_audio_sensevoice_tasks import configured
from mcis_service.audio_review import tasks, generation
from mcis_service.audio_review.app import create_audio_review_app, Revision
from mcis_service.audit.models import AuditEventRow
from mcis_service.common.csjson import sha256_utf8


def stored(app):
    with app.state.db.session() as s:
        gs=s.scalars(select(generation.Generation)).all()
        obs=s.scalars(select(generation.Observation).order_by(generation.Observation.ordinal)).all()
        for ob in obs:
            event=s.scalars(select(AuditEventRow).where(AuditEventRow.case_id==ob.case_id,AuditEventRow.seq==ob.doc['auditSeq'])).one()
            assert sha256_utf8(event.line)==ob.doc['auditLineSha256']
        return gs,obs


def test_success_records_observation_without_public_or_completion_claim(configured):
    c,app,settings,b,calls=configured
    r=c.post(BASE+'/audio-asr-tasks',json=b);assert r.status_code==201
    gs,obs=stored(app)
    assert len(gs)==1 and len(obs)==2 and calls==[b['taskId']]
    assert obs[0].doc['event']=='registration-recorded-before-dispatch'
    assert obs[1].doc['event']=='result-converted-and-source-rechecked'
    assert all(o.doc['writers']=='unknown' and o.doc['archiveReady'] is False for o in obs)
    with app.state.db.session() as s:assert r.json()==tasks.public_doc(s.get(tasks.Task,b['taskId']))
    assert 'generation' not in str(r.json()) and r.json()['archiveSupported'] is False
    reopened=create_audio_review_app(settings)
    assert len(stored(reopened)[1])==2


def test_exception_and_timeout_are_not_exit_proof(configured,monkeypatch):
    import subprocess
    c,app,_,b,calls=configured
    def fail(*args):calls.append('called');raise subprocess.TimeoutExpired('synthetic',120)
    monkeypatch.setattr(tasks,'execute',fail)
    assert c.post(BASE+'/audio-asr-tasks',json=b).status_code==409
    _,obs=stored(app)
    assert obs[1].doc['event']=='timeout-observed' and obs[1].doc['writers']=='unknown'
    assert calls==['called']


def test_observation_fault_rolls_back_final_state_and_audit(configured,monkeypatch):
    c,app,_,b,calls=configured;seen=[];original=generation.observe
    def fail(s,*args):
        original(s,*args);s.flush();seen.append(s.query(generation.Observation).count())
        raise RuntimeError('synthetic transaction failure after observation')
    monkeypatch.setattr(generation,'observe',fail)
    assert c.post(BASE+'/audio-asr-tasks',json=b).status_code==500
    assert seen==[2] and calls==[b['taskId']]
    assert len(stored(app)[1])==1
    with app.state.db.session() as s:
        assert s.get(tasks.Task,b['taskId']).doc['status']=='running_or_unknown'
        assert s.query(Revision).count()==0
        assert s.scalars(select(AuditEventRow).where(AuditEventRow.action=='asr.task.succeeded')).all()==[]


def test_existing_task_is_not_backfilled_on_reopen(local):
    _,app,settings=local
    with app.state.db.session() as s:
        s.add(tasks.Task(task_id='legacy-synthetic',case_id='synthetic-case',doc={'status':'failed'}))
    reopened=create_audio_review_app(settings)
    assert stored(reopened)==([],[])
    with reopened.state.db.session() as s:assert s.get(tasks.Task,'legacy-synthetic').doc=={'status':'failed'}


def test_ordinary_exception_preserves_incomplete_observation(configured,monkeypatch):
    c,app,_,b,calls=configured
    def fail(*args):calls.append('called');raise ValueError('synthetic conversion or execution failure')
    monkeypatch.setattr(tasks,'execute',fail)
    assert c.post(BASE+'/audio-asr-tasks',json=b).status_code==409
    _,obs=stored(app)
    assert obs[1].doc['event']=='execution-or-conversion-exception-observed'
    assert obs[1].doc['manifestStatus']=='not-captured' and calls==['called']


def test_registration_fault_does_not_dispatch_or_leave_partial_generation(configured,monkeypatch):
    c,app,_,b,calls=configured;seen=[];original=generation.register
    def fail(s,*args):
        result=original(s,*args);s.flush();seen.append(result)
        raise RuntimeError('synthetic failure after registration flush')
    monkeypatch.setattr(generation,'register',fail)
    assert c.post(BASE+'/audio-asr-tasks',json=b).status_code==500
    assert len(seen)==1 and calls==[] and stored(app)==([],[])
    with app.state.db.session() as s:
        assert s.get(tasks.Task,b['taskId']) is None
        assert s.scalars(select(AuditEventRow).where(AuditEventRow.action=='asr.task.start')).all()==[]
