import hashlib
from concurrent.futures import ThreadPoolExecutor
import threading
import pytest
from sqlalchemy import select
from fastapi import HTTPException
from .test_internal_unreviewed_save import setup, counts
from .test_local_authority import provision,call
from .conftest import CASE
from mcis_service.identity import local as auth
from mcis_service.timeline import unreviewed_storage as storage


def test_new_session_same_subject_replay_is_authorized(client,empty_client,monkeypatch):
    target,_,body=setup(client,empty_client,monkeypatch);subject,token=provision(target)
    one=call(target,body,token)
    with target.app.state.db.session() as s:
        auth.revoke_session(s,token);second=auth.issue_session(s,subject)
    assert call(target,body,second)['runId']==one['runId']
    with pytest.raises(HTTPException):call(target,body,token)


def test_other_subject_cannot_replay_operation(client,empty_client,monkeypatch):
    target,_,body=setup(client,empty_client,monkeypatch);_,token=provision(target)
    call(target,body,token);_,other=provision(target)
    with pytest.raises(HTTPException) as e:call(target,body,other)
    assert e.value.status_code==409 and counts(target)==(1,1)


def test_revocation_commits_during_core_and_prevents_save(client,empty_client,monkeypatch):
    target,_,body=setup(client,empty_client,monkeypatch);_,token=provision(target)
    reached=threading.Event();released=threading.Event();old=storage.preview_alignment
    def computation(*args):
        result=old(*args);reached.set();assert released.wait(5);return result
    monkeypatch.setattr(storage,'preview_alignment',computation)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(call,target,body,token)
        assert reached.wait(5)
        with target.app.state.db.session() as s:auth.revoke_session(s,token)
        released.set()
        with pytest.raises(HTTPException) as error:future.result(timeout=5)
    assert error.value.status_code==403 and counts(target)==(0,0)


def test_no_raw_token_storage(client,empty_client,monkeypatch):
    target,_,_=setup(client,empty_client,monkeypatch);subject,token=provision(target)
    with target.app.state.db.session() as s:
        row=s.scalar(select(auth.SessionRecord))
        assert row.token_hash==hashlib.sha256(token.encode()).hexdigest()
        assert token not in repr(row.__dict__)
        assert row.subject_id==subject


def test_existing_deferred_transaction_must_not_claim_reserved_writer(client,empty_client,monkeypatch):
    target,_,_=setup(client,empty_client,monkeypatch);_,token=provision(target)
    with target.app.state.db.session() as s:
        s.connection().exec_driver_sql('BEGIN')
        # A reusable authorization kernel must refuse a transaction whose writer
        # reservation it cannot prove, rather than returning a trusted authority.
        with pytest.raises(HTTPException):auth.authorize_save(s,token,CASE)


def test_reserved_authorization_blocks_revocation_until_transaction_finishes(client,empty_client,monkeypatch):
    target,_,_=setup(client,empty_client,monkeypatch);_,token=provision(target)
    started=threading.Event();done=threading.Event()
    def revoke():
        started.set()
        with target.app.state.db.session() as other:auth.revoke_session(other,token)
        done.set()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with target.app.state.db.session() as s:
            assert auth.authorize_save(s,token,CASE).role=='LeadInvestigator'
            future=pool.submit(revoke)
            assert started.wait(3)
            assert not done.wait(.15)
        future.result(timeout=5)
        assert done.is_set()
    with target.app.state.db.session() as s:
        with pytest.raises(HTTPException):auth.authorize_save(s,token,CASE)


def test_rolled_back_provisioning_creates_no_identity(client,empty_client,monkeypatch):
    target,_,_=setup(client,empty_client,monkeypatch)
    with pytest.raises(RuntimeError):
        with target.app.state.db.session() as s:
            subject=auth.create_subject(s);token=auth.issue_session(s,subject)
            auth.set_membership(s,subject,CASE,role='LeadInvestigator',can_save_unreviewed=True)
            raise RuntimeError('injected')
    with target.app.state.db.session() as s:
        assert not list(s.scalars(select(auth.Subject)))
        assert not list(s.scalars(select(auth.SessionRecord)))
        assert not list(s.scalars(select(auth.Membership)))
        with pytest.raises(HTTPException):auth.authorize_save(s,token,CASE)


@pytest.mark.parametrize('field,value',[('case_id','other-case'),('case_incarnation','00000000-0000-4000-8000-000000000099')])
def test_membership_is_bound_to_exact_local_case(client,empty_client,monkeypatch,field,value):
    target,_,body=setup(client,empty_client,monkeypatch);_,token=provision(target)
    with target.app.state.db.session() as s:
        auth.begin(s);row=s.scalar(select(auth.Membership));setattr(row,field,value)
    with pytest.raises(HTTPException) as error:call(target,body,token)
    assert error.value.status_code==403 and counts(target)==(0,0)


def test_auth_receipt_cannot_reuse_previous_transaction_proof(client,empty_client,monkeypatch):
    target,_,_=setup(client,empty_client,monkeypatch);_,token=provision(target)
    with target.app.state.db.session() as s:
        auth.authorize_save(s,token,CASE)
        s.commit()
        s.connection().exec_driver_sql('BEGIN')
        with pytest.raises(HTTPException):auth.authorize_save(s,token,CASE)


@pytest.mark.parametrize('replay',[False,True])
def test_expiry_during_capture_cannot_return_or_write(client,empty_client,monkeypatch,replay):
    target,_,body=setup(client,empty_client,monkeypatch);_,token=provision(target)
    if replay:call(target,body,token)
    with target.app.state.db.session() as s:expires=s.scalar(select(auth.SessionRecord)).expires_at
    old=storage.capture
    def capture(*args):
        result=old(*args)
        monkeypatch.setattr(auth.time,'time',lambda:expires+1)
        return result
    monkeypatch.setattr(storage,'capture',capture)
    with pytest.raises(HTTPException) as error:call(target,body,token)
    assert error.value.status_code==403
    assert counts(target)==((1,1) if replay else (0,0))


def test_expiry_during_final_capture_rolls_back(client,empty_client,monkeypatch):
    target,_,body=setup(client,empty_client,monkeypatch);_,token=provision(target)
    with target.app.state.db.session() as s:expires=s.scalar(select(auth.SessionRecord)).expires_at
    old=storage.capture;calls=0
    def capture(*args):
        nonlocal calls
        result=old(*args);calls+=1
        if calls==2:monkeypatch.setattr(auth.time,'time',lambda:expires+1)
        return result
    monkeypatch.setattr(storage,'capture',capture)
    with pytest.raises(HTTPException) as error:call(target,body,token)
    assert calls==2 and error.value.status_code==403 and counts(target)==(0,0)
