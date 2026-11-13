"""Independent physical/logical record boundary probes; no core implementation changes."""
import os
import pytest
from .conftest import H
from .test_registered_align_preview import register,request,URL
from mcis_service.timeline import align_preview

@pytest.mark.parametrize('raw',[
 b'utc,heading,"unused\nheader"\n2026-05-18T06:15:00Z,45,note\n',
 b'utc,heading,"unused\r\nheader"\n2026-05-18T06:15:00Z,45,note\n',
 b'utc,heading,"unused\rheader"\n2026-05-18T06:15:00Z,45,note\n',
 b'utc,heading,note\n"2026-05-18T06:15:00Z\n2026-05-18T06:16:00Z",45,note\n',
 b'utc,heading,note\n2026-05-18T06:15:00Z,"45\n90",note\n',
 b'utc,heading,note\n2026-05-18T06:15:00Z,45,valid\n2026-05-18T06:16:00Z,50,"later\n2026-05-18T06:17:00Z,90,end"\n',
])
def test_logical_multiline_record_fails_before_dispatch(client,monkeypatch,raw):
 receipt=register(client,raw)
 monkeypatch.setattr(align_preview,'core_run',lambda *_:pytest.fail('must not dispatch'))
 r=client.post(URL,headers=H(),json=request(receipt))
 assert r.status_code==422,r.text
 assert r.json()['code']=='TIMELINE_SOURCE_CSV'
 path=client.app.state.settings.blob_dir/receipt['caseId']/receipt['evidence']['relativePath']
 assert path.read_bytes()==raw

@pytest.mark.parametrize('newline',['\n','\r\n'])
def test_multiple_real_records_not_mistaken_for_multiline_cell(client,newline):
 wrapper=os.environ.get('MCIS_ACCEPTANCE_CORE')
 if not wrapper:pytest.skip('requires actual W2')
 client.app.state.settings.core_cmd=wrapper
 rows=['utc,heading,note','2026-05-18T06:15:00Z,90,"literal \\n is not newline"','2026-05-18T06:16:00Z,90,""']
 a=register(client,(newline.join(rows)+newline).encode())
 b=register(client,(newline.join(['utc,heading','2026-05-18T06:15:00Z,50','2026-05-18T06:16:00Z,50'])+newline).encode(),'second.csv')
 r=client.post(URL,headers=H(),json={'sources':request(a)['sources']+request(b)['sources']})
 assert r.status_code==200,r.text
 assert r.json()['result']['conflicts']
 assert all(c['delta']==40 for c in r.json()['result']['conflicts'])
 assert r.json()['observationApproval']=='not_assessed'
