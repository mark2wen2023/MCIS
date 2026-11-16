"""Ordinary task workflow; fixtures simulated unless explicit real public run enabled."""
import json,os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from mcis_service.image_review import tasks
from mcis_service.image_review.app import create_image_review_app,Record
from .conftest import H
from .test_image_review_candidate import new_app,intake,BASE,CID,edit,digest


def request_body(c,pdf=b'public-fixture-pdf',image=b'public-fixture-image'):
    return {'taskId':'1'*32,'confirmed':True,'bindings':{'pdf':intake(c,pdf,'report.pdf'),'image':intake(c,image,'page.png')}}

@pytest.fixture
def simulated(tmp_path,monkeypatch):
    app,settings=new_app(tmp_path);app.state.image_ocr_runtime=tasks.LocalRuntime(Path('/not-executed'),Path('/not-executed'),Path('/not-executed'))
    monkeypatch.setattr(tasks,'PDF_SHA',digest(b'public-fixture-pdf'));monkeypatch.setattr(tasks,'IMAGE_SHA',digest(b'public-fixture-image'))
    calls=[]
    raw=json.dumps({'page_index':None,'rec_texts':['synthetic 22'],'rec_scores':[.9],'rec_boxes':[[1,2,30,20]],'rec_polys':[[[1,2],[30,2],[30,20],[1,20]]]}).encode()
    def execute(*args):
        calls.append(1)
        return raw,{'versions':{'paddlepaddle':'synthetic','paddleocr':'synthetic','paddlex':'synthetic'},'device':'cpu','raw_sha256':digest(raw)}
    monkeypatch.setattr(tasks,'execute',execute)
    return app,settings,calls,raw


def test_no_runtime_does_not_claim_execution(tmp_path):
    app,_=new_app(tmp_path)
    with TestClient(app) as c:
        r=c.post(BASE+'/image-ocr-tasks',json={});assert r.status_code==503
        with app.state.db.session() as s:assert s.query(tasks.Task).count()==0


def test_simulated_success_persists_artifacts_and_reviews(simulated):
    app,settings,calls,raw=simulated
    with TestClient(app) as c:
        body=request_body(c);r=c.post(BASE+'/image-ocr-tasks',json=body);assert r.status_code==201,r.text
        d=r.json();assert d['status']=='succeeded' and 'rawBase64' not in d
        assert len(calls)==1
        duplicate=c.post(BASE+'/image-ocr-tasks',json=body);assert duplicate.status_code==409 and len(calls)==1
        run=c.get(BASE+'/image-reviews/'+d['runId']);assert run.status_code==200,run.text
        assert run.json()['initial']['mode']=='local-ocr-task'
        assert edit(c,d['runId'],word='synthetic manual correction').status_code==200
        artifact=c.post(BASE+'/image-ocr-tasks/'+body['taskId']+'/artifacts/raw:download',json={'purpose':'ordinary result review'})
        assert artifact.status_code==200 and artifact.content==raw and artifact.headers['X-Sha256']==digest(raw)
        exported=c.get(BASE+'/export',headers=H('LeadInvestigator'))
        assert exported.status_code==409 and 'application/zip' not in exported.headers.get('content-type','')
    with TestClient(create_image_review_app(settings)) as c:
        assert c.get(BASE+'/image-ocr-tasks/'+body['taskId']).json()['status']=='succeeded'
        listing=c.get(BASE+'/image-ocr-tasks');assert listing.status_code==200
        assert listing.json()[0]['taskId']==body['taskId'] and listing.json()[0]['status']=='succeeded'
        assert c.get(BASE+'/image-reviews/'+d['runId']).json()['reviews'][0]['text']=='synthetic manual correction'


