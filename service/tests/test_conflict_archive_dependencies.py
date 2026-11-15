"""Synthetic ordinary dependency characterization; no archive enabling or security probes."""
import hashlib
from sqlalchemy import select
from mcis_service.audit.models import AuditEventRow
from mcis_service.db import put_doc
from mcis_service.timeline.models import ConflictRow
from mcis_service.evidence.models import EvidenceRow
from mcis_service.timeline.revisions import digest
from .conflict_version_helpers import checked
from .test_working_record_archive import client_at,ROOT,CID,populate
from .test_conflict_archive_readiness import body
from .test_consultation_archive_readiness import state


def test_new_multiversion_has_audit_binding_but_export_remains_closed(tmp_path):
    with client_at(tmp_path/'source',True) as c:
        checked(c,'post',ROOT+'/conflicts',body('Synthetic A'),201)
        checked(c,'patch',ROOT+'/conflicts/C-01',{'resolution':'Synthetic long note '*80})
        checked(c,'post',ROOT+'/conflicts',body('Synthetic B'),201)
        h=checked(c,'get',ROOT+'/conflicts/C-01/revisions').json()
        assert len(h['revisions'])==3 and h['coverage']=='captured-from-creation'
        with c.app.state.db.session() as s:
            for r in h['revisions']:
                a=s.scalars(select(AuditEventRow).where(AuditEventRow.case_id==CID,AuditEventRow.seq==r['auditSeq'])).one()
                assert hashlib.sha256(a.line.encode()).hexdigest()==r['auditLineSha256']
                assert (a.entity_type,a.entity_id)==('conflict','C-01')
        before=state(c)
        response=checked(c,'get',ROOT+'/export',status=409)
        assert response.json()['code']=='ARCHIVE_RESTORE_UNSUPPORTED' and state(c)==before


def test_registered_source_binding_does_not_contain_registry_preimage(tmp_path):
    with client_at(tmp_path/'source',True) as c:
        _,receipt,*_=populate(c)
        value=body();value['a']['evidenceId']=receipt['evidenceId']
        checked(c,'post',ROOT+'/conflicts',value,201)
        first=checked(c,'get',ROOT+'/conflicts/C-01/revisions').json()['revisions'][0]
        with c.app.state.db.session() as s:
            row=s.scalars(select(EvidenceRow).where(EvidenceRow.case_id==CID,EvidenceRow.key==receipt['evidenceId'])).one()
            original=dict(row.doc)
            # Explicit constructed legacy registry evolution, NOT a claimed product endpoint.
            put_doc(s,EvidenceRow,CID,row.key,{**original,'title':'Synthetic later registry title'})
        checked(c,'patch',ROOT+'/conflicts/C-01',{'resolution':'Synthetic subsequent explanation'})
        latest=checked(c,'get',ROOT+'/conflicts/C-01/revisions').json()['revisions'][-1]
        source=latest['afterSources']['a']
        assert source==first['afterSources']['a']
        assert source['registryDocSha256']==digest(original) and source['bytesVerified'] is False
        assert not any(k in source for k in ('registryDoc','originalBytes','relativePath'))
        with c.app.state.db.session() as s:
            current=s.scalars(select(EvidenceRow).where(EvidenceRow.case_id==CID,EvidenceRow.key==receipt['evidenceId'])).one().doc
            assert digest(current)!=source['registryDocSha256']


def test_legacy_unknown_stays_unknown_with_forward_history(tmp_path):
    with client_at(tmp_path/'source',True) as c:
        with c.app.state.db.session() as s:put_doc(s,ConflictRow,CID,'C-01',{**body(),'caseId':CID})
        h=checked(c,'get',ROOT+'/conflicts/C-01/revisions').json()
        assert h['coverage']=='unknown-before-capture' and h['revisions']==[]
        checked(c,'patch',ROOT+'/conflicts/C-01',{'resolution':'Synthetic forward revision'})
        h=checked(c,'get',ROOT+'/conflicts/C-01/revisions').json()
        assert h['coverage']=='unknown-before-capture' and h['revisions'][0]['beforeSources'] is None
        before=state(c);checked(c,'get',ROOT+'/export',status=409);assert state(c)==before
