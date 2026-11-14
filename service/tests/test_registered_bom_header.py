"""The first parsed W2 header drops BOMs before its column lookup."""
import os
import pytest
from .conftest import H
from .test_registered_align_preview import register,request,URL
from mcis_service.timeline import align_preview

@pytest.mark.parametrize('first',['"\ufeffheading"','"\ufeff\ufeffheading"','"\ufeff HEADING "'])
def test_first_header_bom_alias_rejected(client,monkeypatch,first):
    raw=(first+',heading,utc\n90,45,2026-05-18T06:15:00Z\n').encode()
    receipt=register(client,raw)
    monkeypatch.setattr(align_preview,'core_run',lambda *_:pytest.fail('BOM alias must reject'))
    r=client.post(URL,headers=H(),json=request(receipt))
    assert r.status_code==422,r.text
    assert r.json()['code']=='TIMELINE_SOURCE_CSV'
    path=client.app.state.settings.blob_dir/receipt['caseId']/receipt['evidence']['relativePath']
    assert path.read_bytes()==raw

def test_regular_utf8_bom_actual_core(client):
    wrapper=os.environ.get('MCIS_ACCEPTANCE_CORE')
    if not wrapper:pytest.skip('requires actual W2')
    client.app.state.settings.core_cmd=wrapper
    a=register(client,b'\xef\xbb\xbfutc,heading\n2026-05-18T06:15:00Z,90\n')
    b=register(client,b'utc,heading\n2026-05-18T06:15:00Z,50\n','second.csv')
    r=client.post(URL,headers=H(),json={'sources':request(a)['sources']+request(b)['sources']})
    assert r.status_code==200,r.text
    assert r.json()['result']['conflicts'][0]['delta']==40
