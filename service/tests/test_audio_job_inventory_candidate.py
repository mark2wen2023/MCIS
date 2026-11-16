"""New ordinary synthetic directory-layout tests, no security/write-refusal probes."""
import hashlib
import json
from types import SimpleNamespace
import pytest
from mcis_service.db import WRITE_LOCK
from mcis_service.reports.access import begin
from mcis_service.audio_review import tasks, job_inventory
from .test_audio_review_candidate import local, BASE, CID
from .test_audio_sensevoice_tasks import configured


def prepare(configured,files=('source.wav','raw.json')):
    c,app,settings,body,calls=configured
    # The injected recognizer result is synthetic; add the worker's ordinary identity field.
    original=tasks.execute
    def output(*args):return {**original(*args),'taskId':body['taskId']}
    tasks.execute=output
    try:
        response=c.post(BASE+'/audio-asr-tasks',json=body)
    finally:tasks.execute=original
    assert response.status_code==201,response.text
    with app.state.db.session() as s:doc=dict(s.get(tasks.Task,body['taskId']).doc)
    job=settings.data_dir/'audio-asr-jobs'/body['taskId']
    if files is not None:
        job.mkdir(parents=True)
        if 'source.wav' in files:
            raw=(settings.blob_dir/CID/'raw'/'evidence-intakes'/body['audioReceipt']/'source.bin').read_bytes()
            (job/'source.wav').write_bytes(raw)
        if 'raw.json' in files:(job/'raw.json').write_text(json.dumps(doc['raw'],ensure_ascii=False,indent=2))
    return app,settings,doc,job,calls


def inspect(app,settings):
    ctx=SimpleNamespace(role='LeadInvestigator',operator='Synthetic observer',settings=settings,db=app.state.db)
    with WRITE_LOCK,app.state.db.session() as s:
        begin(s);return job_inventory.inspect_case_jobs(ctx,s,CID)


def test_known_job_members_match_without_granting_export(configured):
    app,settings,doc,job,calls=prepare(configured)
    before={p.name:p.read_bytes() for p in job.iterdir()};result=inspect(app,settings)
    assert result['inventory_consistent'] is True
    assert not any(result[k] for k in ('export_allowed','restore_ready','cleanup_allowed','execution_allowed'))
    assert {p.name:p.read_bytes() for p in job.iterdir()}==before and len(calls)==1


def test_absent_expected_directory_is_unresolved(configured):
    app,settings,_,job,_=prepare(configured,None)
    result=inspect(app,settings)
    assert result['inventory_consistent'] is False and not job.exists()
    assert result['tasks'][0]['issues']==['JOB_DIRECTORY_UNAVAILABLE']


def test_missing_result_member_is_not_reconstructed(configured):
    app,settings,_,job,_=prepare(configured,('source.wav',))
    result=inspect(app,settings)
    assert 'MISSING_MEMBER:raw.json' in result['tasks'][0]['issues'] and not (job/'raw.json').exists()


def test_worker_log_and_home_remain_unclassified_unread(configured,monkeypatch):
    app,settings,_,job,_=prepare(configured)
    (job/'worker.log').write_text('synthetic diagnostic');(job/'home').mkdir()
    seen=[];original=job_inventory._read_member
    def counted(fd,name,limit):seen.append(name);return original(fd,name,limit)
    monkeypatch.setattr(job_inventory,'_read_member',counted)
    result=inspect(app,settings)
    assert result['inventory_consistent'] is False and seen==['source.wav','raw.json']
    assert set(result['tasks'][0]['issues'])=={'UNCLASSIFIED_MEMBER:worker.log','UNCLASSIFIED_MEMBER:home'}
    assert (job/'worker.log').read_text()=='synthetic diagnostic' and (job/'home').is_dir()


def test_current_raw_file_hash_is_not_historical_digest(configured):
    app,settings,doc,job,_=prepare(configured)
    result=inspect(app,settings);member=result['tasks'][0]['members']['raw.json']
    assert result['inventory_consistent'] is True
    assert member['observedSha256']==hashlib.sha256((job/'raw.json').read_bytes()).hexdigest()
    assert member['observedSha256']!=doc['artifacts']['raw']['sha256']
    assert member['historicalFileDigestVerified'] is False


def test_different_saved_result_is_reported_not_overwritten(configured):
    app,settings,_,job,_=prepare(configured,('source.wav',))
    different=b'{"synthetic":"different result"}';(job/'raw.json').write_bytes(different)
    result=inspect(app,settings)
    assert 'RAW_RESULT_DIFFERS' in result['tasks'][0]['issues']
    assert (job/'raw.json').read_bytes()==different


def test_unconfirmed_task_does_not_read_directory_or_restart(configured,monkeypatch):
    c,app,settings,body,calls=configured
    def failed(*args):calls.append('synthetic failure');raise ValueError('ordinary synthetic execution failure')
    monkeypatch.setattr(tasks,'execute',failed)
    assert c.post(BASE+'/audio-asr-tasks',json=body).status_code==409
    visited=[]
    def observe(path):visited.append(path);return None
    monkeypatch.setattr(job_inventory,'_directory',observe)
    result=inspect(app,settings)
    assert result['tasks'][0]['issues']==['TASK_NOT_CONFIRMED_SUCCESS']
    assert visited==[] and calls==['synthetic failure']
