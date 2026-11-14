"""Do not silently drop observations whose first unused field starts with #."""
import os
import pytest
from .conftest import H
from .test_registered_align_preview import register,request,URL
from mcis_service.timeline import align_preview

@pytest.mark.parametrize('prefix',['#memo','  #memo','\ufeff#memo',' \ufeff  #memo'])
def test_comment_like_row_rejected_before_core(client,monkeypatch,prefix):
    raw=('note,utc,heading\n'+prefix+',2026-05-18T06:15:00Z,90\nnormal,2026-05-18T06:16:00Z,50\n').encode()
    receipt=register(client,raw)
    monkeypatch.setattr(align_preview,'core_run',lambda *_:pytest.fail('comment-like record must not run'))
    r=client.post(URL,headers=H(),json=request(receipt))
    assert r.status_code==422,r.text
    assert r.json()['code']=='TIMELINE_SOURCE_CSV'
    path=client.app.state.settings.blob_dir/receipt['caseId']/receipt['evidence']['relativePath']
    assert path.read_bytes()==raw

@pytest.mark.parametrize('prefix',['"#memo"','ordinary #memo'])
def test_non_comment_first_field_actual_core(client,prefix):
    wrapper=os.environ.get('MCIS_ACCEPTANCE_CORE')
    if not wrapper:pytest.skip('requires actual W2')
    client.app.state.settings.core_cmd=wrapper
    a=register(client,('note,utc,heading\n'+prefix+',2026-05-18T06:15:00Z,90\n').encode())
    b=register(client,b'utc,heading\n2026-05-18T06:15:00Z,50\n','second.csv')
    r=client.post(URL,headers=H(),json={'sources':request(a)['sources']+request(b)['sources']})
    assert r.status_code==200,r.text
    assert r.json()['result']['conflicts'][0]['delta']==40
