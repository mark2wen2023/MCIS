import json
import pytest
from fastapi import HTTPException
from mcis_service.agents import extraction as e
from mcis_service.agents.extraction_review_fixture import document

SOURCE='原文🚢：共计约 12.5 吨\n燃油泄漏。'
ITEM={'kind':'Observation','subject':'spill','summary':'报告记载约12.5吨，待核实','claim':{'valueType':'Scalar','scalar':12.5,'unit':'吨'},'round':1,'field':'Answer','quote':'约 12.5 吨\n燃油泄漏'}

def record():
    doc=document();doc['turns']=[{'round':1,'question':'报告原文','answer':SOURCE,'sensitiveFragments':[]}];return doc

def test_exact_pdf_linebreak_utf16_mapping():
    doc=record();payload=e.parse_output(json.dumps({'statements':[ITEM]}),doc)
    statements,citations=e.checked_statements(payload,doc,{})
    span=statements[0]['span'];raw=SOURCE.encode('utf-16-le')
    assert raw[span['start']*2:(span['start']+span['length'])*2].decode('utf-16-le')==ITEM['quote']
    assert '\n' in citations[0]['quote']

@pytest.mark.parametrize('quote',['约 12.5 吨燃油泄漏','约 12.5 吨 燃油泄漏','约12.5吨\n燃油泄漏'])
def test_no_silent_normalization(quote):
    doc=record();payload=e.parse_output(json.dumps({'statements':[{**ITEM,'quote':quote}]}),doc)
    with pytest.raises(HTTPException):e.checked_statements(payload,doc,{})

def test_scalar_string_rejected():
    doc=record()
    with pytest.raises(HTTPException):e.parse_output(json.dumps({'statements':[{**ITEM,'claim':{**ITEM['claim'],'scalar':'12.5'}}]}),doc)

def test_prompt_requests_format_not_relaxed_validator():
    system=e.prompt(record(),{})[0]['content']
    assert 'character-for-character' in system and 'JSON number' in system
