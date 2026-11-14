"""Prevent Python validation and W2 lookup from selecting different columns."""
import os
import pytest
from .conftest import H
from .test_registered_align_preview import register, request, URL, RAW
from mcis_service.timeline import align_preview

@pytest.mark.parametrize('alias', ['Heading', ' heading', 'heading ', ' HEADING '])
def test_ambiguous_header_never_reaches_core(client, monkeypatch, alias):
    raw=('utc,heading,'+alias+'\n2026-05-18T06:15:00Z,45,90\n').encode()
    receipt=register(client,raw)
    body=request(receipt)
    body['sources'][0]['csvMapping']['columns'][0]['column']=alias
    monkeypatch.setattr(align_preview,'core_run',lambda *_:pytest.fail('ambiguous column must not reach core'))
    r=client.post(URL,headers=H(),json=body)
    assert r.status_code==422,r.text
    assert r.json()['code']=='TIMELINE_SOURCE_CSV'
    path=client.app.state.settings.blob_dir/receipt['caseId']/receipt['evidence']['relativePath']
    assert path.read_bytes()==raw

@pytest.mark.parametrize('name', ['Heading', ' heading '])
def test_unique_header_preserved_with_actual_core(client,name):
    wrapper=os.environ.get('MCIS_ACCEPTANCE_CORE')
    if not wrapper:pytest.skip('requires actual W2 wrapper')
    client.app.state.settings.core_cmd=wrapper
    a=register(client,('utc,'+name+'\n2026-05-18T06:15:00Z,90\n').encode())
    b=register(client,RAW.replace(b'45',b'50'),'second.csv')
    body={'sources':request(a)['sources']+request(b)['sources']}
    body['sources'][0]['csvMapping']['columns'][0]['column']=name
    r=client.post(URL,headers=H(),json=body)
    assert r.status_code==200,r.text
    assert r.json()['result']['conflicts'][0]['delta']==40
    assert r.json()['observationApproval']=='not_assessed'
