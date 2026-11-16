"""New ordinary business nodes only: generated PDF/PNG + fabricated OCR arrays.
No product database, permission/write probe, original case or OCR model execution.
"""
import base64
import copy
import io
import json
import pytest
from PIL import Image, ImageDraw
from reportlab.pdfgen.canvas import Canvas
from .contract import digest
from .test_contract import fixture
from .image_bytes import check_image_members


def supplied():
    i,b,put=fixture('image')
    pdf=io.BytesIO();canvas=Canvas(pdf,pagesize=(200,200))
    for n in (1,2):
        canvas.drawString(20,160,'Synthetic PDF page '+str(n));canvas.showPage()
    canvas.save()
    png=io.BytesIO();image=Image.new('RGB',(100,200),'white')
    ImageDraw.Draw(image).text((5,5),'Synthetic PNG',fill='black');image.save(png,format='PNG')
    for src,raw in zip(i['sources'],(pdf.getvalue(),png.getvalue())):
        put(src['originalMember'],raw);src.update(registeredSha256=digest(raw),currentSha256=digest(raw))
        receipt=json.loads(b[src['receiptMember']]);receipt['sourceSha256']=digest(raw);put(src['receiptMember'],receipt)
    i['sources'][1]['location'].update(pdfPage1Based=2,printedPage='declared-2')
    raw={'rec_texts':['Synthetic OCR',''],'rec_scores':[0.9,0.5],
         'rec_boxes':[[0,0,90,20],[0,30,90,50]],
         'rec_polys':[[[0,0],[90,0],[90,20],[0,20]],[[0,30],[90,30],[90,50],[0,50]]],
         'page_index':None}
    put('raw',raw)
    rec=dict(paddlepaddle='synthetic',paddleocr='synthetic',paddlex='synthetic',pipeline='PP-OCRv5',device='not-executed',models=['synthetic-fixture'])
    machine=dict(schema='mcis.offline-ocr-candidate/v0.1',production_import_supported=False,status='pending_human_review',needs_review=True,confirmed=False,
        source=dict(pdf_sha256=i['sources'][0]['currentSha256'],image_sha256=i['sources'][1]['currentSha256'],raw_sha256=digest(b['raw']),
                    pdf_page_1based=2,printed_page='declared-2',mapping_basis='manual_source_manifest',width=100,height=200),
        recognizer=rec,raw_page_index=None,page_index_inferred=False,coordinate_space='rendered_page_pixels_xy_top_left',
        limitations=['Synthetic test; no rendering lineage or OCR execution.'],tables=[],
        text_lines=[dict(line_index=n,text=t,is_blank=t=='',model_score=raw['rec_scores'][n],bbox=raw['rec_boxes'][n],polygon=raw['rec_polys'][n],
                        needs_review=True,confirmed=False) for n,t in enumerate(raw['rec_texts'])])
    put('recognizer',rec)
    initial=json.loads(b['initial']);initial.update(pageMappingVerified=False,originalAuthenticityVerified=False);put('initial',initial)
    human=json.loads(b['human']);human['decision']='pending';put('human',human)
    sync(i,b,put,machine)
    return i,b,put


def sync(i,b,put,machine):
    put('machine',machine)
    initial=json.loads(b['initial']);initial['candidate']=machine;put('initial',initial)
    task=json.loads(b['task'])
    for key in ('raw','candidate'):
        member='raw' if key=='raw' else 'machine'
        task[key+'Base64']=base64.b64encode(b[member]).decode()
        task['artifacts'][key]['sha256']=digest(b[member])
    put('task',task)


def test_generated_pdf_png_and_pending_ocr_consistency():
    i,b,_=supplied();before=copy.deepcopy((i,b));result=check_image_members(i,b)
    assert result['pdfPageCounts']=={'PDF':2} and result['source_bytes_match'] is True
    assert result['page_mapping_verified'] is False and result['ocr_execution_verified'] is False
    assert result['restore_ready'] is False and result['export_allowed'] is False
    assert (i,b)==before


def test_declared_page_outside_actual_pdf_rejected():
    i,b,put=supplied();i['sources'][1]['location']['pdfPage1Based']=3
    machine=json.loads(b['machine']);machine['source']['pdf_page_1based']=3;sync(i,b,put,machine)
    with pytest.raises(ValueError,match='outside document'):check_image_members(i,b)


def test_declared_png_dimensions_must_match_decoded_bytes():
    i,b,put=supplied();i['sources'][1]['location']['width']=101
    machine=json.loads(b['machine']);machine['source']['width']=101;sync(i,b,put,machine)
    with pytest.raises(ValueError,match='image size'):check_image_members(i,b)


def test_missing_raw_member_rejected():
    i,b,_=supplied();del b['raw']
    with pytest.raises(ValueError):check_image_members(i,b)


def test_original_digest_disagreement_rejected():
    i,b,_=supplied();i['sources'][0]['registeredSha256']='0'*64
    with pytest.raises(ValueError):check_image_members(i,b)


def test_candidate_text_must_match_retained_ocr_rows():
    i,b,put=supplied();machine=json.loads(b['machine']);machine['text_lines'][0]['text']='Different draft';sync(i,b,put,machine)
    with pytest.raises(ValueError,match='retained OCR rows'):check_image_members(i,b)


def test_recognizer_metadata_must_match():
    i,b,put=supplied();put('recognizer',{'model':'different declaration'})
    with pytest.raises(ValueError,match='recognizer declaration'):check_image_members(i,b)


def test_null_raw_page_and_blank_line_remain_unknown_pending():
    i,b,_=supplied();check_image_members(i,b);doc=json.loads(b['machine'])
    assert doc['raw_page_index'] is None and doc['page_index_inferred'] is False
    assert doc['text_lines'][1]['text']=='' and doc['text_lines'][1]['is_blank'] is True
    assert doc['text_lines'][1]['confirmed'] is False


def test_ocr_boxes_must_fit_actual_image_dimensions():
    i,b,put=supplied();raw=json.loads(b['raw']);raw['rec_boxes'][0][2]=101;put('raw',raw)
    machine=json.loads(b['machine']);machine['source']['raw_sha256']=digest(b['raw']);machine['text_lines'][0]['bbox'][2]=101;sync(i,b,put,machine)
    with pytest.raises(ValueError,match='box bounds'):check_image_members(i,b)


def test_missing_pdf_inspector_does_not_claim_success(monkeypatch):
    from . import image_bytes
    i,b,_=supplied();monkeypatch.setattr(image_bytes.shutil,'which',lambda name:None)
    with pytest.raises(ValueError,match='unavailable'):check_image_members(i,b)


def test_table_candidate_remains_unsupported():
    i,b,put=supplied();machine=json.loads(b['machine']);machine['tables']=[{'synthetic':True}];sync(i,b,put,machine)
    with pytest.raises(ValueError,match='table review not supported'):check_image_members(i,b)


def test_page_declaration_does_not_become_verified():
    i,b,put=supplied();initial=json.loads(b['initial']);initial['pageMappingVerified']=True;put('initial',initial)
    with pytest.raises(ValueError,match='unverified source markers'):check_image_members(i,b)
