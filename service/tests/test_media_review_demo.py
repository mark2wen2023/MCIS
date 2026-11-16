"""New ordinary same-app synthetic workflows; no model/browser/safety probes."""
import inspect
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from mcis_service.media_review_demo import create_media_review_demo
from mcis_service.main import create_app
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.audit.models import AuditEventRow
from mcis_service.audit.service import verify_chain
from mcis_service.audio_review.app import Revision, create_audio_review_app
from mcis_service.image_review.app import Record, create_image_review_app
from .conftest import make_settings, H
from .test_image_review_candidate import register, edit, BASE, CID
from .test_audio_review_candidate import attach, revision
from .test_image_audio_combination import AudioCaseClient


@pytest.fixture
def demo(tmp_path):
    settings=make_settings(tmp_path,False);app=create_media_review_demo(settings)
    with app.state.db.session() as s:
        put_doc(s,CaseRow,CID,CID,{'caseId':CID,'schemaVersion':'1.0.0','title':'synthetic combined demo','isFictionalDemo':True,
            'caseEpochUtc':'2026-01-01T00:00:00Z','incidentTimeUtc':'2026-01-01T00:00:00Z',
            'incidentLocation':{'lonDeg':121,'latDeg':31},'displayTimeZoneOffsetMinutes':0})
    with TestClient(app) as c:
        r,_=register(c);assert r.status_code==201
        _,_,_,a=attach(AudioCaseClient(c))
        yield app,settings,c,r.json()['runId'],a['runId']


def test_same_app_edits_audit_and_reopen_preserve_both_histories(demo):
    app,settings,c,ir,ar=demo
    assert edit(c,ir,word='demo image correction').status_code==200
    assert c.post(BASE+'/audio-reviews/'+ar+'/revisions',json=revision(text='demo audio correction')).status_code==200
    with app.state.db.session() as s:
        events=s.scalars(select(AuditEventRow).where(AuditEventRow.case_id==CID).order_by(AuditEventRow.seq)).all()
        assert verify_chain([e.line for e in events])['valid']
        assert all([e.action for e in events].count(action)==1 for action in ('ocr.import','ocr.review','audio.draft.attach','audio.human.revise'))
    with TestClient(create_media_review_demo(settings)) as reopened:
        im=reopened.get(BASE+'/image-reviews/'+ir).json();au=reopened.get(BASE+'/audio-reviews/'+ar).json()
        assert im['reviews'][0]['text']=='demo image correction'
        assert au['humanRevisions'][0]['text']=='demo audio correction'
        assert im['initial']['candidate']['text_lines'][0]['text']=='ship 001'
        assert au['initial']['machineDraft']['transcript']['segments'][0]['text']=='合成草稿，非ASR文字'


def test_demo_routes_once_and_default_app_still_unmounted(demo):
    app,settings,c,_,_=demo
    paths=[getattr(r,'path','') for r in app.routes]
    for path in ('/image-review-lab','/image-review-lab/preview.js','/audio-review-lab'):
        assert paths.count(path)==1
        assert c.get(path).status_code==200
    keys=[(r.path,m) for r in app.routes if hasattr(r,'methods') for m in r.methods]
    assert len(keys)==len(set(keys))
    default={getattr(r,'path','') for r in create_app(settings).routes}
    assert '/image-review-lab' not in default and '/audio-review-lab' not in default


def test_demo_has_no_runtime_arguments_and_both_tasks_unconfigured(demo):
    app,_,c,_,_=demo
    assert list(inspect.signature(create_media_review_demo).parameters)==['settings']
    assert app.state.image_ocr_runtime is None and app.state.audio_asr_runtime is None
    assert c.post(BASE+'/image-ocr-tasks',json={}).status_code==503
    assert c.post(BASE+'/audio-asr-tasks',json={}).status_code==503


def test_demo_mixed_case_refuses_export_without_partial_state(demo):
    app,_,c,_,_=demo
    def snapshot():
        with app.state.db.session() as s:
            return ([r.doc for r in s.scalars(select(Record).order_by(Record.id))],
                    [r.doc for r in s.scalars(select(Revision).order_by(Revision.id))],
                    [r.line for r in s.scalars(select(AuditEventRow).order_by(AuditEventRow.seq))])
    before=snapshot();r=c.get(BASE+'/export',headers=H('LeadInvestigator'))
    assert r.status_code==409 and not r.content.startswith(b'PK')
    assert 'application/zip' not in r.headers.get('content-type','') and snapshot()==before


def test_original_factories_keep_separate_routes_and_explicit_configuration(tmp_path):
    settings=make_settings(tmp_path,False);runtime=object()
    image=create_image_review_app(settings,ocr_runtime=runtime)
    audio=create_audio_review_app(settings,sensevoice_runtime=runtime)
    assert image.state.image_ocr_runtime is runtime and audio.state.audio_asr_runtime is runtime
    assert '/audio-review-lab' not in {getattr(r,'path','') for r in image.routes}
    assert '/image-review-lab' not in {getattr(r,'path','') for r in audio.routes}
