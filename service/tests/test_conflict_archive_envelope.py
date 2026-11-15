"""Synthetic envelope boundary checks; no conflict export/restore capability enabled."""
import base64
import hashlib
import io
import json
import zipfile
from copy import deepcopy
import pytest
from mcis_service.package.mcase import manifest_json
from mcis_service.working_records_archive import conflict_envelope as envelope
from mcis_service.working_records_archive.conflicts import ConflictArchiveInvalid
from mcis_service.working_records_archive.validation import canonical
from .test_package_intake_parser import base,pack
from .test_conflict_archive_parser import bundle
from .conflict_version_helpers import checked
from .test_conflict_archive_readiness import body
from .test_working_record_archive import client_at,ROOT,CID,HEAD
from .test_consultation_archive_readiness import state


def wrap(files,change_manifest=None):
    manifest=json.loads(manifest_json(CID,files,'2026-01-01T00:00:00Z',envelope.VERSION))
    if change_manifest:change_manifest(manifest)
    return pack(files,json.dumps(manifest))


def inspect(raw):return envelope.inspect_envelope(raw,expected_sha256=hashlib.sha256(raw).hexdigest())


@pytest.fixture
def sample(tmp_path):
    with client_at(tmp_path/'source',True) as c:
        blob=b'Synthetic evidence only\n'
        evidence=checked(c,'post',ROOT+'/evidence',{'title':'Synthetic','source':'Synthetic',
            'extractedBy':'Synthetic','extractedUtc':'2026-01-01T00:00:00Z','relativePath':'raw/source.txt',
            'category':'Document','contentBase64':base64.b64encode(blob).decode()},201).json()
        value=body();value['a']['evidenceId']=evidence['evidenceId']
        checked(c,'post',ROOT+'/conflicts',value,201)
        checked(c,'patch',ROOT+'/conflicts/C-01',{'resolution':'Synthetic second version'})
        member,ctx=bundle(c)
        files=base()
        files.update({envelope.PATH:canonical(member),envelope.MIRROR:canonical({'conflicts':[r['doc'] for r in member['records']]}),
            'evidence/index.json':canonical(ctx['evidence']),'raw/source.txt':blob,
            'audit/audit.jsonl':('\n'.join(ctx['audit_lines'])+'\n').encode(),
            'audit/custody.jsonl':('\n'.join(ctx['custody_lines'])+'\n').encode()})
        yield c,files


def test_boundary_success_is_not_restore_permission(sample,tmp_path):
    source,files=sample;raw=wrap(files);before=state(source)
    result=inspect(raw)
    assert result.case_id==CID and result.record_count==1 and result.revision_count==2
    assert result.unknown_history_count==0 and result.restore_ready is False
    assert state(source)==before
    checked(source,'get',ROOT+'/export',status=409);assert state(source)==before
    with client_at(tmp_path/'target') as target:
        before=state(target);payload={'contentBase64':base64.b64encode(raw).decode()}
        checked(target,'post','/api/v1/packages/intakes:preview',payload,status=422)
        checked(target,'post','/api/v1/packages/intakes:commit',{**payload,'confirmed':True,'sourceSha256':hashlib.sha256(raw).hexdigest()},status=422)
        assert state(target)==before and not(target.app.state.settings.blob_dir/CID).exists()


@pytest.mark.parametrize('mutation',[
    lambda m:m.update(packageVersion='1.4.0'),lambda m:m.update(packageFormat='other'),
    lambda m:m.update(caseId='OTHER'),lambda m:m.update(extra=True),
    lambda m:m['files'].pop(),lambda m:m['files'].append(deepcopy(m['files'][0])),
    lambda m:m['files'][0].update(sizeBytes=True),lambda m:m['files'][0].update(sha256='0'*64),
    lambda m:m['files'][0].update(role='Other'),lambda m:m['files'][0].update(relativePath='../source'),
])
def test_manifest_mismatch(sample,mutation):
    source,files=sample;before=state(source)
    with pytest.raises(ConflictArchiveInvalid):inspect(wrap(files,mutation))
    assert state(source)==before


