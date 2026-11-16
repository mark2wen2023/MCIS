"""New ordinary combined synthetic workflows; no real OCR/ASR/browser or safety probes."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from mcis_service.audio_review.app import create_audio_review_app, Revision
from mcis_service.image_review.app import create_image_review_app, Record
from mcis_service.main import create_app
from mcis_service.audit.models import AuditEventRow
from mcis_service.audit.service import verify_chain
from .conftest import H
from .test_image_review_candidate import new_app, register, edit, BASE, CID
from .test_audio_review_candidate import attach, revision, BASE as AUDIO_BASE


class AudioCaseClient:
    """Use existing synthetic audio fixture functions with the same synthetic case."""
    def __init__(self,client):self.client=client
    def get(self,path,**kw):return self.client.get(path.replace(AUDIO_BASE,BASE),**kw)
    def post(self,path,**kw):return self.client.post(path.replace(AUDIO_BASE,BASE),**kw)


@pytest.fixture
def combined(tmp_path):
    image,settings=new_app(tmp_path)
    audio=create_audio_review_app(settings)
    with TestClient(image) as ic,TestClient(audio) as ac:
        r,_=register(ic);assert r.status_code==201,r.text
        image_run=r.json()['runId']
        _,_,_,a=attach(AudioCaseClient(ac));audio_run=a['runId']
        yield image,audio,settings,ic,ac,image_run,audio_run


def test_shared_database_preserves_independent_revisions_and_audit(combined):
    image,audio,_,ic,ac,ir,ar=combined
    assert edit(ic,ir,word='synthetic image correction').status_code==200
    r=ac.post(BASE+'/audio-reviews/'+ar+'/revisions',json=revision(text='synthetic audio correction'))
    assert r.status_code==200,r.text
    im=ic.get(BASE+'/image-reviews/'+ir).json();au=ac.get(BASE+'/audio-reviews/'+ar).json()
    assert im['reviews'][0]['text']=='synthetic image correction'
    assert au['humanRevisions'][0]['text']=='synthetic audio correction'
    assert im['initial']['candidate']['text_lines'][0]['text']=='ship 001'
    assert au['initial']['machineDraft']['transcript']['segments'][0]['text']=='合成草稿，非ASR文字'
    with image.state.db.session() as s:
        rows=s.scalars(select(AuditEventRow).where(AuditEventRow.case_id==CID).order_by(AuditEventRow.seq)).all()
        assert verify_chain([r.line for r in rows])['valid'] is True
        actions=[r.action for r in rows]
        assert all(actions.count(a)==1 for a in ('ocr.import','audio.draft.attach','ocr.review','audio.human.revise'))
        assert s.query(Record).count()==2 and s.query(Revision).count()==2


def test_independent_factories_reopen_same_histories(combined):
    _,_,settings,ic,ac,ir,ar=combined
    assert edit(ic,ir,word='retained image').status_code==200
    assert ac.post(BASE+'/audio-reviews/'+ar+'/revisions',json=revision(text='retained audio')).status_code==200
    with TestClient(create_audio_review_app(settings)) as anew,TestClient(create_image_review_app(settings)) as inew:
        assert anew.get(BASE+'/audio-reviews/'+ar).json()['humanRevisions'][0]['text']=='retained audio'
        assert inew.get(BASE+'/image-reviews/'+ir).json()['reviews'][0]['text']=='retained image'


def test_mixed_case_export_refuses_without_partial_package_or_record_changes(combined):
    image,_,_,ic,ac,ir,ar=combined
    def rows():
        with image.state.db.session() as s:
            return ([r.doc for r in s.scalars(select(Record).order_by(Record.id))],
                    [r.doc for r in s.scalars(select(Revision).order_by(Revision.id))],
                    [r.line for r in s.scalars(select(AuditEventRow).order_by(AuditEventRow.seq))])
    before=rows()
    for client in (ic,ac):
        r=client.get(BASE+'/export',headers=H('LeadInvestigator'))
        assert r.status_code==409,r.text
        assert 'application/zip' not in r.headers.get('content-type','') and not r.content.startswith(b'PK')
    assert rows()==before


def test_no_unified_default_routes_or_implicit_model_runtime(combined):
    image,audio,settings,ic,ac,_,_=combined
    paths=lambda app:{getattr(r,'path','') for r in app.routes}
    assert '/image-review-lab' in paths(image) and '/audio-review-lab' not in paths(image)
    assert '/audio-review-lab' in paths(audio) and '/image-review-lab' not in paths(audio)
    default=paths(create_app(settings))
    assert '/audio-review-lab' not in default and '/image-review-lab' not in default
    assert image.state.image_ocr_runtime is None and audio.state.audio_asr_runtime is None
    assert ic.post(BASE+'/image-ocr-tasks',json={}).status_code==503
    assert ac.post(BASE+'/audio-asr-tasks',json={}).status_code==503
