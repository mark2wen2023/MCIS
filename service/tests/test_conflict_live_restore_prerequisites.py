"""Ordinary domain-function characterization on temporary synthetic restored stores.
No product restore wiring, HTTP/SSO claim, original-file read or security/ECFC probe.
"""
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from pathlib import Path
import hashlib
import pytest
from fastapi import HTTPException
from sqlalchemy import select,text
from mcis_service.working_records_archive.conflict_sandbox import TemporaryConflictStore
from mcis_service.working_records_archive.conflicts import ConflictArchiveInvalid
from mcis_service.timeline.router import editable_conflicts,patch_conflict,conflict_revisions,ConflictPatch
from mcis_service.package_intake.router import IntakeReceipt
from mcis_service.timeline.origin import TimelineImportOrigin
from .test_conflict_archive_envelope import sample,wrap
from .test_conflict_temporary_restore import all_rows
from .test_working_record_archive import CID


def context(db):return SimpleNamespace(db=db,role='LeadInvestigator',operator='Synthetic continuing investigator')
def restore(store,raw):store.restore(raw,expected_sha256=hashlib.sha256(raw).hexdigest())


def test_domain_continuation_appends_but_frozen_backup_refuses(sample):
    source,files=sample;raw=wrap(files)
    old_token=editable_conflicts(CID,context(source.app.state.db))[0]['version']
    with TemporaryConflictStore() as store:
        restore(store,raw);ctx=context(store.db)
        original=conflict_revisions(CID,'C-01',ctx)['revisions']
        token=editable_conflicts(CID,ctx)[0]['version']
        # Content-derived token survives cloning; it is NOT a restore-generation identity.
        assert token==old_token
        changed=patch_conflict(CID,'C-01',ConflictPatch(expectedVersion=token,resolution='Synthetic new investigation note'),ctx)
        history=conflict_revisions(CID,'C-01',ctx)['revisions']
        assert history[:-1]==original and history[-1]['before']==original[-1]['after']
        assert history[-1]['after']==changed and history[-1]['previousSha256']==original[-1]['sha256']
        assert history[-1]['operator']=='Synthetic continuing investigator'
        before=all_rows(store)
        with pytest.raises(ConflictArchiveInvalid,match='restored journal/current differs from source'):store.export_candidate()
        assert all_rows(store)==before


def test_sqlite_source_retention_is_not_product_layout_or_receipt(sample):
    _,files=sample;raw=wrap(files)
    with TemporaryConflictStore() as store:
        restore(store,raw)
        root=Path(store.db.engine.url.database).parent
        assert not(root/CID).exists()  # No attempt to read any original or protected API.
        with store.db.session() as s:
            assert s.scalars(select(IntakeReceipt)).first() is None
            assert s.scalars(select(TimelineImportOrigin)).first() is None
            receipt=s.execute(text('SELECT source_sha256,source_bytes FROM offline_conflict_receipt')).one()
            assert receipt.source_bytes==raw and receipt.source_sha256==hashlib.sha256(raw).hexdigest()
            blob=s.execute(text("SELECT data FROM offline_conflict_members WHERE path='raw/source.txt'")).scalar_one()
            assert blob==files['raw/source.txt']


def test_restored_domain_concurrency_retains_one_successful_revision(sample):
    _,files=sample
    with TemporaryConflictStore() as store:
        restore(store,wrap(files));ctx=context(store.db)
        token=editable_conflicts(CID,ctx)[0]['version']
        original=conflict_revisions(CID,'C-01',ctx)['revisions']
        def save(n):
            try:
                patch_conflict(CID,'C-01',ConflictPatch(expectedVersion=token,resolution=f'Synthetic concurrent {n}'),ctx)
                return 200
            except HTTPException as exc:return exc.status_code
        with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(save,range(2)))
        assert sorted(statuses)==[200,412]
        history=conflict_revisions(CID,'C-01',ctx)['revisions']
        assert history[:-1]==original and len(history)==len(original)+1
        with pytest.raises(ConflictArchiveInvalid):store.export_candidate()