@pytest.mark.parametrize('path,content',[
    (envelope.MIRROR,b'{"conflicts":[]}'),(envelope.PATH,b'{}'),
    ('raw/source.txt',b'wrong bytes'),('evidence/index.json',b'[]'),
    ('audit/audit.jsonl',b''),('audit/custody.jsonl',b''),
    ('access-policy.json',b'{}'),('working-records/backup.v1.json',b'{}'),
    ('recommendations.json',b'[{"id":"synthetic"}]'),('consultation/rounds.json',b'[{}]'),
    ('analysis/timeline.json',b'{"events":[{}]}'),('agents/drafts.json',b'[{}]'),
    ('unrecognized.json',b'{}'),
])
def test_correct_checksum_does_not_hide_dependency_or_scope_failure(sample,path,content):
    source,files=sample;files[path]=content;before=state(source)
    with pytest.raises(ConflictArchiveInvalid):inspect(wrap(files))
    assert state(source)==before


def test_missing_member_and_whole_envelope_digest(sample):
    _,files=sample
    with pytest.raises(ConflictArchiveInvalid):envelope.inspect_envelope(wrap(files),expected_sha256='0'*64)
    del files[envelope.PATH]
    with pytest.raises(ConflictArchiveInvalid):inspect(wrap(files))


def test_legacy_unknown_is_retained(tmp_path):
    from mcis_service.db import put_doc
    from mcis_service.timeline.models import ConflictRow
    with client_at(tmp_path/'legacy',True) as c:
        with c.app.state.db.session() as s:put_doc(s,ConflictRow,CID,'C-01',{**body(),'caseId':CID})
        member,_=bundle(c);files=base()
        files[envelope.PATH]=canonical(member);files[envelope.MIRROR]=canonical({'conflicts':[member['records'][0]['doc']]})
        result=inspect(wrap(files));assert result.unknown_history_count==1 and result.revision_count==0 and not result.restore_ready


def test_existing_transaction_rolls_back_on_injected_boundary_failure(sample,tmp_path,monkeypatch):
    # Test-only injection after normal supported case import, before publication.
    # This is NOT a conflict restoration or a way to accept the experimental envelope.
    from mcis_service.package_intake import router
    _,files=sample;files[envelope.MIRROR]=b'{"conflicts":[]}'
    invalid=wrap(files);normal=pack(base());original=router.import_case;visited=[]
    def fail_after_import(*args,**kwargs):
        original(*args,**kwargs)
        from mcis_service.cases.models import CaseRow
        from sqlalchemy import select
        assert args[0].scalars(select(CaseRow).where(CaseRow.case_id==CID)).one()
        visited.append(True)
        inspect(invalid)
    with client_at(tmp_path/'target') as c:
        before=state(c)
        monkeypatch.setattr(router,'import_case',fail_after_import)
        payload={'contentBase64':base64.b64encode(normal).decode(),'confirmed':True,'sourceSha256':hashlib.sha256(normal).hexdigest()}
        checked(c,'post','/api/v1/packages/intakes:commit',payload,status=500)
        assert visited==[True]
        assert state(c)==before and not(c.app.state.settings.blob_dir/CID).exists()
        assert not list(c.app.state.settings.blob_dir.glob('.package-intake-*'))
        monkeypatch.setattr(router,'import_case',original)
        checked(c,'post','/api/v1/packages/intakes:commit',payload)


def test_zip_duplicate_member_refused(sample):
    _,files=sample;raw=wrap(files)
    stream=io.BytesIO(raw)
    with zipfile.ZipFile(stream,'a') as z:
        # Case alias tests reader's actual member inventory, not just manifest entries.
        z.writestr('CASE.JSON',files['case.json'])
    with pytest.raises(ConflictArchiveInvalid):inspect(stream.getvalue())


def test_registered_version_replacement_still_refused(sample):
    from mcis_service.evidence.service import append_custody
    source,files=sample;member,ctx=bundle(source);doc=ctx['evidence'][0]
    with source.app.state.db.session() as s:
        append_custody(s,case_id=CID,evidence_id=doc['evidenceId'],kind='Change',operator='Synthetic',role='LeadInvestigator',sha256='b'*64,previous_sha256=doc['sha256'],detail='Synthetic declaration, no file replacement')
    _,ctx=bundle(source)
    files['audit/custody.jsonl']=('\n'.join(ctx['custody_lines'])+'\n').encode()
    with pytest.raises(ConflictArchiveInvalid,match='replaced-original history unsupported'):inspect(wrap(files))
