"""Independent comment/observation boundary and compatible quoted-data probes."""
import os
import pytest
from .conftest import H
from .test_registered_align_preview import register,request,URL
from mcis_service.timeline import align_preview

@pytest.mark.parametrize('raw',[
 b'note,utc,heading\r\nnormal,2026-05-18T06:14:00Z,50\r\n#later,2026-05-18T06:15:00Z,90\r\n',
 b'note,utc,heading\rnormal,2026-05-18T06:14:00Z,50\r#later,2026-05-18T06:15:00Z,90\r',
 b'#note,utc,heading\nnormal,2026-05-18T06:15:00Z,90\n',
 b'note,utc,heading\nnormal,2026-05-18T06:14:00Z,50\n\t#later,2026-05-18T06:15:00Z,90',
 'note,utc,heading\n\u2003\ufeff\u2003#later,2026-05-18T06:15:00Z,90\n'.encode(),
])
def test_comment_header_or_later_record_rejected(client,monkeypatch,raw):
 receipt=register(client,raw)
 monkeypatch.setattr(align_preview,'core_run',lambda *_:pytest.fail('must reject before dispatch'))
 r=client.post(URL,headers=H(),json=request(receipt))
 assert r.status_code==422,r.text
 assert r.json()['code']=='TIMELINE_SOURCE_CSV'
 path=client.app.state.settings.blob_dir/receipt['caseId']/receipt['evidence']['relativePath']
 assert path.read_bytes()==raw

@pytest.mark.parametrize('header,note,newline',[
 ('"#note",utc,heading','"#memo"','\r\n'),
 ('note,utc,heading','"#memo, still data"','\n'),
 ('note,utc,heading','" #memo"','\r\n'),
 ('note,utc,heading','ordinary #memo','\n'),
])
def test_quoted_hash_and_internal_hash_remain_observations(client,header,note,newline):
 wrapper=os.environ.get('MCIS_ACCEPTANCE_CORE')
 if not wrapper:pytest.skip('requires actual W2')
 client.app.state.settings.core_cmd=wrapper
 raw=(header+newline+note+',2026-05-18T06:15:00Z,90'+newline).encode()
 a=register(client,raw);b=register(client,b'utc,heading\n2026-05-18T06:15:00Z,50\n','second.csv')
 r=client.post(URL,headers=H(),json={'sources':request(a)['sources']+request(b)['sources']})
 assert r.status_code==200,r.text
 assert r.json()['result']['conflicts'][0]['delta']==40
 assert r.json()['observationApproval']=='not_assessed'
