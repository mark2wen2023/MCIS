"""New ordinary workflow tests only; synthetic unless explicit public fixture supplied.
No historical security/ECFC test selection, no model/network calls.
"""
import base64
import copy
import hashlib
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from mcis_service.image_review.app import create_image_review_app, Record
from mcis_service.image_review.contract import parse
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.audit.models import AuditEventRow
from mcis_service.main import create_app
from .conftest import make_settings, H

CID='OCR-SYNTHETIC'
BASE='/api/v1/cases/'+CID

def digest(raw): return hashlib.sha256(raw).hexdigest()

def candidate(pdf=b'synthetic PDF bytes', image=b'synthetic page bytes'):
    return {'schema':'mcis.offline-ocr-candidate/v0.1','production_import_supported':False,'page_index_inferred':False,'limitations':['synthetic fixture'],'confirmed':False,'needs_review':True,'status':'pending_human_review',
        'source':{'pdf_sha256':digest(pdf),'image_sha256':digest(image),'raw_sha256':digest(b'synthetic recognizer output'),
        'pdf_page_1based':6,'printed_page':'4','mapping_basis':'synthetic declaration','width':100,'height':100},
        'recognizer':{'paddlepaddle':'synthetic','paddleocr':'synthetic','paddlex':'synthetic','pipeline':'synthetic', 'models':['fixture'],'device':'none'},
        'raw_page_index':None,'coordinate_space':'rendered_page_pixels_xy_top_left','tables':[],
        'text_lines':[{'line_index':0,'text':'ship 001','is_blank':False,'confirmed':False,'needs_review':True,'model_score':.9,'bbox':[0,0,30,20],'polygon':[[0,0],[30,0],[30,20],[0,20]]}]}

def new_app(tmp_path):
    settings=make_settings(tmp_path,False);app=create_image_review_app(settings)
    with app.state.db.session() as s:
        put_doc(s,CaseRow,CID,CID,{'caseId':CID,'schemaVersion':'1.0.0','title':'synthetic OCR workflow','isFictionalDemo':True,
            'caseEpochUtc':'2026-01-01T00:00:00Z','incidentTimeUtc':'2026-01-01T00:00:00Z',
            'incidentLocation':{'lonDeg':121,'latDeg':31},'displayTimeZoneOffsetMinutes':0})
    return app,settings

def intake(c,raw,name):
    body={'profile':'mcis-evidence-intake-v1','fileName':name,'title':name,'source':'synthetic or explicit public test copy',
          'extractedBy':'test fixture operator','extractedUtc':'2026-11-16T00:00:00Z','category':'Document',
          'confidentiality':'Restricted','note':'test acquisition timestamp; not accident time','contentBase64':base64.b64encode(raw).decode()}
    r=c.post(BASE+'/evidence-intakes:preview',json=body);assert r.status_code==200,r.text
    r=c.post(BASE+'/evidence-intakes:commit',json={**body,'requestDigest':r.json()['requestDigest'],'confirmed':True});assert r.status_code==200,r.text
    return r.json()['requestDigest']

def register(c,pdf=b'synthetic PDF bytes',image=b'synthetic page bytes',value=None,raw_output=b'synthetic recognizer output'):
    value=value or candidate(pdf,image)
    bindings={k:intake(c,raw,name) for k,raw,name in [('pdf',pdf,'report.pdf'),('image',image,'page.png'),('candidate',json.dumps(value,ensure_ascii=False).encode(),'result.json'),('raw',raw_output,'raw-ocr.json')]}
    r=c.post(BASE+'/image-reviews',json={'bindings':bindings,'acknowledgeArchiveBlocked':True})
    return r,bindings

def edit(c,run,revision=0,word='ship 002'):
    return c.post(BASE+'/image-reviews/'+run+'/reviews',json={'expectedRevision':revision,'lineIndex':0,'text':word,'decision':'transcription-checked','reason':'synthetic manual correction'})


def test_roundtrip_review_restart_download_and_archive_refusal(tmp_path):
    app,settings=new_app(tmp_path)
    with TestClient(app) as c:
        r,bindings=register(c);assert r.status_code==201,r.text
        d=r.json();run=d['runId'];assert d['initial']['candidate']['raw_page_index'] is None
        r=edit(c,run);assert r.status_code==200,r.text
        assert r.json()['initial']['candidate']['text_lines'][0]['text']=='ship 001'
        assert r.json()['reviews'][0]['text']=='ship 002' and r.json()['factVerified'] is False
        r=edit(c,run,0,'stale');assert r.status_code==412
        r=edit(c,run,1,'ship 003');assert r.status_code==200
        for k,raw in [('pdf',b'synthetic PDF bytes'),('image',b'synthetic page bytes')]:
            q=c.post(BASE+'/evidence-intakes/'+bindings[k]+':download',json={'purpose':'synthetic human comparison'})
            assert q.status_code==200 and q.content==raw and q.headers['X-Sha256']==digest(raw)
        q=c.get(BASE+'/export',headers=H('LeadInvestigator'));assert q.status_code==409,q.text
        assert 'application/zip' not in q.headers.get('content-type','')
    with TestClient(create_image_review_app(settings)) as c:
        q=c.get(BASE+'/image-reviews/'+run);assert q.status_code==200
        assert [x['text'] for x in q.json()['reviews']]==['ship 002','ship 003']
        assert q.json()['revision']==2
    with app.state.db.session() as s:
        actions=[x.action for x in s.scalars(select(AuditEventRow).where(AuditEventRow.case_id==CID))]
        assert actions.count('ocr.import')==1 and actions.count('ocr.review')==2


