"""Independent header ambiguity rejection and legitimate time-column compatibility."""
import os
import pytest
from .conftest import H
from .test_registered_align_preview import register, request, URL, RAW
from mcis_service.timeline import align_preview

@pytest.mark.parametrize('headers,row,time_column',[
 ('utc,UTC,heading','2026-05-18T06:15:00Z,2026-05-18T06:16:00Z,45','UTC'),
 ('utc, utc ,heading','2026-05-18T06:15:00Z,2026-05-18T06:16:00Z,45',' utc '),
 ('utc,heading,note,NOTE','2026-05-18T06:15:00Z,45,a,b','utc'),
 ('utc,heading,note, note ','2026-05-18T06:15:00Z,45,a,b','utc'),
 ('utc,heading,straße,STRASSE','2026-05-18T06:15:00Z,45,a,b','utc'),
 ('utc,heading,\u00a0note,NOTE\u00a0','2026-05-18T06:15:00Z,45,a,b','utc'),
])
def test_independent_alias_blocks_dispatch(client,monkeypatch,headers,row,time_column):
 raw=(headers+'\n'+row+'\n').encode();receipt=register(client,raw);body=request(receipt);body['sources'][0]['csvMapping']['timeColumn']=time_column
 monkeypatch.setattr(align_preview,'core_run',lambda *_:pytest.fail('aliases must not reach core'))
 response=client.post(URL,headers=H(),json=body)
 assert response.status_code==422,response.text
 assert response.json()['code']=='TIMELINE_SOURCE_CSV'
 path=client.app.state.settings.blob_dir/receipt['caseId']/receipt['evidence']['relativePath']
 assert path.read_bytes()==raw

@pytest.mark.parametrize('time_column',['UTC',' utc '])
def test_independent_unique_time_name_actual_core(client,time_column):
 wrapper=os.environ.get('MCIS_ACCEPTANCE_CORE')
 if not wrapper:pytest.skip('requires actual W2')
 client.app.state.settings.core_cmd=wrapper
 raw=(time_column+',heading,note\n2026-05-18T06:15:00Z,90,ignored\n').encode()
 a=register(client,raw);b=register(client,RAW.replace(b'45',b'50'),'second.csv')
 body={'sources':request(a)['sources']+request(b)['sources']};body['sources'][0]['csvMapping']['timeColumn']=time_column
 response=client.post(URL,headers=H(),json=body)
 assert response.status_code==200,response.text
 assert response.json()['result']['conflicts'][0]['delta']==40
