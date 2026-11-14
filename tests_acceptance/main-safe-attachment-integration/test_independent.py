"""Independent synthetic combined-branch API tests; no remote exploit claim."""
import base64
import hashlib
import io
import zipfile
from urllib.parse import quote

import pytest
from sqlalchemy import select
from mcis_service.audit.models import AuditEventRow
from mcis_service.evidence.models import CustodyEventRow
from tests.test_working_record_archive import client_at, exported, imported, ROOT, CID, HEAD
from tests.test_restored_attachment_filename import attach

LIMITED = {**HEAD, 'X-MCIS-Role': 'Investigator'}


def container(prefix=b''):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as z: z.writestr('synthetic.txt', b'synthetic container content')
    return prefix + stream.getvalue()


def legacy(c, raw):
    body = {'title':'Synthetic old registration','source':'Synthetic','extractedBy':'Independent',
        'extractedUtc':'2026-01-01T00:00:00Z','relativePath':'evidence/EV-001/renamed.bin',
        'category':'Other','contentBase64':base64.b64encode(raw).decode()}
    r = c.post(ROOT+'/evidence', headers=HEAD, json=body)
    assert r.status_code == 201, r.text
    return r.json()


def counts(c):
    with c.app.state.db.session() as s:
        return s.query(AuditEventRow).count(), s.query(CustodyEventRow).count()


@pytest.mark.parametrize('prefix', [b'', b'prefix-not-extension-dependent'])
def test_legacy_container_export_cannot_bypass_individual_gate(tmp_path, prefix):
    with client_at(tmp_path/'origin', True) as c:
        raw = container(prefix); item = legacy(c, raw)
        before = counts(c)
        assert c.get(ROOT+'/evidence/'+item['evidenceId']+'/content', headers=LIMITED).status_code == 403
        response = c.get(ROOT+'/export', headers=LIMITED)
        assert response.status_code == 403, 'legacy export bypassed container permission: '+str(response.status_code)
        assert counts(c) == before
        lead = c.get(ROOT+'/export', headers=HEAD)
        assert lead.status_code == 200, lead.text
        assert zipfile.ZipFile(io.BytesIO(lead.content)).read(item['relativePath']) == raw


def test_same_verified_bytes_reach_container_gate(tmp_path, monkeypatch):
    from mcis_service.evidence import recorded_content
    with client_at(tmp_path/'origin', True) as c:
        raw = container(); item = legacy(c, raw)
        original = recorded_content.read_content
        def after_read(path):
            result = original(path); path.write_bytes(b'no longer a zip on disk'); return result
        monkeypatch.setattr(recorded_content, 'read_content', after_read)
        before = counts(c)
        r = c.get(ROOT+'/evidence/'+item['evidenceId']+'/content', headers=LIMITED)
        assert r.status_code == 403 and counts(c) == before


@pytest.mark.parametrize('route', ['content','export'])
def test_same_inode_tamper_prevents_delivery_and_success_audit(tmp_path, route):
    with client_at(tmp_path/'origin', True) as c:
        raw = container(); item = legacy(c, raw)
        path = c.app.state.settings.blob_dir/CID/item['relativePath']
        path.write_bytes(b'tampered to plain bytes')
        before = counts(c)
        url = ROOT+'/export' if route=='export' else ROOT+'/evidence/'+item['evidenceId']+'/content'
        r = c.get(url, headers=HEAD)
        assert r.status_code == 409 and r.json()['code'] == 'EVIDENCE_CONTENT_MISMATCH'
        assert counts(c) == before


def test_restored_container_keeps_filename_hash_denial_and_inactive_receipt(tmp_path):
    name = '调查归档 “副本” 😀.zip'; raw = container()
    with client_at(tmp_path/'origin', True) as c:
        receipt = attach(c, raw, name); archive = exported(c)
    with client_at(tmp_path/'restored') as c:
        imported(c, archive); before = counts(c)
        url = ROOT+'/archive-history/evidence/'+receipt['evidenceId']+'/content'
        denied = c.get(url, headers=LIMITED)
        assert denied.status_code == 403 and 'content-disposition' not in denied.headers
        assert counts(c) == before
        r = c.get(url, headers=HEAD)
        assert r.status_code == 200 and r.content == raw
        assert r.headers['x-sha256'] == hashlib.sha256(raw).hexdigest()
        assert r.headers['content-disposition'] == 'attachment; filename="historical-source.bin"; filename*=UTF-8\'\''+quote(name,safe='')
        assert c.get(ROOT+'/evidence-intakes/'+receipt['requestDigest'], headers=HEAD).status_code == 409


def test_container_gate_error_rolls_back_without_access(tmp_path, monkeypatch):
    from mcis_service.report_output import attachment_access
    from mcis_service.common.context import problem
    with client_at(tmp_path/'origin', True) as c:
        item=legacy(c,container()); before=counts(c)
        def fail(*args): raise problem(503,'SYNTHETIC_GATE_ERROR','synthetic')
        monkeypatch.setattr(attachment_access,'protect_container',fail)
        r=c.get(ROOT+'/evidence/'+item['evidenceId']+'/content',headers=HEAD)
        assert r.status_code==503 and counts(c)==before


def test_plain_legacy_file_remains_allowed_in_old_export(tmp_path):
    with client_at(tmp_path/'origin',True) as c:
        raw=b'ordinary synthetic text'; item=legacy(c,raw)
        response=c.get(ROOT+'/export',headers=LIMITED)
        assert response.status_code==200,response.text
        assert zipfile.ZipFile(io.BytesIO(response.content)).read(item['relativePath'])==raw
        response=c.get(ROOT+'/evidence/'+item['evidenceId']+'/content',headers=LIMITED)
        assert response.status_code==200 and response.content==raw


@pytest.mark.parametrize('route',['content','export'])
def test_saved_policy_revocation_blocks_combined_container_delivery(tmp_path,route):
    from mcis_service.redaction.policy import default_policy
    with client_at(tmp_path/'origin',True) as c:
        item=legacy(c,container()); policy=default_policy()
        policy['matrix']['LeadInvestigator']['audit']='Deny'
        changed=c.put(ROOT+'/access-policy',headers=HEAD,json=policy)
        assert changed.status_code==200,changed.text
        before=counts(c)
        url=ROOT+'/export' if route=='export' else ROOT+'/evidence/'+item['evidenceId']+'/content'
        response=c.get(url,headers=HEAD)
        assert response.status_code==403 and counts(c)==before
