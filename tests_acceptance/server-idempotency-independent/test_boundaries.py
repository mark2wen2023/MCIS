import uuid,threading,sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta
import pytest
from sqlalchemy import text,event
from fastapi import HTTPException
from mcis_service.db import Database,put_doc
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from tests.test_server_idempotency_research import setup,local,p,V,A,META,CASE,run,receipts,counts


def test_external_prior_revoke_is_seen_before_any_registration(setup):
    app,store=setup;external=sqlite3.connect(app.state.settings.data_dir/'test.db');external.execute('BEGIN IMMEDIATE');entered=threading.Event()
    def observe(conn,cursor,statement,*args):
        if statement=='BEGIN IMMEDIATE':entered.set()
    event.listen(app.state.db.engine,'before_cursor_execute',observe)
    try:
        with ThreadPoolExecutor(1) as pool:
            future=pool.submit(run,store)
            assert entered.wait(3)
            external.execute('DELETE FROM research_grants');external.commit()
            with pytest.raises(HTTPException) as error:future.result(timeout=5)
            assert error.value.status_code==403
    finally:external.close();event.remove(app.state.db.engine,'before_cursor_execute',observe)
    assert counts(app)==(0,0,0) and receipts(app)==0


def test_same_key_conflicting_metadata_across_connections_has_one_winner(setup):
    app,_=setup;key=str(uuid.uuid4());barrier=threading.Barrier(3)
    def worker(index):
        db=Database(app.state.settings.resolved_db_url)
        try:
            store=p.Registration(db,store_epoch='synthetic-store-1',verifier=V(),authorizer=A());barrier.wait(timeout=3)
            try:return store.run(CASE,'synthetic-case-generation-1',key,{**META,'title':f'Synthetic {index}'},'synthetic-test-only')
            except HTTPException as error:return error.status_code
        finally:db.engine.dispose()
    with ThreadPoolExecutor(3) as pool:results=list(pool.map(worker,range(3)))
    assert sum(isinstance(result,dict) for result in results)==1 and results.count(409)==2
    assert counts(app)==(1,1,1) and receipts(app)==1


def test_policy_revocation_blocks_existing_receipt_queries(setup):
    app,store=setup;key=str(uuid.uuid4());run(store,key)
    policy=default_policy();policy['matrix']['Investigator']['evidence_meta']='Deny'
    with app.state.db.session() as session:put_doc(session,AccessPolicyRow,CASE,'policy',policy)
    for recover in (False,True):
        with pytest.raises(HTTPException) as error:run(store,key,recover=recover)
        assert error.value.status_code==403
    assert counts(app)==(1,1,1) and receipts(app)==1


def test_verifier_actor_issuer_must_be_string(setup):
    app,_=setup
    class WrongVerifier:
        def verify(self,credential):return p.Actor(['synthetic-issuer'],'synthetic-subject',datetime.now(timezone.utc)+timedelta(minutes=1))
    store=p.Registration(app.state.db,store_epoch='synthetic-store-1',verifier=WrongVerifier(),authorizer=A())
    with pytest.raises(HTTPException) as error:run(store)
    assert error.value.status_code==401
    assert counts(app)==(0,0,0)

def test_python_write_lock_precedes_begin_and_covers_commit(setup):
    from mcis_service.db import WRITE_LOCK
    app,store=setup;observed=[]
    def statement(conn,cursor,sql,*args):
        if sql=='BEGIN IMMEDIATE':observed.append(('begin',WRITE_LOCK._is_owned()))
    def committed(conn):observed.append(('commit',WRITE_LOCK._is_owned()))
    event.listen(app.state.db.engine,'before_cursor_execute',statement)
    event.listen(app.state.db.engine,'commit',committed)
    try:
        key=str(uuid.uuid4());original=run(store,key)
        assert run(store,key,recover=True)==original
    finally:
        event.remove(app.state.db.engine,'before_cursor_execute',statement)
        event.remove(app.state.db.engine,'commit',committed)
    assert observed==[('begin',True),('commit',True),('begin',True),('commit',True)]
