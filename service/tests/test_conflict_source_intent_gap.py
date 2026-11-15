"""Ordinary synthetic registry evolution, not original-file or security verification."""
from mcis_service.db import put_doc
from mcis_service.evidence.models import EvidenceRow
from mcis_service.evidence.service import append_custody
from .test_working_record_archive import client_at, ROOT, CID, HEAD
from .test_conflict_archive_readiness import body


def test_edit_token_does_not_bind_reviewed_evidence_version(tmp_path):
    with client_at(tmp_path/'synthetic', True) as c:
        with c.app.state.db.session() as s:
            put_doc(s,EvidenceRow,CID,'EV-001',{'caseId':CID,'evidenceId':'EV-001','sha256':'a'*64,'confidentiality':'Normal'})
        value=body(); value['a']['evidenceId']='EV-001'
        assert c.post(ROOT+'/conflicts',headers=HEAD,json=value).status_code==201
        before=c.get(ROOT+'/conflicts:editable',headers=HEAD)
        assert before.status_code==200
        version=next(row['version'] for row in before.json() if row['conflict']['conflictId']=='C-01')
        with c.app.state.db.session() as s:
            append_custody(s,case_id=CID,evidence_id='EV-001',kind='Change',operator='Synthetic',role='LeadInvestigator',sha256='b'*64,previous_sha256='a'*64,detail='Synthetic registration update; no original bytes')
        listing=c.get(ROOT+'/conflicts:editable',headers=HEAD)
        assert listing.status_code==200
        assert next(row['version'] for row in listing.json() if row['conflict']['conflictId']=='C-01')==version
        value['a']['valueText']='Synthetic observation written from earlier screen'
        response=c.post(ROOT+'/conflicts',headers=HEAD,json={**value,'expectedVersion':version})
        assert response.status_code==201
        history=c.get(ROOT+'/conflicts/C-01/revisions',headers=HEAD)
        assert history.status_code==200
        revisions=history.json()['revisions']
        assert revisions[0]['afterSources']['a']['sha256']=='a'*64
        assert revisions[1]['beforeSources']['a']['sha256']=='a'*64
        assert revisions[1]['afterSources']['a']['sha256']=='b'*64
        assert revisions[1]['afterSources']['a']['bytesVerified'] is False
