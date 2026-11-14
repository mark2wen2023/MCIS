from copy import deepcopy
import hashlib
import pytest
from binding import build,validate,BindingError,digest,canonical


def fixture():
    pdf=b'%PDF-synthetic binding bytes (not parsed)'
    source={'caseId':'CASE-A','evidenceId':'EV-A','registeredSha256':'a'*64,'expectedCurrentSha256':digest(pdf),'sourceStateDigest':'b'*64}
    text='报告原文\n';raw=text.encode()
    d={'format':'mcis-digital-pdf-text-layer','version':1,'sourcePdfSha256':digest(pdf),'sourceByteLength':len(pdf),'method':'embedded_text_only','tool':'synthetic unit fixture','parameters':['-layout','-enc','UTF-8'],'pageCount':1,'pages':[{'physicalPage':1,'text':text,'textSha256':digest(raw),'byteLength':len(raw),'status':'text_layer_present'}],'warnings':['synthetic test, not parsed']}
    return pdf,source,d

def test_three_hashes_distinct_and_source_preserved():
    pdf,s,d=fixture();before=deepcopy((s,d));a=build(s,pdf,d)
    assert validate(a,s,pdf)
    assert a['sourceBinding']['registeredSha256']=='a'*64
    assert len({a['artifactSha256'],a['derivativeContentSha256'],s['expectedCurrentSha256']})==3
    assert (s,d)==before and 'custody' not in a
    a['derivative']['pages'][0]['text']='edited';assert d==before[1]

@pytest.mark.parametrize('kind',['pdf','case','evidence','source_version','current_hash','page_hash','page_index','page_count','tool','method','artifact_hash'])
def test_mismatch_reject(kind):
    pdf,s,d=fixture();a=build(s,pdf,d)
    if kind=='pdf':pdf+=b'change'
    elif kind=='case':s['caseId']='CASE-B'
    elif kind=='evidence':s['evidenceId']='EV-B'
    elif kind=='source_version':s['sourceStateDigest']='c'*64
    elif kind=='current_hash':s['expectedCurrentSha256']='d'*64
    elif kind=='page_hash':a['derivative']['pages'][0]['textSha256']='f'*64
    elif kind=='page_index':a['derivative']['pages'][0]['physicalPage']=2
    elif kind=='page_count':a['derivative']['pageCount']=True
    elif kind=='tool':a['derivative']['tool']='other'
    elif kind=='method':a['derivative']['method']='ocr'
    elif kind=='artifact_hash':a['artifactSha256']='f'*64
    with pytest.raises(BindingError):validate(a,s,pdf)

def test_recomputed_derivative_still_cannot_change_source():
    pdf,s,d=fixture();a=build(s,pdf,d);a['sourceBinding']['expectedCurrentSha256']=a['derivativeContentSha256']
    body={k:v for k,v in a.items() if k!='artifactSha256'};a['artifactSha256']=digest(canonical(body))
    with pytest.raises(BindingError):validate(a,s,pdf)

def test_custody_instruction_rejected():
    pdf,s,d=fixture();a=build(s,pdf,d);a['custody']={'kind':'Change','sha256':a['derivativeContentSha256']}
    with pytest.raises(BindingError):validate(a,s,pdf)

def test_empty_page_label():
    pdf,s,d=fixture();p=d['pages'][0];p.update(text='\f',textSha256=digest(b'\f'),byteLength=1,status='no_selectable_text')
    assert validate(build(s,pdf,d),s,pdf)

def test_public_pdf_derivative_binding_read_only():
    from pathlib import Path
    import importlib.util
    root=Path(__file__).resolve().parents[2]
    spec=importlib.util.spec_from_file_location('pdf_deriver_binding_test',root/'tests_acceptance/PDF_TEXT_LAYER_CANDIDATE/derive.py')
    import sys
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    path=root/'reports/yangze22/report.pdf';pdf=path.read_bytes();d=module.derive(pdf)
    s={'caseId':'OFFLINE-PUBLIC-TEST','evidenceId':'TECHNICAL-TEST-ID','registeredSha256':digest(pdf),'expectedCurrentSha256':digest(pdf),'sourceStateDigest':digest(b'synthetic source binding, not database')}
    a=build(s,pdf,d)
    assert validate(a,s,pdf) and len(a['derivative']['pages'])==53
    assert path.read_bytes()==pdf
