"""Synthetic registry contract only; no original files or security probes."""
import pytest
from fastapi import HTTPException
from mcis_service.db import put_doc
from mcis_service.evidence.models import EvidenceRow
from mcis_service.evidence.service import append_custody
from research.conflict_source_intent.registry_receipt import RegistryReceipts
from .test_working_record_archive import client_at,CID


def seed(c):
    with c.app.state.db.session() as s:
        for k in ('EV-A','EV-B'):put_doc(s,EvidenceRow,CID,k,{'caseId':CID,'evidenceId':k,'sha256':'a'*64,'confidentiality':'Normal'})


def issue(g,c,ids=['EV-A','EV-B'],role='LeadInvestigator'):
    with c.app.state.db.session() as s:return g.issue(s,CID,role,ids)


def compare(g,c,token,ids=['EV-A','EV-B'],role='LeadInvestigator',case=CID):
    with c.app.state.db.session() as s:return g.compare(s,case,role,ids,token)


def test_unchanged_no_file_or_human_claim(tmp_path):
    with client_at(tmp_path/'c',True) as c:
        seed(c);g=RegistryReceipts();r=issue(g,c)
        r['sources']['EV-A']['sha256']='f'*64
        result=compare(g,c,r['receiptId'],ids=['EV-B','EV-A'])
        assert result['registryVersionsMatch'] and not result['writePerformed'] and not result['humanReadVerified'] and not result['bytesVerified']


@pytest.mark.parametrize('revert',[False,True])
def test_one_changed_source_rejects_all_including_a_b_a(tmp_path,revert):
    with client_at(tmp_path/'c',True) as c:
        seed(c);g=RegistryReceipts();r=issue(g,c)
        for old,new in ([('a','b'),('b','a')] if revert else [('a','b')]):
            with c.app.state.db.session() as s:append_custody(s,case_id=CID,evidence_id='EV-B',kind='Change',operator='Synthetic',role='LeadInvestigator',sha256=new*64,previous_sha256=old*64,detail='Synthetic registry change')
        with pytest.raises(HTTPException) as e:compare(g,c,r['receiptId'])
        assert e.value.status_code==412


@pytest.mark.parametrize('token,status',[(None,428),('unknown',409)])
def test_missing_legacy_receipt(tmp_path,token,status):
    with client_at(tmp_path/'c',True) as c:
        seed(c)
        with pytest.raises(HTTPException) as e:compare(RegistryReceipts(),c,token)
        assert e.value.status_code==status


def test_expiration_and_restart(tmp_path):
    with client_at(tmp_path/'c',True) as c:
        seed(c);now=[4194262.256341955];g=RegistryReceipts(clock=lambda:now[0]);r=issue(g,c)
        now[0]+=600
        with pytest.raises(HTTPException) as e:compare(g,c,r['receiptId'])
        assert e.value.status_code==409
        with pytest.raises(HTTPException):compare(RegistryReceipts(),c,r['receiptId'])


def test_unknown_legacy_digest_unchanged(tmp_path):
    with client_at(tmp_path/'c',True) as c:
        with c.app.state.db.session() as s:put_doc(s,EvidenceRow,CID,'EV-A',{'caseId':CID,'evidenceId':'EV-A','confidentiality':'Normal'})
        with pytest.raises(HTTPException) as e:issue(RegistryReceipts(),c,['EV-A'])
        assert e.value.status_code==409
        with c.app.state.db.session() as s:
            from sqlalchemy import select
            assert 'sha256' not in s.scalars(select(EvidenceRow).where(EvidenceRow.key=='EV-A')).first().doc


def test_denied_roles_no_metadata(tmp_path):
    with client_at(tmp_path/'c',True) as c:
        seed(c);g=RegistryReceipts();r=issue(g,c)
        for role in ('Investigator','Public'):
            with pytest.raises(HTTPException) as e:issue(g,c,role=role)
            assert e.value.status_code==403
            with pytest.raises(HTTPException) as e:compare(g,c,r['receiptId'],role=role)
            assert e.value.status_code==403


def test_wrong_set_cross_case(tmp_path):
    with client_at(tmp_path/'c',True) as c:
        seed(c);g=RegistryReceipts();r=issue(g,c)
        with pytest.raises(HTTPException) as e:compare(g,c,r['receiptId'],ids=['EV-A'])
        assert e.value.status_code==409
        with pytest.raises(HTTPException) as e:compare(g,c,r['receiptId'],case='OTHER')
        assert e.value.status_code==403
