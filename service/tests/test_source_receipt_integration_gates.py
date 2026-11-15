"""Ordinary policy compatibility checks; no original files or restricted probes."""
import pytest
from fastapi import HTTPException
from mcis_service.db import put_doc
from mcis_service.evidence.models import EvidenceRow
from research.conflict_source_intent.registry_receipt import RegistryReceipts
from .test_working_record_archive import client_at, ROOT, CID, HEAD
from .test_conflict_archive_readiness import body
from .conftest import H


def test_existing_editable_permission_is_not_receipt_permission(tmp_path):
    with client_at(tmp_path/'c',True) as c:
        with c.app.state.db.session() as s:
            put_doc(s,EvidenceRow,CID,'EV-A',{'caseId':CID,'evidenceId':'EV-A','sha256':'a'*64,'confidentiality':'Normal'})
        value=body();value['a']['evidenceId']='EV-A'
        assert c.post(ROOT+'/conflicts',headers=HEAD,json=value).status_code==201
        editable=c.get(ROOT+'/conflicts:editable',headers=H('Investigator','Synthetic'))
        assert editable.status_code==200
        assert any(row['conflict']['conflictId']=='C-01' for row in editable.json())
        with c.app.state.db.session() as s:
            with pytest.raises(HTTPException) as error:
                RegistryReceipts().issue(s,CID,'Investigator',['EV-A'])
            assert error.value.status_code==403


def test_legacy_missing_version_write_rejected_with_current_unchanged(tmp_path):
    with client_at(tmp_path/'c',True) as c:
        created=c.post(ROOT+'/conflicts',headers=HEAD,json=body())
        assert created.status_code==201
        reply=c.patch(ROOT+'/conflicts/C-01',headers=HEAD,json={'resolution':'Synthetic unsaved draft'})
        assert reply.status_code==428
        listing=c.get(ROOT+'/conflicts',headers=HEAD)
        assert listing.status_code==200
        assert next(row for row in listing.json() if row['conflictId']=='C-01')==created.json()


def test_registered_source_revision_audit_rollback_together(tmp_path,monkeypatch):
    from mcis_service.timeline import revisions
    from .test_consultation_archive_readiness import state
    with client_at(tmp_path/'c',True) as c:
        with c.app.state.db.session() as s:
            put_doc(s,EvidenceRow,CID,'EV-A',{'caseId':CID,'evidenceId':'EV-A','sha256':'a'*64,'confidentiality':'Normal'})
        value=body();value['a']['evidenceId']='EV-A'
        assert c.post(ROOT+'/conflicts',headers=HEAD,json=value).status_code==201
        editable=c.get(ROOT+'/conflicts:editable',headers=HEAD)
        assert editable.status_code==200
        token=next(row['version'] for row in editable.json() if row['conflict']['conflictId']=='C-01')
        before=state(c)
        history_before=c.get(ROOT+'/conflicts/C-01/revisions',headers=HEAD)
        assert history_before.status_code==200
        original=revisions.capture
        def fail_after_capture(s,case,key,*args):
            original(s,case,key,*args)
            captured=revisions.last(s,case,key)
            assert captured.doc['afterSources']['a']['sha256']=='a'*64
            assert captured.doc['auditSeq'] is not None
            raise RuntimeError('Synthetic rollback after source binding and audit capture')
        monkeypatch.setattr(revisions,'capture',fail_after_capture)
        reply=c.patch(ROOT+'/conflicts/C-01',headers=HEAD,json={'expectedVersion':token,'resolution':'Synthetic failed judgment'})
        assert reply.status_code==500
        assert state(c)==before
        history_after=c.get(ROOT+'/conflicts/C-01/revisions',headers=HEAD)
        assert history_after.status_code==200 and history_after.json()==history_before.json()
