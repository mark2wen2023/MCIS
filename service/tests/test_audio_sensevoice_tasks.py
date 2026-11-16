"""Ordinary synthetic task lifecycle tests; execution stub is NOT an ASR model."""
import hashlib,json,subprocess,io,wave
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from .test_audio_review_candidate import local,intake,tone,BASE,revision
from .test_audio_sensevoice_candidate import result
from mcis_service.audio_review import tasks
from mcis_service.audio_review.app import create_audio_review_app,Revision

@pytest.fixture
def configured(local,monkeypatch):
    c,app,settings=local;buf=io.BytesIO()
    with wave.open(buf,'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000);wav.writeframes(b'\0\0'*16000)
    audio=buf.getvalue();digest=intake(c,audio,'synthetic-task.wav')
    app.state.audio_asr_runtime=tasks.LocalRuntime(Path('/synthetic/python'),Path('/synthetic/model'))
    calls=[]
    source=c.get(BASE+'/audio-reviews/source/'+digest).json()['sampleSource']
    def fake(*args):calls.append(args[-1]);return result(source)
    monkeypatch.setattr(tasks,'execute',fake)
    return c,app,settings,{'taskId':'1'*32,'audioReceipt':digest,'confirmed':True},calls


def test_success_import_read_restart_and_no_redispatch(configured):
    c,app,settings,b,calls=configured;r=c.post(BASE+'/audio-asr-tasks',json=b);assert r.status_code==201,r.text
    task=r.json();assert task['status']=='succeeded' and task['asrExecutedByService'] is True
    assert 'raw' not in task and 'candidate' not in task
    url=BASE+'/audio-reviews/'+task['runId'];run=c.get(url);assert run.status_code==200 and run.json()['asrExecutedByService'] is True
    assert c.post(url+'/revisions',json=revision(segmentId='sv-1',startMs=None,endMs=None)).status_code==200
    for kind in ('raw','candidate'):
        out=c.post(BASE+'/audio-asr-tasks/'+b['taskId']+'/artifacts/'+kind+':download',json={'purpose':'synthetic lifecycle result check'})
        assert out.status_code==200 and hashlib.sha256(out.content).hexdigest()==task['artifacts'][kind]['sha256']
    assert c.post(BASE+'/audio-asr-tasks',json=b).status_code==409 and calls==[b['taskId']]
    with TestClient(create_audio_review_app(settings)) as restarted:
        assert restarted.get(BASE+'/audio-asr-tasks/'+b['taskId']).json()['status']=='succeeded'
        assert restarted.get(url).json()['revision']==1


def test_not_configured_does_not_dispatch(local):
    c,_,_=local;r=c.post(BASE+'/audio-asr-tasks',json={});assert r.status_code==503

@pytest.mark.parametrize('timeout',[False,True])
def test_failure_or_timeout_retains_status_and_no_retry(configured,monkeypatch,timeout):
    c,app,settings,b,calls=configured
    def fail(*args):calls.append('called');raise subprocess.TimeoutExpired('fixture',120) if timeout else ValueError('fixture')
    monkeypatch.setattr(tasks,'execute',fail)
    assert c.post(BASE+'/audio-asr-tasks',json=b).status_code==409
    assert c.get(BASE+'/audio-asr-tasks/'+b['taskId']).json()['status']==('interrupted_unknown' if timeout else 'failed')
    assert c.post(BASE+'/audio-asr-tasks',json=b).status_code==409 and calls==['called']
    if timeout:assert c.post(BASE+'/audio-asr-tasks',json={**b,'taskId':'2'*32}).status_code==409
    with app.state.db.session() as s:assert s.query(Revision).count()==0


def test_final_audit_failure_preserves_unknown_and_rolls_back_run(configured,monkeypatch):
    c,app,_,b,calls=configured;original=tasks.audit.append;seen=[]
    def inject(s,**kw):
        if kw['action']=='asr.task.succeeded':
            s.flush();seen.append(s.query(Revision).count());raise RuntimeError('synthetic final transaction fault')
        return original(s,**kw)
    monkeypatch.setattr(tasks.audit,'append',inject)
    with TestClient(app,raise_server_exceptions=False) as client:
        r=client.post(BASE+'/audio-asr-tasks',json=b);assert r.status_code==500 and seen==[1]
    assert c.get(BASE+'/audio-asr-tasks/'+b['taskId']).json()['status']=='running_or_unknown'
    assert c.post(BASE+'/audio-asr-tasks',json=b).status_code==409 and calls==[b['taskId']]
    with app.state.db.session() as s:assert s.query(Revision).count()==0


def test_running_status_is_readable_and_second_task_does_not_dispatch(configured,monkeypatch):
    from threading import Event
    from concurrent.futures import ThreadPoolExecutor
    c,app,_,b,calls=configured;entered=Event();release=Event();original=tasks.execute
    def blocked(*args):
        entered.set()
        if not release.wait(5):raise ValueError('synthetic test wait expired')
        return original(*args)
    monkeypatch.setattr(tasks,'execute',blocked)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending=pool.submit(c.post,BASE+'/audio-asr-tasks',json=b)
        try:
            assert entered.wait(5)
            assert c.get(BASE+'/audio-asr-tasks/'+b['taskId']).json()['status']=='running_or_unknown'
            assert c.post(BASE+'/audio-asr-tasks',json={**b,'taskId':'2'*32}).status_code==409
        finally:release.set()
        assert pending.result(timeout=5).status_code==201
    assert calls==[b['taskId']]


def test_other_supported_registration_is_not_fixed_demo_hash(configured):
    c,app,_,b,calls=configured
    # Fixture source is generated silence and is not the former public-demo SHA.
    r=c.post(BASE+'/audio-asr-tasks',json=b)
    assert r.status_code==201 and calls==[b['taskId']]


@pytest.mark.parametrize('rate,channels,width,seconds,extra',[(8000,1,2,1,False),(16000,2,2,1,False),(16000,1,3,1,False),(16000,1,2,31,False),(16000,1,2,1,True)])
def test_outside_worker_format_does_not_dispatch_or_create_task(configured,rate,channels,width,seconds,extra):
    c,app,_,b,calls=configured;buf=io.BytesIO()
    with wave.open(buf,'wb') as wav:
        wav.setnchannels(channels);wav.setsampwidth(width);wav.setframerate(rate);wav.writeframes(b'\0'*(rate*seconds*channels*width))
    audio=buf.getvalue()+(b'\0'*1048576 if extra else b'')
    receipt=intake(c,audio,'synthetic-outside-task-scope.wav')
    r=c.post(BASE+'/audio-asr-tasks',json={**b,'audioReceipt':receipt})
    assert r.status_code==422 and r.json()['code']=='ASR_WAV_SCOPE' and calls==[]
    with app.state.db.session() as s:assert s.query(tasks.Task).count()==0
    # Existing broader read/review format remains available, no destructive conversion.
    assert c.get(BASE+'/audio-reviews/source/'+receipt).status_code==200