def test_review_failure_rolls_back_with_explicit_injection(tmp_path,monkeypatch):
    from mcis_service.image_review import app as module
    app,_=new_app(tmp_path)
    with TestClient(app,raise_server_exceptions=False) as c:
        r,_=register(c);run=r.json()['runId'];reached=[]
        def fail(*args,**kwargs):
            s=args[0]
            reached.append(s.scalar(select(Record.revision).where(Record.run_id==run).order_by(Record.revision.desc())))
            raise RuntimeError('synthetic failure after inserted review')
        monkeypatch.setattr(module.audit,'append',fail)
        assert edit(c,run).status_code==500
        assert reached==[1]
        q=c.get(BASE+'/image-reviews/'+run);assert q.json()['revision']==0 and q.json()['reviews']==[]


@pytest.mark.parametrize('change',[
    lambda d:d.update(tables=[{}]),lambda d:d['source'].update(pdf_page_1based=0),
    lambda d:d['text_lines'][0].update(bbox=[0,0,101,20]),lambda d:d['text_lines'][0].update(confirmed=True),
    lambda d:d['text_lines'][0].update(line_index=True),lambda d:d['recognizer'].update(models=[]),
])
def test_new_contract_rejects_unsupported_or_invalid_values(change):
    d=candidate();change(d)
    with pytest.raises(ValueError):parse(json.dumps(d).encode())


def test_blank_line_is_not_filled():
    d=candidate();d['text_lines'][0]['text']='';d['text_lines'][0]['is_blank']=True
    assert parse(json.dumps(d).encode())['text_lines'][0]['text']==''


def test_default_application_does_not_enable_experiment(tmp_path):
    app=create_app(make_settings(tmp_path,False))
    with TestClient(app) as c:
        assert c.get('/image-review-lab').status_code==404
    from sqlalchemy import inspect
    assert 'image_ocr_review_records' not in inspect(app.state.db.engine).get_table_names()


def test_public_existing_output(tmp_path):
    # Opt-in local public artifact only: no automatic download or fixture fabrication.
    import os
    root=os.environ.get('MCIS_PUBLIC_OCR_FIXTURE')
    if not root:pytest.skip('explicit local public handoff required')
    root=Path(root);pdf=(root/'source/report.pdf').read_bytes();image=(root/'source/page-6.png').read_bytes()
    assert digest(pdf)=='99084b8e672da6e2f8d9809bea25a92fe5fcf31c318554832e14339610015d7f'
    value=json.loads((root/'candidates/ocr-page-6.candidate.json').read_text())
    app,settings=new_app(tmp_path)
    with TestClient(app) as c:
        r,bindings=register(c,pdf,image,value,(root/'raw/ocr-page-6.json').read_bytes());assert r.status_code==201,r.text
        d=r.json();assert d['initial']['candidate']==value
        assert d['initial']['mode']=='imported-existing-output'
        # Simulated reviewer: preserves the real OCR text; not independent human acceptance.
        r=edit(c,d['runId'],word=value['text_lines'][0]['text']);assert r.status_code==200,r.text
        for kind,raw in [('pdf',pdf),('image',image)]:
            q=c.post(BASE+'/evidence-intakes/'+bindings[kind]+':download',json={'purpose':'public sample byte roundtrip test'})
            assert q.status_code==200 and q.content==raw
    with TestClient(create_image_review_app(settings)) as c:
        q=c.get(BASE+'/image-reviews/'+d['runId']);assert q.status_code==200
        assert q.json()['initial']['candidate']==value and len(q.json()['reviews'])==1


def test_run_list_recovers_id_without_claiming_source_check(tmp_path):
    app,_=new_app(tmp_path)
    with TestClient(app) as c:
        assert c.get(BASE+'/image-reviews').json()==[]
        r,_=register(c);run=r.json()['runId']
        listing=c.get(BASE+'/image-reviews');assert listing.status_code==200
        assert listing.json()==[{'runId':run,'caseId':CID,'utc':r.json()['initial']['utc'],'sourceCheck':'not-performed-by-list'}]
        assert c.get(BASE+'/image-reviews/'+run).json()['initial']==r.json()['initial']


def test_source_input_mismatch_is_not_silently_rebound(tmp_path):
    app,_=new_app(tmp_path)
    with TestClient(app) as c:
        value=candidate();value['source']['pdf_sha256']=digest(b'different input version')
        r,_=register(c,value=value);assert r.status_code==409
        assert r.json()['code']=='OCR_VERSION'
        assert c.get(BASE+'/image-reviews').json()==[]


def test_two_editors_and_empty_pending_revision(tmp_path):
    app,_=new_app(tmp_path)
    with TestClient(app) as a,TestClient(app) as b:
        r,_=register(a);run=r.json()['runId']
        assert b.get(BASE+'/image-reviews/'+run).json()['revision']==0
        assert edit(a,run,0,'first editor').status_code==200
        assert edit(b,run,0,'second editor draft').status_code==412
        r=b.post(BASE+'/image-reviews/'+run+'/reviews',json={'expectedRevision':1,'lineIndex':0,'text':'','decision':'unreadable','reason':'cannot transcribe'})
        assert r.status_code==200 and r.json()['reviews'][-1]['text']==''
        assert r.json()['initial']['candidate']['text_lines'][0]['text']=='ship 001'


def test_page_contains_caveats_and_no_remote_scripts(tmp_path):
    app,_=new_app(tmp_path)
    with TestClient(app) as c:
        response=c.get('/image-review-lab');assert response.status_code==200
        html=response.text
        for text in ['已有OCR输出导入，不重新识别','不是事实确认','未自动验证','草稿仅页面内存','授权下载','不自动重试']:
            assert text in html
        assert '<script src=' not in html and 'innerHTML' not in html and 'localStorage' not in html
