"""Tests existing intake lifecycle facts, not an implemented approval service."""
import pytest
from .conftest import H
from .test_registered_align_preview import register,request,URL,RAW
from .test_align_preview_w41 import result
from mcis_service.timeline import align_preview
from mcis_service.evidence import service


def test_same_sha_change_is_not_a_fresh_trusted_run(client,monkeypatch):
    receipt=register(client)
    with client.app.state.db.session() as s:
        service.append_custody(s,case_id=receipt['caseId'],evidence_id=receipt['evidenceId'],
            kind='Change',operator='test investigator',role='LeadInvestigator',
            sha256=receipt['sourceSha256'],previous_sha256=receipt['sourceSha256'],
            detail='same bytes do not erase custody change')
    monkeypatch.setattr(align_preview,'core_run',lambda *_:pytest.fail('changed intake must reject'))
    r=client.post(URL,headers=H(),json=request(receipt))
    assert r.status_code==409,r.text
    assert r.json()['code']=='INTAKE_INTEGRITY'
    path=client.app.state.settings.blob_dir/receipt['caseId']/receipt['evidence']['relativePath']
    assert path.read_bytes()==RAW


def test_access_log_does_not_invalidate_byte_snapshot_or_approve_it(client,monkeypatch):
    receipt=register(client)
    with client.app.state.db.session() as s:
        service.append_custody(s,case_id=receipt['caseId'],evidence_id=receipt['evidenceId'],
            kind='Access',operator='test investigator',role='Investigator',
            sha256=receipt['sourceSha256'],detail='read-only review preparation')
    monkeypatch.setattr(align_preview,'core_run',lambda *args:result(args[2]))
    r=client.post(URL,headers=H(),json=request(receipt))
    assert r.status_code==200,r.text
    assert r.json()['observationApproval']=='not_assessed'
    assert r.json()['persisted'] is False
    assert r.json()['sourceSnapshots'][0]['sourceSha256']==receipt['sourceSha256']
