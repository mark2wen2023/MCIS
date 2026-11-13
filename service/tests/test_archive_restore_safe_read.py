"""Actual export/import keeps registered originals readable only as history."""
import base64
from fastapi.testclient import TestClient
from .conftest import C,H,make_settings
from .test_registered_align_preview import register,request,RAW,URL
from mcis_service.main import create_app


def test_original_archive_roundtrip_stays_historical(client,empty_client,tmp_path):
    case=client.get(C,headers=H()).json()
    assert empty_client.post('/api/v1/cases',headers=H(),json=case).status_code==201
    receipt=register(empty_client)
    exported=empty_client.get(C+'/export',headers=H('LeadInvestigator'))
    assert exported.status_code==200,exported.text
    encoded=base64.b64encode(exported.content).decode()
    with TestClient(create_app(make_settings(tmp_path/'restored',seed=False))) as target:
        preview=target.post('/api/v1/packages/intakes:preview',headers=H('LeadInvestigator'),json={'contentBase64':encoded})
        assert preview.status_code==200,preview.text
        committed=target.post('/api/v1/packages/intakes:commit',headers=H('LeadInvestigator'),json={'contentBase64':encoded,'sourceSha256':preview.json()['sourceSha256'],'confirmed':True})
        assert committed.status_code==200,committed.text
        history=target.get(C+'/archive-history/evidence/'+receipt['evidenceId']+'/content',headers=H('LeadInvestigator'))
        assert history.status_code==200,history.text
        assert history.content==RAW
        denied=target.get(C+'/archive-history/evidence/'+receipt['evidenceId']+'/content',headers=H('Public'))
        assert denied.status_code==403
        result=target.post(URL,headers=H('LeadInvestigator'),json=request(receipt))
        assert result.status_code==409,result.text
        assert result.json()['code']=='ARCHIVE_HISTORY_ONLY'
