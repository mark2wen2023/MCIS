"""Integration regressions using synthetic files and actual APIs, no remote mutation claim."""
import base64,io,zipfile
import pytest
from .test_evidence_intake_w42 import local,CASE
from .conftest import H
from mcis_service.audit.models import AuditEventRow
from mcis_service.evidence.models import CustodyEventRow
from mcis_service.evidence import service
URL=f'/api/v1/cases/{CASE}'

def archive_bytes(docx=False):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:z.writestr('word/document.xml' if docx else 'report.txt',b'synthetic restricted report')
    return stream.getvalue()

def register(c,raw):
    r=c.post(URL+'/evidence',headers=H('LeadInvestigator'),json={'title':'synthetic','source':'synthetic','extractedBy':'synthetic','extractedUtc':'2026-01-01T00:00:00Z','relativePath':'evidence/EV-001/source.bin','contentBase64':base64.b64encode(raw).decode()})
    assert r.status_code==201,r.text
    return r.json()

def counts(app):
    with app.state.db.session() as s:return s.query(AuditEventRow).count(),s.query(CustodyEventRow).filter_by(kind='Access').count()

@pytest.mark.parametrize('docx',[False,True])
def test_legacy_container_permission_also_covers_case_export(local,docx):
    c,app=local;raw=archive_bytes(docx);register(c,raw);before=counts(app)
    assert c.get(URL+'/evidence/EV-001/content',headers=H()).status_code==403
    r=c.get(URL+'/export',headers=H())
    assert r.status_code==403, 'legacy package must not bypass container permission: '+str(r.status_code)
    assert counts(app)==before
    allowed=c.get(URL+'/export',headers=H('LeadInvestigator'))
    assert allowed.status_code==200,allowed.text
    assert zipfile.ZipFile(io.BytesIO(allowed.content)).read('evidence/EV-001/source.bin')==raw

@pytest.mark.parametrize('route',['content','export'])
def test_container_modified_to_plain_cannot_evade_digest(local,route):
    c,app=local;register(c,archive_bytes());path=service.blob_path(app.state.settings.blob_dir,CASE,'evidence/EV-001/source.bin')
    path.write_bytes(b'plain synthetic replacement');before=counts(app)
    url=URL+('/export' if route=='export' else '/evidence/EV-001/content')
    r=c.get(url,headers=H('LeadInvestigator'))
    assert r.status_code==409 and r.json()['code']=='EVIDENCE_CONTENT_MISMATCH'
    assert counts(app)==before

@pytest.mark.parametrize('denied_category',['evidence_meta','audit'])
def test_plain_legacy_export_respects_revoked_policy(local,denied_category):
    from mcis_service.redaction.policy import default_policy
    c,app=local;register(c,b'plain synthetic evidence')
    policy=default_policy();policy['matrix']['Investigator'][denied_category]='Deny'
    response=c.put(URL+'/access-policy',headers=H('LeadInvestigator'),json=policy)
    assert response.status_code==200,response.text
    before=counts(app)
    r=c.get(URL+'/export',headers=H())
    assert r.status_code==403, 'plain legacy export ignores '+denied_category+': '+str(r.status_code)
    assert counts(app)==before
