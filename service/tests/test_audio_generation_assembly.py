"""New ordinary native synthetic member assembly tests, no real worker or safety probes."""
import json
from types import SimpleNamespace
import pytest
from sqlalchemy import select
from mcis_service.db import WRITE_LOCK, put_doc
from mcis_service.reports.access import begin
from mcis_service.audio_review import generation_assembly as assembly, tasks
from mcis_service.audio_review.generation import Generation, Observation
from mcis_service.recommendations.models import RecommendationRow
from .test_audio_review_candidate import local, BASE, CID, revision
from .test_audio_sensevoice_tasks import configured


def extract(app,settings):
    ctx=SimpleNamespace(role='LeadInvestigator',operator='Synthetic assembly',settings=settings,db=app.state.db)
    with WRITE_LOCK,app.state.db.session() as s:
        begin(s);return assembly.build_candidate(ctx,s,CID)


def start(configured):
    c,app,settings,b,calls=configured
    r=c.post(BASE+'/audio-asr-tasks',json=b);assert r.status_code==201,r.text
    return c,app,settings,b,calls,r.json()


def test_native_generation_observations_and_revisions_are_retained(configured):
    c,app,settings,b,calls,task=start(configured)
    for n in range(2):
        r=c.post(BASE+'/audio-reviews/'+task['runId']+'/revisions',json=revision(expectedRevision=n,segmentId='sv-1',text='synthetic '+str(n),startMs=None,endMs=None))
        assert r.status_code==200
    out=extract(app,settings);index=out['index'];payloads=out['payloads']
    assert len(index['generations'])==1 and len(index['observations'])==2
    with app.state.db.session() as s:
        g=s.scalars(select(Generation)).one()
        assert json.loads(payloads[index['generations'][0]])==dict(case_id=g.case_id,generation_id=g.generation_id,task_id=g.task_id,doc=g.doc)
        obs=s.scalars(select(Observation).order_by(Observation.ordinal)).all()
        assert [json.loads(payloads[x]) for x in index['observations']]==[dict(case_id=o.case_id,generation_id=o.generation_id,ordinal=o.ordinal,doc=o.doc) for o in obs]
    run=index['base']['runs'][0]
    assert [r['revision'] for r in run['revisions']]==[0,1,2]
    assert out['generationChecks']['archiveReady'] is False
    assert out['export_allowed'] is False and out['restore_ready'] is False and len(calls)==1
    assert out['checks']['source_bytes_match'] is True


def test_two_tasks_keep_all_histories_and_one_source_read(configured,monkeypatch):
    c,app,settings,b,calls,_=start(configured)
    assert c.post(BASE+'/audio-asr-tasks',json={**b,'taskId':'2'*32}).status_code==201
    seen=[];original=assembly.load_receipt
    def read(*args):seen.append(args[-1]);return original(*args)
    monkeypatch.setattr(assembly,'load_receipt',read)
    out=extract(app,settings)
    assert seen==[b['audioReceipt']]
    assert len(out['index']['generations'])==2 and len(out['index']['observations'])==4
    assert len(calls)==2


def test_missing_registered_member_refuses_component(configured,monkeypatch):
    _,app,settings,_,_,_=start(configured)
    monkeypatch.setattr(assembly,'load_receipt',lambda *args:None)
    with pytest.raises(ValueError,match='missing registered source'):extract(app,settings)


def test_unfinished_task_is_not_omitted_or_restarted(configured,monkeypatch):
    c,app,settings,b,calls=configured
    def fail(*args):calls.append('synthetic');raise ValueError('ordinary failure')
    monkeypatch.setattr(tasks,'execute',fail)
    assert c.post(BASE+'/audio-asr-tasks',json=b).status_code==409
    with pytest.raises(ValueError):extract(app,settings)
    assert calls==['synthetic']


def test_other_business_state_remains_unsupported(configured):
    _,app,settings,_,_,_=start(configured)
    with app.state.db.session() as s:put_doc(s,RecommendationRow,CID,'synthetic',{'title':'synthetic unsupported recommendation'})
    with pytest.raises(ValueError,match='unsupported case state'):extract(app,settings)


def test_legacy_task_without_generation_stays_unknown(local):
    _,app,settings=local
    with app.state.db.session() as s:
        s.add(tasks.Task(task_id='legacy-synthetic',case_id=CID,doc={'taskId':'legacy-synthetic','caseId':CID,'status':'failed','runId':None}))
    with pytest.raises(ValueError,match='legacy or lost history unknown'):extract(app,settings)
    with app.state.db.session() as s:
        assert s.query(Generation).count()==0 and s.query(Observation).count()==0
