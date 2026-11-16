"""Constructed OCR arrays, not a real recognizer run."""
import copy,json
import pytest
from mcis_service.image_review.ppocr import convert
from .test_image_review_candidate import candidate,digest

def fixture():
    raw=json.dumps({'page_index':None,'rec_texts':['','ship 22'],'rec_scores':[0.2,0.9],
        'rec_boxes':[[0,0,20,20],[20,20,40,40]],'rec_polys':[[[0,0],[20,0],[20,20]],[[20,20],[40,20],[40,40]]]}).encode()
    original=candidate();source=original['source'];source['raw_sha256']=digest(raw)
    return raw,source,original['recognizer']

def test_adapter_preserves_blank_and_null_without_confirming():
    raw,source,rec=fixture();before=copy.deepcopy(source)
    result=convert(raw,source,rec)
    assert source==before and result['raw_page_index'] is None
    assert result['text_lines'][0]['text']=='' and result['text_lines'][0]['is_blank'] is True
    assert all(x['confirmed'] is False for x in result['text_lines'])
    assert result['source']['raw_sha256']==digest(raw)

def test_adapter_requires_exact_raw_version():
    raw,source,rec=fixture();source['raw_sha256']='a'*64
    with pytest.raises(ValueError):convert(raw,source,rec)

def test_adapter_rejects_array_length_mismatch():
    raw,source,rec=fixture();obj=json.loads(raw);obj['rec_scores']=[];raw=json.dumps(obj).encode();source['raw_sha256']=digest(raw)
    with pytest.raises(ValueError):convert(raw,source,rec)
