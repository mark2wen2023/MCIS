"""Independent transaction/concurrency proof for untrusted history copies."""
import uuid
from threading import Barrier
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import text,select
from .test_host_extraction import extraction_case
from .test_extraction_working_store import working,host,decisions
from mcis_service.agents import working_history_archive as a
from mcis_service.identity import local

@pytest.fixture
def exported(working):
    args,_=working;a.initialize(args[0])
    with host(working) as c:
        pid=c.generate(str(uuid.uuid4()))['proposalId'];c.review(pid,str(uuid.uuid4()),0,decisions())
    raw=a.export_bundle(*args[:4])
    with args[0].session() as s:a.grant(s,local.authorize_read(s,args[2],args[3]).subject_id,args[3],can_import=True,can_read=True)
    return args,raw

def test_concurrent_same_archive_import_is_single_row(exported):
    args,raw=exported;gate=Barrier(2)
    def run():gate.wait();return a.restore_bundle(args[0],args[2],args[3],raw)
    with ThreadPoolExecutor(max_workers=2) as pool:
        fs=[pool.submit(run) for _ in range(2)];results=[f.result(timeout=20) for f in fs]
    assert sorted(r['replayed'] for r in results)==[False,True]
    with args[0].session() as s:assert len(list(s.scalars(select(a.ImportedWorkingArchive))))==1

def test_final_guard_failure_rolls_back_restore(exported,monkeypatch):
    args,raw=exported
    def reject(*x):raise RuntimeError('injected final boundary')
    with monkeypatch.context() as m:
        m.setattr(a,'_final',reject)
        with pytest.raises(RuntimeError):a.restore_bundle(args[0],args[2],args[3],raw)
    assert a.list_imported(args[0],args[2],args[3])['items']==[]

@pytest.mark.parametrize('verb',['UPDATE','DELETE'])
def test_imported_history_cannot_be_rewritten(exported,verb):
    args,raw=exported;saved=a.restore_bundle(args[0],args[2],args[3],raw)
    sql='UPDATE extraction_imported_working_archives SET doc=doc' if verb=='UPDATE' else 'DELETE FROM extraction_imported_working_archives'
    with pytest.raises(Exception):
        with args[0].engine.begin() as c:c.execute(text(sql))
    view=a.read_imported(args[0],args[2],args[3],saved['sha256'])
    assert view['activated'] is False and view['historicalClaimsVerified'] is False

def test_reopened_database_retains_only_history_and_never_token(exported):
    args,raw=exported;saved=a.restore_bundle(args[0],args[2],args[3],raw)
    from mcis_service.db import Database
    db=Database(str(args[0].engine.url))
    try:
        view=a.read_imported(db,args[2],args[3],saved['sha256'])
        assert view['payload']['proposals'][0]['reviews'][0]['factVerified'] is False
        assert args[2].encode() not in raw
        assert a.restore_bundle(db,args[2],args[3],raw)['replayed']
    finally:db.engine.dispose()

def test_export_final_metadata_expiry_denies_package(exported,monkeypatch):
    import inspect
    from fastapi import HTTPException
    from mcis_service.investigation import journal as j
    args,_=exported;original=j.load_case;direct=0
    def load(s,case_id):
        nonlocal direct
        result=original(s,case_id)
        if inspect.currentframe().f_back.f_code.co_name=='export_bundle':
            direct+=1
            if direct==2:
                s.scalar(select(local.SessionRecord)).expires_at=0;s.flush()
        return result
    monkeypatch.setattr(j,'load_case',load)
    with pytest.raises(HTTPException):a.export_bundle(*args[:4])
    assert direct==2
