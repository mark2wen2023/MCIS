"""A quoted note must not become an extra W2 measurement."""
import os
import pytest
from .conftest import H
from .test_registered_align_preview import register,request,URL
from mcis_service.timeline import align_preview

@pytest.mark.parametrize('newline',['\n','\r\n','\r'])
def test_multiline_unused_note_rejected(client,monkeypatch,newline):
    raw=('utc,heading,note\n2026-05-18T06:15:00Z,45,"memo'+newline+'2026-05-18T06:16:00Z,90,end"\n').encode()
    receipt=register(client,raw)
    monkeypatch.setattr(align_preview,'core_run',lambda *_:pytest.fail('multiline cell must not reach core'))
    r=client.post(URL,headers=H(),json=request(receipt))
    assert r.status_code==422,r.text
    assert r.json()['code']=='TIMELINE_SOURCE_CSV'
    path=client.app.state.settings.blob_dir/receipt['caseId']/receipt['evidence']['relativePath']
    assert path.read_bytes()==raw

@pytest.mark.parametrize('newline',['\n','\r\n'])
def test_single_line_quoted_csv_still_works(client,newline):
    wrapper=os.environ.get('MCIS_ACCEPTANCE_CORE')
    if not wrapper:pytest.skip('requires actual W2')
    client.app.state.settings.core_cmd=wrapper
    a=register(client,('"utc","heading",note'+newline+'"2026-05-18T06:15:00Z","90","memo, with ""quotes"""'+newline).encode())
    b=register(client,b'utc,heading\n2026-05-18T06:15:00Z,50\n','second.csv')
    r=client.post(URL,headers=H(),json={'sources':request(a)['sources']+request(b)['sources']})
    assert r.status_code==200,r.text
    assert r.json()['result']['conflicts'][0]['delta']==40
