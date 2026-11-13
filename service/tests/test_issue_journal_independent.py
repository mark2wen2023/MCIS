import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import HTTPException
from sqlalchemy import select,text
from sqlalchemy.orm import Session
from .test_issue_journal import ready,add
from .test_internal_unreviewed_save import setup
from .test_local_authority import provision
from .conftest import CASE
from mcis_service.identity import local
from mcis_service.investigation import journal as j


def count(target):
    with target.app.state.db.session() as s:return len(list(s.scalars(select(j.Event))))


def test_import_does_not_implicitly_initialize(client,empty_client,monkeypatch):
    target,r,_=setup(client,empty_client,monkeypatch)
    with target.app.state.db.engine.connect() as c:
        names=set(c.execute(text("select name from sqlite_master where type='table'" )).scalars())
    assert 'investigation_issue_events' not in names
    assert 'investigation_issue_grants' not in names


def test_same_operation_different_actor_rejected(ready):
    target,r,subject,token,i=ready;op=str(uuid.uuid4());add(ready,0,op=op)
    other,other_token=provision(target)
    with target.app.state.db.session() as s:j.grant(s,other,CASE,enabled=True)
    with pytest.raises(HTTPException) as error:
        j.append(target.app.state.db,target.app.state.settings,other_token,CASE,i,op,0,{'kind':'judgment','note':'初步判断'})
    assert error.value.status_code==409 and count(target)==1
    assert j.read(target.app.state.db,other_token,CASE,i)['events'][0]['authorSubjectId']==subject


def test_same_operation_concurrent_exactly_once(ready):
    op=str(uuid.uuid4())
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(lambda _:add(ready,0,op=op),range(2)))
    assert sorted(r['replayed'] for r in results)==[False,True]
    assert count(ready[0])==1


def test_distinct_operations_concurrent_revision_conflict(ready):
    def attempt(_):
        try:return add(ready,0)['revision']
        except HTTPException as error:return error.status_code
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(attempt,range(2)))
    assert sorted(results)==[1,409] and count(ready[0])==1


def test_commit_failure_rolls_back_and_retry(ready,monkeypatch):
    target=ready[0];op=str(uuid.uuid4());original=Session.commit
    def fail(s):raise RuntimeError('injected failure')
    monkeypatch.setattr(Session,'commit',fail)
    with pytest.raises(RuntimeError):add(ready,0,op=op)
    monkeypatch.setattr(Session,'commit',original)
    assert count(target)==0
    assert add(ready,0,op=op)['revision']==1 and count(target)==1


def test_source_changes_at_final_check_roll_back(ready,monkeypatch):
    target,r,_,_,_=ready;original=j.source_current;calls=0
    def changed(*args):
        nonlocal calls
        calls+=1
        if calls==2:(target.app.state.settings.blob_dir/CASE/r['evidence']['relativePath']).write_bytes(b'changed')
        return original(*args)
    monkeypatch.setattr(j,'source_current',changed)
    with pytest.raises(HTTPException):add(ready,0,sourceIds=[r['evidenceId']])
    assert count(target)==0


def test_replay_is_historical_not_current_source(ready,monkeypatch):
    target,r,_,token,i=ready;op=str(uuid.uuid4());add(ready,0,op=op,sourceIds=[r['evidenceId']])
    (target.app.state.settings.blob_dir/CASE/r['evidence']['relativePath']).write_bytes(b'changed')
    monkeypatch.setattr(j,'source_current',lambda *_:pytest.fail('historical replay should not attest current bytes'))
    replay=add(ready,0,op=op,sourceIds=[r['evidenceId']])
    assert replay['replayed'] and replay['sourceSnapshots']=='historical-at-entry-not-current-attestation'
    assert j.read(target.app.state.db,token,CASE,i)['revision']==1 and count(target)==1


@pytest.mark.parametrize('change',['session','grant','member'])
def test_final_revocation_rolls_back(ready,monkeypatch,change):
    target,r,subject,token,i=ready;original=j.project
    def changed(*args):
        response=original(*args)
        # project is inside same write transaction. Mutate via current session
        # intercepted below, not a second connection blocked by writer reservation.
        return response
    original_auth=j.auth;calls=0
    def auth(s,*args,**kwargs):
        nonlocal calls
        calls+=1
        if calls==2:
            if change=='session':local.revoke_session(s,token)
            elif change=='grant':j.grant(s,subject,CASE,enabled=False)
            else:local.set_membership(s,subject,CASE,role='LeadInvestigator',enabled=False)
        return original_auth(s,*args,**kwargs)
    monkeypatch.setattr(j,'auth',auth)
    with pytest.raises(HTTPException) as error:add(ready,0)
    assert error.value.status_code==403 and count(target)==0


def test_new_judgment_invalidates_old_verification_for_discussion(ready):
    add(ready,0);add(ready,1,'verification',outcome='supports',againstJudgment=1)
    add(ready,2,'judgment','另一种可能')
    for reference in (1,3):
        with pytest.raises(HTTPException) as error:add(ready,3,'discussion','集体讨论',againstJudgment=reference)
        assert error.value.status_code==409
    assert count(ready[0])==3


def test_no_write_grant_from_save_grant(client,empty_client,monkeypatch):
    target,r,_=setup(client,empty_client,monkeypatch);subject,token=provision(target);j.initialize(target.app.state.db)
    with pytest.raises(HTTPException) as error:
        j.append(target.app.state.db,target.app.state.settings,token,CASE,str(uuid.uuid4()),str(uuid.uuid4()),0,{'kind':'judgment','note':'未授权'})
    assert error.value.status_code==403 and count(target)==0


@pytest.mark.parametrize('method',['read','list'])
def test_read_materialization_expiry_no_result(ready,monkeypatch,method):
    target,r,subject,token,i=ready;add(ready,0);original=j.auth;calls=0
    def expired(s,*args,**kwargs):
        nonlocal calls
        calls+=1
        if calls==2:
            s.scalar(select(local.SessionRecord)).expires_at=0
        return original(s,*args,**kwargs)
    monkeypatch.setattr(j,'auth',expired)
    with pytest.raises(HTTPException) as error:
        if method=='read':j.read(target.app.state.db,token,CASE,i)
        else:j.list_issues(target.app.state.db,token,CASE)
    assert error.value.status_code==403


def test_read_permission_does_not_need_write_grant(ready):
    target,_,subject,token,i=ready;add(ready,0)
    with target.app.state.db.session() as s:j.grant(s,subject,CASE,enabled=False)
    assert j.read(target.app.state.db,token,CASE,i)['revision']==1
    assert j.list_issues(target.app.state.db,token,CASE)['items'][0]['issueId']==i


@pytest.mark.parametrize('extra',[{'approved':True},{'role':'LeadInvestigator'},{'authorSubjectId':'forged'}])
def test_no_client_approval_or_actor_injection(ready,extra):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):add(ready,0,**extra)
    assert count(ready[0])==0
