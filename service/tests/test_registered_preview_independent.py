"""Independent real intake/API/SQLite probes with explicitly controlled core."""
import pytest
from mcis_service.timeline import align_preview
from mcis_service.db import get_doc, put_doc
from mcis_service.evidence.models import EvidenceRow
from mcis_service.redaction.policy import default_policy
from .conftest import C, CASE, H
from .test_registered_align_preview import register, request, URL, RAW
from .test_align_preview_w41 import result

@pytest.fixture
def calls(monkeypatch):
    seen=[]
    def core(*args):
        seen.append(args[2]); return result(args[2])
    monkeypatch.setattr(align_preview,'core_run',core)
    return seen

@pytest.mark.parametrize('role',['AgentService','ExternalExpert','Public'])
def test_non_investigator_cannot_read_registered_bytes(client,calls,role):
    receipt=register(client)
    response=client.post(URL,headers=H(role),json=request(receipt))
    assert response.status_code==403 and not calls


def test_redacted_evidence_access_is_not_full_byte_access(client,calls):
    receipt=register(client)
    p=default_policy();p['matrix']['Investigator']['evidence_meta']='Redacted'
    assert client.put(C+'/access-policy',headers=H('LeadInvestigator'),json=p).status_code==200
    assert client.post(URL,headers=H(),json=request(receipt)).status_code==403
    assert not calls

@pytest.mark.parametrize('length,status',[(262144,200),(262145,413)])
def test_exact_byte_limit(client,calls,length,status):
    header, row = RAW.split(b'\n', 1)
    header += b'\n'
    copies=(length-len(header))//len(row)
    raw=header+row*copies
    raw=raw[:-1]+b' '*(length-len(raw))+b'\n'
    receipt=register(client, raw)
    response=client.post(URL,headers=H(),json=request(receipt))
    assert response.status_code==status,response.text
    assert bool(calls)==(status==200)


def test_tampered_registered_path_cannot_escape_storage(client,calls):
    receipt=register(client)
    with client.app.state.db.session() as s:
        item=get_doc(s,EvidenceRow,CASE,receipt['evidenceId'])
        item['relativePath']='../../outside.csv'
        put_doc(s,EvidenceRow,CASE,receipt['evidenceId'],item)
    response=client.post(URL,headers=H(),json=request(receipt))
    assert response.status_code==422 and not calls


def test_tamper_before_compute_never_calls_core(client,calls):
    receipt=register(client)
    path=client.app.state.settings.blob_dir/CASE/receipt['evidence']['relativePath']
    path.write_bytes(RAW+b'changed')
    response=client.post(URL,headers=H(),json=request(receipt))
    assert response.status_code==409 and not calls


def test_bom_hash_binds_original_bytes_while_core_gets_decoded_text(client,calls):
    receipt=register(client,b'\xef\xbb\xbf'+RAW)
    response=client.post(URL,headers=H(),json=request(receipt))
    assert response.status_code==200,response.text
    assert calls[0]['sources'][0]['text']==RAW.decode()
    assert response.json()['sourceSnapshots'][0]['byteLength']==len(RAW)+3


def test_formula_is_inert_text_not_host_evaluation(client,calls):
    raw=RAW.replace(b',45',b',=1+1')
    receipt=register(client,raw)
    response=client.post(URL,headers=H(),json=request(receipt))
    assert response.status_code==422,response.text
    assert response.json()['code']=='TIMELINE_SOURCE_CSV'
    assert not calls


def test_foreign_case_evidence_id_is_not_resolved(client,calls):
    from mcis_service.cases.models import CaseRow
    receipt=register(client)
    other='CASE-INDEPENDENT-OTHER'
    with client.app.state.db.session() as s:
        case=dict(get_doc(s,CaseRow,CASE,CASE));case['caseId']=other
        put_doc(s,CaseRow,other,other,case)
    response=client.post('/api/v1/cases/'+other+'/timeline/registered-align-preview',headers=H(),json=request(receipt))
    assert response.status_code==404,response.text
    assert not calls


def test_historical_receipt_cannot_be_reactivated(client,calls):
    from mcis_service.working_records_archive.models import ArchiveImportHistoryRow
    receipt=register(client)
    with client.app.state.db.session() as s:
        s.add(ArchiveImportHistoryRow(case_id=CASE,kind='evidence-intake',key=receipt['requestDigest'],evidence_id=receipt['evidenceId'],doc={}))
    response=client.post(URL,headers=H('LeadInvestigator'),json=request(receipt))
    assert response.status_code==409,response.text
    assert response.json()['code']=='ARCHIVE_HISTORY_ONLY'
    assert not calls
