"""Synthetic combined legacy POST/GET/export/import; no identity or model claims."""
import base64,hashlib
import pytest
from .test_evidence_intake_w42 import local,counts
from .test_package_export_policy import URL,INV,LEAD
from .test_content_visibility import hidden


@pytest.mark.parametrize('raw',[b'',b'\x00\xffsynthetic binary\r\n'])
def test_invalid_then_valid_revoke_and_restore(local,empty_client,raw):
    c,app=local
    body={'title':'Synthetic combined','source':'Declared synthetic origin',
          'extractedBy':'Synthetic collector','extractedUtc':'2026-01-01T00:00:00Z',
          'relativePath':'evidence/combined.bin','confidentiality':'Restricted','contentBase64':'!!!!'}
    before=counts(app);paths=set(app.state.settings.blob_dir.rglob('*'))
    invalid=c.post(URL+'/evidence',headers=INV,json=body)
    assert invalid.status_code==422 and counts(app)==before
    assert set(app.state.settings.blob_dir.rglob('*'))==paths
    body['contentBase64']=base64.b64encode(raw).decode()
    item=c.post(URL+'/evidence',headers=INV,json=body)
    assert item.status_code==201 and item.json()['sha256']==hashlib.sha256(raw).hexdigest()
    eid=item.json()['evidenceId'];content=URL+'/evidence/'+eid+'/content'
    r=c.get(content,headers=INV);assert r.status_code==200 and r.content==raw
    assert c.put(URL+'/access-policy',headers=LEAD,json=hidden()).status_code==200
    before=counts(app)
    assert c.get(content,headers=INV).status_code==403
    assert c.get(URL+'/export',headers=INV).status_code==403
    assert counts(app)==before
    archive=c.get(URL+'/export',headers=LEAD);assert archive.status_code==200
    restored=empty_client.post('/api/v1/cases:import',headers=LEAD,content=archive.content)
    assert restored.status_code==201,restored.text
    assert empty_client.get(content,headers=INV).status_code==403
    assert empty_client.get(URL+'/export',headers=INV).status_code==403
    r=empty_client.get(content,headers=LEAD);assert r.status_code==200 and r.content==raw
    meta=empty_client.get(URL+'/evidence/'+eid,headers=LEAD).json()
    assert meta['source']==body['source'] and meta['sha256']==item.json()['sha256']
    assert empty_client.get(URL+'/audit:verify',headers=LEAD).json()['valid']
    assert empty_client.get(URL+'/custody:verify-chain',headers=LEAD).json()['valid']
