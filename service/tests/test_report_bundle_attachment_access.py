"""Synthetic cases; real report ZIP generation, opaque registration and archive restore."""
import base64
import hashlib
import io
import zipfile
import pytest
from sqlalchemy import select
from mcis_service.evidence.models import CustodyEventRow
from mcis_service.db import put_doc
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from .test_report_output import origin, body as export_body, H, BASE, CID
from .test_evidence_intake_w42 import body as intake_body

INVESTIGATOR = {'X-MCIS-Role':'Investigator','X-MCIS-Operator':'Synthetic limited reader'}


def register(c, raw, name='renamed.bin'):
    body = intake_body(raw, fileName=name)
    preview = c.post(BASE+'/evidence-intakes:preview', headers=H, json=body)
    assert preview.status_code == 200, preview.text
    r = c.post(BASE+'/evidence-intakes:commit', headers=H,
               json={**body,'confirmed':True,'requestDigest':preview.json()['requestDigest']})
    assert r.status_code == 200, r.text
    return r.json()


def access_count(c):
    with c.app.state.db.session() as s:
        return len(s.scalars(select(CustodyEventRow).where(CustodyEventRow.kind=='Access')).all())


def download(c, receipt, route, headers):
    if route == 'intake':
        return c.post(BASE+'/evidence-intakes/'+receipt['requestDigest']+':download',
                      headers=headers,json={'purpose':'Synthetic explicit read'})
    return c.get(BASE+'/evidence/'+receipt['evidenceId']+'/content',headers=headers)


@pytest.mark.parametrize('route', ['intake','legacy'])
def test_report_bundle_copy_cannot_downgrade_report_access(origin,route):
    c, report, path = origin
    assert c.get(path+':preview',headers=INVESTIGATOR).status_code == 403
    generated = c.post(path, headers=H, json=export_body(c,path))
    assert generated.status_code == 200
    receipt = register(c, generated.content)
    before = access_count(c)
    denied = download(c,receipt,route,INVESTIGATOR)
    assert denied.status_code == 403
    assert access_count(c) == before
    assert denied.headers['cache-control'] == 'no-store'
    allowed = download(c,receipt,route,H)
    assert allowed.status_code == 200
    assert allowed.content == generated.content
    assert access_count(c) == before+1


@pytest.mark.parametrize('route',['intake','legacy'])
@pytest.mark.parametrize('variant',['empty','compressed','prefixed','truncated'])
def test_zip_classification_without_extension_or_extraction(origin,route,variant,monkeypatch):
    c,_,_=origin
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
        if variant!='empty':z.writestr('opaque.txt',b'A'*10000)
    raw=stream.getvalue()
    if variant=='prefixed':raw=b'self-extracting-prefix'+raw
    if variant=='truncated':raw=raw[:24]
    receipt=register(c,raw)
    def no_extract(*a,**kw):raise AssertionError('must not decompress')
    monkeypatch.setattr(zipfile.ZipFile,'read',no_extract)
    before=access_count(c)
    assert download(c,receipt,route,INVESTIGATOR).status_code==403
    assert access_count(c)==before
    assert download(c,receipt,route,H).content==raw


@pytest.mark.parametrize('route',['intake','legacy'])
def test_nonzip_opaque_copy_unchanged(origin,route):
    c,_,_=origin
    raw=b'plain synthetic text, not a classified report'
    receipt=register(c,raw,'misleading.zip')
    r=download(c,receipt,route,INVESTIGATOR)
    assert r.status_code==200 and r.content==raw


@pytest.mark.parametrize('route',['intake','legacy'])
def test_saved_policy_revocation_prevents_copy_download(origin,route):
    c,_,path=origin
    generated=c.post(path,headers=H,json=export_body(c,path));assert generated.status_code==200
    receipt=register(c,generated.content)
    with c.app.state.db.session() as s:
        policy=default_policy();policy['matrix']['LeadInvestigator']['audit']='Deny'
        put_doc(s,AccessPolicyRow,CID,'policy',policy)
    before=access_count(c)
    assert download(c,receipt,route,H).status_code==403
    assert access_count(c)==before


def test_whole_report_zip_explicit_registration_and_restoration(origin,tmp_path):
    from fastapi.testclient import TestClient
    from mcis_service.main import create_app
    from .conftest import make_settings
    c,_,path=origin
    generated=c.post(path,headers=H,json=export_body(c,path));assert generated.status_code==200
    raw=generated.content
    receipt=register(c,raw,'report-output.zip')
    package=c.get(BASE+'/export',headers=H);assert package.status_code==200,package.text
    with TestClient(create_app(make_settings(tmp_path/'restore',False))) as restored:
        payload={'contentBase64':base64.b64encode(package.content).decode()}
        r=restored.post('/api/v1/packages/intakes:commit',headers=H,
                        json={**payload,'confirmed':True,'sourceSha256':hashlib.sha256(package.content).hexdigest()})
        assert r.status_code==200,r.text
        url=BASE+'/archive-history/evidence/'+receipt['evidenceId']+'/content'
        assert restored.get(url,headers=INVESTIGATOR).status_code==403
        result=restored.get(url,headers=H)
        assert result.status_code==200 and result.content==raw
        assert result.headers['x-sha256']==hashlib.sha256(raw).hexdigest()
        with zipfile.ZipFile(io.BytesIO(result.content)) as z:
            assert z.namelist()==['report.docx','report.json','audit.json','manifest.json']
        assert restored.get(BASE+'/evidence-intakes/'+receipt['requestDigest'],headers=H).status_code==409
