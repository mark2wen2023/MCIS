"""Real temporary SQLite + existing domain PATCH; synthetic only, no product restore."""
import hashlib
from types import SimpleNamespace
from sqlalchemy import select,text,inspect
import pytest
from research.conflict_source_intent.temporary_continuation import TemporaryContinuingConflictStore
from research.conflict_source_intent.archive_receipts_v2 import ConflictArchiveInvalid
from research.conflict_source_intent import archive_envelope_v2 as envelope
from mcis_service.package_intake.parser import read_bounded,strict_json,parse_package
from mcis_service.timeline.router import editable_conflicts,patch_conflict,conflict_revisions,ConflictPatch
from mcis_service.timeline.source_receipts import ConflictSourceReceipt
from mcis_service.timeline import revisions
from mcis_service.working_records_archive.validation import canonical
from .test_conflict_archive_envelope_v2 import archives,DATE
from .test_package_intake_parser import base,pack
from .test_conflict_archive_readiness import body
from .test_working_record_archive import CID


def context(store):return SimpleNamespace(db=store.db,role='LeadInvestigator',operator='Synthetic continuation')
def restore(store,raw,**kwargs):return store.restore(raw,expected_sha256=hashlib.sha256(raw).hexdigest(),**kwargs)
def snapshot(store):
    with store.db.session() as s:
        return {name:s.execute(text('SELECT * FROM "'+name+'"')).all() for name in inspect(s.connection()).get_table_names() if not name.startswith('sqlite_')}
def history(store):return conflict_revisions(CID,'C-01',context(store))['revisions']
def update(store,note):
    ctx=context(store);token=editable_conflicts(CID,ctx)[0]['version']
    return patch_conflict(CID,'C-01',ConflictPatch(expectedVersion=token,resolution=note),ctx)
def build(files,version=envelope.VERSION):return envelope.build_envelope(files,case_id=CID,created_utc=DATE,version=version)


def test_v2_restore_append_export_restore_preserves_prefix_and_inactive_receipts(archives):
    files=archives[1];raw=build(files);original=strict_json(files[envelope.PATH])
    with TemporaryContinuingConflictStore() as first:
        assert not restore(first,raw).restore_ready
        with first.db.session() as s:
            assert s.scalars(select(ConflictSourceReceipt)).first() is None
            stored=s.execute(text('SELECT doc FROM offline_conflict_inactive_receipts')).all()
            assert len(stored)==2
        prior=history(first);assert prior==original['records'][0]['revisions']
        update(first,'Synthetic post-restore note')
        continued=history(first)
        assert continued[:-1]==prior and continued[-1]['before']==prior[-1]['after']
        assert continued[-1]['after']['resolution']=='Synthetic post-restore note'
        assert continued[-1]['afterSources']==prior[-1]['afterSources']
        assert continued[-1]['operator']=='Synthetic continuation'
        raw2=first.export_candidate();files2=read_bounded(raw2)
        assert files2['raw/source.txt']==files['raw/source.txt']
        assert files2['evidence/index.json']==files['evidence/index.json']
        assert files2['audit/custody.jsonl']==files['audit/custody.jsonl']
        assert files2['audit/audit.jsonl'].startswith(files['audit/audit.jsonl'])
        member2=strict_json(files2[envelope.PATH]);assert member2['receipts']==original['receipts']
        with TemporaryContinuingConflictStore() as second:
            assert not restore(second,raw2).restore_ready
            assert history(second)==continued
            update(second,'Synthetic second-store note')
            raw3=second.export_candidate()
            with TemporaryContinuingConflictStore() as third:
                restore(third,raw3)
                assert history(third)[:-1]==continued
                assert history(third)[-1]['after']['resolution']=='Synthetic second-store note'
                with third.db.session() as s:assert s.scalars(select(ConflictSourceReceipt)).first() is None

@pytest.mark.parametrize('phase',['current','journal','inactive_receipts','audit','objects','before_commit'])
def test_restore_failure_rolls_back_all_sqlite_tables(archives,phase):
    raw=build(archives[1])
    with TemporaryContinuingConflictStore() as store:
        before=snapshot(store)
        with pytest.raises(RuntimeError,match='SYNTHETIC_RESTORE_FAILURE:'+phase):restore(store,raw,fault_after=phase)
        assert snapshot(store)==before
        # Explicit retry only after proven ordinary rollback; not unknown commit.
        restore(store,raw);assert len(history(store))==2

def test_append_capture_failure_rolls_back(archives,monkeypatch):
    with TemporaryContinuingConflictStore() as store:
        restore(store,build(archives[1]));before=snapshot(store);visited=[];original=revisions.capture
        def fail(*args,**kwargs):
            original(*args,**kwargs)
            visited.append(True)
            raise RuntimeError('SYNTHETIC_AFTER_CAPTURE')
        monkeypatch.setattr(revisions,'capture',fail)
        with pytest.raises(RuntimeError,match='SYNTHETIC_AFTER_CAPTURE'):update(store,'Should rollback')
        assert visited==[True] and snapshot(store)==before

@pytest.mark.parametrize('version',[envelope.LEGACY_VERSION,envelope.VERSION])
def test_legacy_unknown_continuation_preserves_unknown(version):
    n,path=envelope.PROFILES[version];doc={**body(),'caseId':CID}
    member={'format':'MCIS-CONFLICT-ARCHIVE','version':n,'caseId':CID,'records':[{'key':'C-01','createdUtc':DATE,'updatedUtc':DATE,'doc':doc,'coverage':'unknown-before-capture','revisions':[]}]}
    if n==2:member['receipts']=[]
    files=base();files[path]=canonical(member);files[envelope.MIRROR]=canonical({'conflicts':[doc]})
    with TemporaryContinuingConflictStore() as first,TemporaryContinuingConflictStore() as second:
        restore(first,build(files,version));assert history(first)==[]
        update(first,'Synthetic first captured note')
        revision=history(first)[0];assert revision['coverage']=='unknown-before-capture' and revision['beforeSources'] is None
        restore(second,first.export_candidate());assert history(second)==[revision]

def test_existing_target_and_old_product_version_boundaries(archives):
    old=pack(base());assert parse_package(old).manifest['packageVersion']=='1.0.0'
    with TemporaryContinuingConflictStore() as store:
        before=snapshot(store)
        with pytest.raises(ConflictArchiveInvalid):restore(store,old)
        assert snapshot(store)==before
        raw=build(archives[1]);restore(store,raw);before=snapshot(store)
        with pytest.raises(ConflictArchiveInvalid,match='target not empty'):restore(store,raw)
        assert snapshot(store)==before
