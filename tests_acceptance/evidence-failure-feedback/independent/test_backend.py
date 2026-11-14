import pytest
from tests.test_evidence_intake_w42 import local,CASE,body,prepared,counts
URL=f'/api/v1/cases/{CASE}/evidence-intakes'

@pytest.mark.parametrize('change,code',[({'title':''},'INTAKE_METADATA'),({'confirmed':False},'INTAKE_CONFIRM'),({'contentBase64':'!!'},'INTAKE_BASE64'),({'requestDigest':'0'*64},'INTAKE_STALE')])
def test_prewrite_rejections_have_no_registration(local,change,code):
    client,app=local;request=prepared(client,body())
    response=client.post(URL+':commit',json={**request,**change})
    assert response.status_code==(409 if code=='INTAKE_STALE' else 422)
    assert response.json()['code']==code
    assert counts(app)==(0,0,0)
    assert not list(app.state.settings.blob_dir.rglob('source.bin'))


def test_committed_then_tampered_is_not_proof_of_noncommit(local):
    client,app=local;request=prepared(client,body())
    response=client.post(URL+':commit',json=request);assert response.status_code==200
    path=app.state.settings.blob_dir/CASE/'raw/evidence-intakes'/request['requestDigest']/'source.bin'
    path.write_bytes(b'synthetic changed content')
    before=counts(app);assert before==(1,1,1)
    rejected=client.post(URL+':commit',json=request)
    assert rejected.status_code==409 and rejected.json()['code']=='INTAKE_INTEGRITY'
    assert counts(app)==before and path.read_bytes()==b'synthetic changed content'
    recovered=client.get(URL+'/'+request['requestDigest'])
    assert recovered.status_code==409 and recovered.json()['code']=='INTAKE_INTEGRITY'
    assert counts(app)==before
