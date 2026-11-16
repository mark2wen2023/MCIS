"""New ordinary parity tests against exact parent implementation; no old test nodes."""
import subprocess
from types import ModuleType, SimpleNamespace
import pytest
from mcis_service.db import WRITE_LOCK, put_doc
from mcis_service.reports.access import begin
from mcis_service.audio_review import archive_candidate, generation_assembly, generation
from mcis_service.recommendations.models import RecommendationRow
from .test_audio_review_candidate import local, BASE, CID, revision
from .test_audio_sensevoice_tasks import configured

PARENT='de207b3544abc1fc097b098eff3085d647ca7b3e'


def parent_module(path,package):
    # Read committed Python source only, never load historical test modules or run a suite.
    source=subprocess.check_output(['git','show',PARENT+':'+path],text=True)
    mod=ModuleType('frozen_reference');mod.__package__=package
    exec(compile(source,path,'exec'),mod.__dict__)
    return mod


def reference(mode):
    name='preflight' if mode=='legacy' else 'generation_inventory'
    inventory=parent_module('research/media_archive/'+name+'.py','research.media_archive')
    name='archive_candidate' if mode=='legacy' else 'generation_assembly'
    adapter=parent_module('service/mcis_service/audio_review/'+name+'.py','mcis_service.audio_review')
    adapter.scan=inventory.scan
    return adapter


def extract(adapter,app,settings):
    ctx=SimpleNamespace(role='LeadInvestigator',operator='Synthetic compatibility',settings=settings,db=app.state.db)
    with WRITE_LOCK,app.state.db.session() as s:
        begin(s);return adapter.build_candidate(ctx,s,CID)


def start(configured):
    c,app,settings,b,calls=configured
    response=c.post(BASE+'/audio-asr-tasks',json=b)
    assert response.status_code==201,response.text
    return c,app,settings,b,calls,response.json()


def test_generation_output_is_identical_to_parent_with_human_history(configured):
    c,app,settings,b,calls,task=start(configured)
    assert c.post(BASE+'/audio-reviews/'+task['runId']+'/revisions',json=revision(expectedRevision=0,segmentId='sv-1',text='synthetic edit',startMs=None,endMs=None)).status_code==200
    expected=extract(reference('generation'),app,settings)
    actual=extract(generation_assembly,app,settings)
    assert actual==expected and actual['export_allowed'] is False and actual['restore_ready'] is False


def test_legacy_entry_still_rejects_new_tables_like_parent(configured):
    _,app,settings,_,_,_=start(configured)
    for adapter in (reference('legacy'),archive_candidate):
        with pytest.raises(ValueError,match='unknown media table'):extract(adapter,app,settings)


def test_legacy_shaped_task_output_matches_parent(configured,monkeypatch):
    # Synthetic pre-generation task fixture; no old records deleted or backfilled.
    monkeypatch.setattr(generation,'register',lambda *args:'synthetic-no-generation')
    monkeypatch.setattr(generation,'observe',lambda *args:None)
    _,app,settings,_,_,_=start(configured)
    assert extract(archive_candidate,app,settings)==extract(reference('legacy'),app,settings)
    for adapter in (reference('generation'),generation_assembly):
        with pytest.raises(ValueError,match='history unknown'):extract(adapter,app,settings)


def test_unsupported_business_state_still_refused_by_generation_entry(configured):
    _,app,settings,_,_,_=start(configured)
    with app.state.db.session() as s:put_doc(s,RecommendationRow,CID,'synthetic',{'title':'ordinary unsupported fixture'})
    for adapter in (reference('generation'),generation_assembly):
        with pytest.raises(ValueError,match='unsupported case state'):extract(adapter,app,settings)


def test_generation_two_tasks_still_read_one_registered_source(configured,monkeypatch):
    c,app,settings,b,calls,_=start(configured)
    assert c.post(BASE+'/audio-asr-tasks',json={**b,'taskId':'2'*32}).status_code==201
    original=generation_assembly.load_receipt;seen=[]
    def counted(*args):seen.append(args[-1]);return original(*args)
    monkeypatch.setattr(generation_assembly,'load_receipt',counted)
    out=extract(generation_assembly,app,settings)
    assert seen==[b['audioReceipt']] and len(out['index']['observations'])==4
    assert out==extract(reference('generation'),app,settings)
