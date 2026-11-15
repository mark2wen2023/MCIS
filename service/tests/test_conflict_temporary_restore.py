"""Actual disposable SQLite roundtrips of synthetic experimental envelopes only."""
import hashlib
from sqlalchemy import select,text
import pytest
from mcis_service.working_records_archive.conflict_sandbox import TemporaryConflictStore
from mcis_service.working_records_archive.conflicts import ConflictArchiveInvalid
from mcis_service.working_records_archive.conflict_envelope import inspect_envelope,PATH
from mcis_service.package_intake.parser import read_bounded,strict_json
from mcis_service.timeline.models import ConflictRow
from mcis_service.timeline.revisions import ConflictRevision
from mcis_service.audit.models import AuditEventRow
from mcis_service.evidence.models import EvidenceRow,CustodyEventRow
from mcis_service.db import put_doc
from .test_conflict_archive_envelope import sample,wrap
from .test_conflict_archive_parser import bundle
from .test_package_intake_parser import base,pack
from .test_working_record_archive import CID,ROOT,client_at,checked
from .test_conflict_archive_readiness import body
from mcis_service.working_records_archive.validation import canonical
from mcis_service.working_records_archive.conflict_envelope import MIRROR


def restore(store,raw,**kwargs):return store.restore(raw,expected_sha256=hashlib.sha256(raw).hexdigest(),**kwargs)


def all_rows(store):
    with store.db.session() as s:
        names=s.execute(text("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")).scalars().all()
        return {n:s.execute(text('SELECT * FROM "'+n+'"')).all() for n in names}


def business(store):
    with store.db.session() as s:
        conflicts=[(r.key,r.created_utc,r.updated_utc,r.doc) for r in s.scalars(select(ConflictRow).order_by(ConflictRow.id))]
        revisions=[(r.case_id,r.conflict_id,r.revision,r.doc) for r in s.scalars(select(ConflictRevision).order_by(ConflictRevision.revision))]
        audit=[(r.seq,r.line,r.entity_type,r.entity_id) for r in s.scalars(select(AuditEventRow).order_by(AuditEventRow.seq))]
        evidence=[r.doc for r in s.scalars(select(EvidenceRow).order_by(EvidenceRow.id))]
        custody=[(r.seq,r.line,r.evidence_id,r.kind) for r in s.scalars(select(CustodyEventRow).order_by(CustodyEventRow.seq))]
        return conflicts,revisions,audit,evidence,custody


def test_two_restore_roundtrip_exact_business_and_bytes(sample):
    source,files=sample
    from .conflict_version_helpers import checked as versioned
    versioned(source,'patch',ROOT+'/conflicts/C-01',{'status':'Annotated','resolution':'Synthetic third revision 中文'})
    member,ctx=bundle(source)
    files[PATH]=canonical(member);files[MIRROR]=canonical({'conflicts':[r['doc'] for r in member['records']]})
    files['audit/audit.jsonl']=(''.join(line+'\n' for line in ctx['audit_lines'])).encode()
    raw=wrap(files)
    with TemporaryConflictStore() as first:
        result=restore(first,raw);assert result.restore_ready is False
        expected=business(first)
        original=strict_json(files[PATH])['records'][0]
        assert expected[0][0]==(original['key'],original['createdUtc'],original['updatedUtc'],original['doc'])
        assert len(expected[1])==3 and [r[3] for r in expected[1]]==original['revisions']
        second_raw=first.export_candidate()
        second_files=read_bounded(second_raw)
        assert strict_json(second_files[PATH])==strict_json(files[PATH])
        assert second_files['raw/source.txt']==files['raw/source.txt']
        assert second_files['audit/audit.jsonl']==files['audit/audit.jsonl']
        assert second_files['audit/custody.jsonl']==files['audit/custody.jsonl']
        with TemporaryConflictStore() as second:
            restore(second,second_raw)
            assert business(second)==expected
            third_raw=second.export_candidate()
            assert strict_json(read_bounded(third_raw)[PATH])==strict_json(files[PATH])
            assert inspect_envelope(third_raw,expected_sha256=hashlib.sha256(third_raw).hexdigest()).restore_ready is False
    checked(source,'get',ROOT+'/export',status=409)


