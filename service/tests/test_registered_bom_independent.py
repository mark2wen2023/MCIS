"""Independent first-header-only BOM semantics probes."""
import os
import pytest
from .conftest import H
from .test_registered_align_preview import register,request,URL
from mcis_service.timeline import align_preview

@pytest.mark.parametrize('first',['\ufeffutc','\ufeff\ufeffUTC','\ufeff utc '])
def test_time_header_bom_alias_rejects_before_core(client,monkeypatch,first):
 raw=('"'+first+'",utc,heading\n2026-05-18T06:16:00Z,2026-05-18T06:15:00Z,45\n').encode()
 receipt=register(client,raw)
 monkeypatch.setattr(align_preview,'core_run',lambda *_:pytest.fail('must reject time alias before dispatch'))
 r=client.post(URL,headers=H(),json=request(receipt));assert r.status_code==422,r.text
 assert r.json()['code']=='TIMELINE_SOURCE_CSV'
 path=client.app.state.settings.blob_dir/receipt['caseId']/receipt['evidence']['relativePath'];assert path.read_bytes()==raw

@pytest.mark.parametrize('header,row,column,delta',[
 ('utc,"\ufeffheading",heading','2026-05-18T06:15:00Z,90,45','heading',5),
 ('utc,"\ufeffheading",heading','2026-05-18T06:15:00Z,90,45','\ufeffheading',40),
 ('" \ufeffheading",heading,utc','90,45,2026-05-18T06:15:00Z','heading',5),
])
def test_only_initial_bom_not_other_positions_are_removed(client,header,row,column,delta):
 wrapper=os.environ.get('MCIS_ACCEPTANCE_CORE')
 if not wrapper:pytest.skip('requires actual W2')
 client.app.state.settings.core_cmd=wrapper
 raw=(header+'\n'+row+'\n').encode();a=register(client,raw);b=register(client,b'utc,heading\n2026-05-18T06:15:00Z,50\n','second.csv')
 body={'sources':request(a)['sources']+request(b)['sources']};body['sources'][0]['csvMapping']['columns'][0]['column']=column
 r=client.post(URL,headers=H(),json=body);assert r.status_code==200,r.text
 assert r.json()['result']['conflicts'][0]['delta']==delta
 path=client.app.state.settings.blob_dir/a['caseId']/a['evidence']['relativePath'];assert path.read_bytes()==raw
