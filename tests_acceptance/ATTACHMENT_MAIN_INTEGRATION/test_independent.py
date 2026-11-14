"""Independent main-only patch provenance and combined attachment safety checks."""
import hashlib
import io
from pathlib import Path
import subprocess
from urllib.parse import unquote
import zipfile

import pytest
from tests.test_report_output import origin, H, CID
from tests.test_report_bundle_attachment_access import register, download, access_count, INVESTIGATOR
from tests.test_working_record_archive import client_at, checked, exported, imported, ROOT as URL, HEAD
from tests.test_restored_attachment_filename import attach, accesses
from mcis_service.evidence import service as evidence
from mcis_service.db import put_doc
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy, CATEGORIES

REPO=Path(__file__).resolve().parents[2]
BASE='3aba2bf03e393909c611489ae573a887087637ac'
SOURCE61='aad96d439d34d112cd07637fc341c06dbaf22978'
SOURCE64='5d10b67db47e55b6352b559ec1d00ae61ede99c7'


def show(ref,path):
    return subprocess.run(['git','show',f'{ref}:{path}'],cwd=REPO,capture_output=True,check=True).stdout


@pytest.mark.parametrize('ref,path',[
    (SOURCE64,'service/mcis_service/report_output/attachment_access.py'),
    (SOURCE64,'service/mcis_service/evidence/router.py'),
    (SOURCE61,'service/mcis_service/working_records_archive/filename.py'),
    (SOURCE61,'service/mcis_service/working_records_archive/router.py'),
    (SOURCE61,'web/src/evidenceIntake/history.ts'),
    (SOURCE61,'web/src/evidenceIntake/EvidenceIntakePanel.tsx'),
])
def test_other_production_files_match_exact_source(ref,path):
    assert (REPO/path).read_bytes()==show(ref,path)


def test_intake_only_four_download_lines_added_to_main():
    path='service/mcis_service/evidence_intake/router.py'
    base=show(BASE,path).decode()
    before="            authorize(ctx,s,case_id);found=load_receipt(ctx,s,case_id,digest)"
    after="            from ..reports.access import begin\n            begin(s)\n"+before
    assert base.count(before)==1
    expected=base.replace(before,after)
    before="            receipt,raw=found\n            evidence.append_custody"
    after="            receipt,raw=found\n            from ..report_output.attachment_access import protect_container\n            protect_container(s,case_id,ctx.role,raw)\n            evidence.append_custody"
    assert expected.count(before)==1
    expected=expected.replace(before,after)
    assert (REPO/path).read_text()==expected
    assert (REPO/path).read_bytes()!=show(SOURCE64,path)
    assert 'allocate_for_intake' not in expected and 'SafeReadUnavailable' not in expected


def test_branch_has_not_imported_pr56_ancestry():
    ancestor=subprocess.run(['git','merge-base','--is-ancestor','254167e3e957784fd9d2d136a275731f33314d9b','HEAD'],cwd=REPO)
    assert ancestor.returncode==1
    base=subprocess.run(['git','merge-base','HEAD',BASE],cwd=REPO,capture_output=True,text=True,check=True)
    assert base.stdout.strip()==BASE


def test_candidate_freeze_matches():
    for line in (REPO/'logs/attachment-main-integration-impl-hashes-frozen.txt').read_text().splitlines():
        digest,path=line.split(maxsplit=1)
        assert hashlib.sha256((REPO/path).read_bytes()).hexdigest()==digest


def policy(client,case,readable):
    p=default_policy();p['matrix']['Investigator']={c:'ReadOnly' for c in CATEGORIES};p['fieldRules']=[]
    if not readable:p['matrix']['Investigator']['audit']='Deny'
    with client.app.state.db.session() as session:put_doc(session,AccessPolicyRow,case,'policy',p)


@pytest.mark.parametrize('route',['intake','legacy'])
def test_full_readonly_then_revocation_on_both_live_routes(origin,route):
    client,_,_=origin
    raw=b'PK opaque damaged ZIP fixture';receipt=register(client,raw,'名称%20.docx')
    policy(client,CID,True)
    before=access_count(client)
    allowed=download(client,receipt,route,INVESTIGATOR)
    assert allowed.status_code==200 and allowed.content==raw and access_count(client)==before+1
    policy(client,CID,False);before=access_count(client)
    denied=download(client,receipt,route,INVESTIGATOR)
    assert denied.status_code==403 and denied.headers['cache-control']=='no-store'
    assert 'content-disposition' not in denied.headers and raw not in denied.content
    assert access_count(client)==before


@pytest.mark.parametrize('route',['intake','legacy'])
def test_success_audit_failure_rolls_back_and_no_bytes(origin,route,monkeypatch):
    client,_,_=origin;raw=b'PK PRIVATE-CONTENT';receipt=register(client,raw)
    before=access_count(client);real=evidence.append_custody
    def fail_after_append(*args,**kwargs):
        real(*args,**kwargs);raise RuntimeError('PRIVATE-AUDIT-FAILURE')
    monkeypatch.setattr(evidence,'append_custody',fail_after_append)
    result=download(client,receipt,route,H)
    assert result.status_code==500 and b'PRIVATE' not in result.content
    assert 'content-disposition' not in result.headers and result.headers['cache-control']=='no-store'
    assert access_count(client)==before


def test_restored_unicode_name_gate_and_audit_rollback(tmp_path,monkeypatch):
    name='报告 “原件” %2F 😀.zip'
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z:z.writestr('synthetic.txt','synthetic report copy')
    raw=buf.getvalue()
    with client_at(tmp_path/'source',True) as client:
        receipt=attach(client,raw,name);package=exported(client)
    with client_at(tmp_path/'restored') as client:
        imported(client,package);case=receipt['caseId'];policy(client,case,True)
        url=URL+'/archive-history/evidence/'+receipt['evidenceId']+'/content'
        before=accesses(client)
        good=checked(client,'get',url,headers=INVESTIGATOR)
        assert good.content==raw and good.headers['x-sha256']==hashlib.sha256(raw).hexdigest()
        assert unquote(good.headers['content-disposition'].split("UTF-8''")[1])==name
        assert accesses(client)==before+1
        real=evidence.append_custody
        def fail_after_append(*args,**kwargs):
            real(*args,**kwargs);raise RuntimeError('PRIVATE-HISTORY-FAILURE')
        monkeypatch.setattr(evidence,'append_custody',fail_after_append)
        before=accesses(client);bad=checked(client,'get',url,headers=INVESTIGATOR,status=500)
        assert accesses(client)==before and 'content-disposition' not in bad.headers and 'PRIVATE' not in bad.text
        monkeypatch.setattr(evidence,'append_custody',real)
        policy(client,case,False)
        bad=checked(client,'get',url,headers=INVESTIGATOR,status=403)
        assert accesses(client)==before and 'content-disposition' not in bad.headers and name not in bad.text