@pytest.mark.parametrize('stage',['current','journal','audit','objects','before_commit'])
def test_failure_rolls_back_every_table_and_blob_then_retry(sample,stage):
    _,files=sample;raw=wrap(files)
    with TemporaryConflictStore() as store:
        before=all_rows(store)
        with pytest.raises(RuntimeError,match='SYNTHETIC_RESTORE_FAILURE'):
            restore(store,raw,fault_after=stage)
        assert all_rows(store)==before
        restore(store,raw)
        assert len(business(store)[1])==2


def test_no_existing_target_overwrite(sample):
    _,files=sample;raw=wrap(files)
    with TemporaryConflictStore() as store:
        restore(store,raw);before=all_rows(store)
        with pytest.raises(ConflictArchiveInvalid,match='target not empty'):restore(store,raw)
        assert all_rows(store)==before


@pytest.mark.parametrize('edited',[False,True])
def test_unknown_legacy_roundtrip(tmp_path,edited):
    with client_at(tmp_path/'source',True) as c:
        with c.app.state.db.session() as s:put_doc(s,ConflictRow,CID,'C-01',{**body(),'caseId':CID})
        if edited:
            from .conflict_version_helpers import checked as versioned
            versioned(c,'patch',ROOT+'/conflicts/C-01',{'resolution':'Synthetic known later note'})
        member,ctx=bundle(c);files=base()
        files[PATH]=canonical(member);files[MIRROR]=canonical({'conflicts':[member['records'][0]['doc']]})
        files['audit/audit.jsonl']=(''.join(line+'\n' for line in ctx['audit_lines'])).encode()
        raw=wrap(files)
        with TemporaryConflictStore() as a,TemporaryConflictStore() as b:
            assert restore(a,raw).unknown_history_count==1
            assert restore(b,a.export_candidate()).unknown_history_count==1
            assert business(a)==business(b)
            output=strict_json(read_bounded(b.export_candidate())[PATH])
            assert output==member


def test_old_format_stays_on_existing_parser_and_new_store_refuses(tmp_path):
    from mcis_service.package_intake.parser import parse_package
    old=pack(base());assert parse_package(old).manifest['packageVersion']=='1.0.0'
    with TemporaryConflictStore() as store:
        before=all_rows(store)
        with pytest.raises(ConflictArchiveInvalid):restore(store,old)
        assert all_rows(store)==before


def test_unsupported_new_state_still_refuses_reexport(sample):
    from mcis_service.recommendations.models import RecommendationRow
    _,files=sample
    with TemporaryConflictStore() as store:
        restore(store,wrap(files))
        with store.db.session() as s:put_doc(s,RecommendationRow,CID,'SYN',{'synthetic':'unsupported'})
        before=all_rows(store)
        with pytest.raises(ConflictArchiveInvalid,match='unsupported stored state'):store.export_candidate()
        assert all_rows(store)==before


def test_two_concurrent_restores_only_one_owns_empty_store(sample):
    from concurrent.futures import ThreadPoolExecutor
    _,files=sample;raw=wrap(files)
    with TemporaryConflictStore() as store:
        def attempt(_):
            try:restore(store,raw);return 'restored'
            except ConflictArchiveInvalid as exc:
                assert str(exc)=='target not empty';return 'refused'
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,range(2)))
        assert sorted(results)==['refused','restored']
        assert len(business(store)[1])==2
        assert read_bounded(store.export_candidate())['raw/source.txt']==files['raw/source.txt']


def test_restored_history_uses_existing_policy_without_new_approval(sample):
    from types import SimpleNamespace
    from fastapi import HTTPException
    from mcis_service.timeline.revisions import history
    _,files=sample
    with TemporaryConflictStore() as store:
        restore(store,wrap(files));before=all_rows(store)
        with store.db.session() as s:
            current=s.scalars(select(ConflictRow)).one().doc
            result=history(s,SimpleNamespace(role='LeadInvestigator'),CID,'C-01',current)
            assert result['revisions']==strict_json(files[PATH])['records'][0]['revisions']
            assert result['identityMode']=='unverified-self-reported'
            with pytest.raises(HTTPException) as denied:
                history(s,SimpleNamespace(role='Investigator'),CID,'C-01',current)
            assert denied.value.status_code==403
        assert all_rows(store)==before


def test_invalid_preparation_does_not_create_rows_or_objects(sample):
    _,files=sample;raw=wrap(files)[:-30]
    with TemporaryConflictStore() as store:
        before=all_rows(store)
        with pytest.raises(ConflictArchiveInvalid):restore(store,raw)
        assert all_rows(store)==before