def test_worker_failure_never_automatically_retries(simulated,monkeypatch):
    app,_,calls,_=simulated
    def fail(*args):calls.append(1);raise ValueError('synthetic worker failure')
    monkeypatch.setattr(tasks,'execute',fail)
    with TestClient(app) as c:
        body=request_body(c);r=c.post(BASE+'/image-ocr-tasks',json=body);assert r.status_code==409
        status=c.get(BASE+'/image-ocr-tasks/'+body['taskId']).json();assert status['status']=='failed' and status['runId'] is None
        assert c.post(BASE+'/image-ocr-tasks',json=body).status_code==409 and len(calls)==1
        with app.state.db.session() as s:assert s.query(Record).count()==0


def test_finalization_failure_remains_unknown(simulated,monkeypatch):
    app,_,_,_=simulated;original=tasks.audit.append;reached=[]
    def fail(s,**kwargs):
        if kwargs['action']=='ocr.task.succeeded':
            s.flush();reached.append(s.query(Record).count());raise RuntimeError('synthetic before-commit failure')
        return original(s,**kwargs)
    monkeypatch.setattr(tasks.audit,'append',fail)
    with TestClient(app,raise_server_exceptions=False) as c:
        body=request_body(c);assert c.post(BASE+'/image-ocr-tasks',json=body).status_code==500
        assert reached==[1]
        assert c.get(BASE+'/image-ocr-tasks/'+body['taskId']).json()['status']=='running_or_unknown'
        with app.state.db.session() as s:assert s.query(Record).count()==0
        assert c.post(BASE+'/image-ocr-tasks',json={**body,'taskId':'2'*32}).status_code==409


def test_timeout_is_unknown_not_safe_to_restart(simulated,monkeypatch):
    import subprocess
    app,_,_,_=simulated
    monkeypatch.setattr(tasks,'execute',lambda *args:(_ for _ in ()).throw(subprocess.TimeoutExpired('synthetic',120)))
    with TestClient(app) as c:
        body=request_body(c);assert c.post(BASE+'/image-ocr-tasks',json=body).status_code==409
        assert c.get(BASE+'/image-ocr-tasks/'+body['taskId']).json()['status']=='interrupted_unknown'
        assert c.post(BASE+'/image-ocr-tasks',json={**body,'taskId':'2'*32}).status_code==409


def test_real_public_task(tmp_path):
    if os.environ.get('MCIS_RUN_REAL_PUBLIC_OCR')!='1':pytest.skip('explicit opt-in real local OCR required')
    app,_=new_app(tmp_path)
    app.state.image_ocr_runtime=tasks.LocalRuntime(Path('/workspace/mcis-paddleocr-trial/venv/bin/python'),Path('/workspace/mcis-paddleocr-trial/models'),Path('/workspace/mcis-paddleocr-trial/cache'))
    root=Path('/workspace/mcis-paddleocr-handoff/source')
    with TestClient(app) as c:
        body=request_body(c,(root/'report.pdf').read_bytes(),(root/'page-6.png').read_bytes())
        response=c.post(BASE+'/image-ocr-tasks',json=body);assert response.status_code==201,response.text
        d=response.json();assert d['status']=='succeeded' and d['runtime']['mode']=='actual-local-ocr-run'
        run=c.get(BASE+'/image-reviews/'+d['runId']);assert run.status_code==200,run.text
        assert len(run.json()['initial']['candidate']['text_lines'])>0
        assert run.json()['factVerified'] is False
        raw=c.post(BASE+'/image-ocr-tasks/'+body['taskId']+'/artifacts/raw:download',json={'purpose':'public actual output check'})
        assert raw.status_code==200 and digest(raw.content)==d['runtime']['raw_sha256']
        assert edit(c,d['runId'],word=run.json()['initial']['candidate']['text_lines'][0]['text']).status_code==200
        # Operator/test confirmation, not independently accepted transcription or fact.
        print(json.dumps({'runtime':d['runtime'],'lineCount':len(run.json()['initial']['candidate']['text_lines']),'taskId':d['taskId']},ensure_ascii=False))
