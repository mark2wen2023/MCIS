import hashlib,json,uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import HTTPException
from sqlalchemy import select,text
from sqlalchemy.orm import Session
from .test_issue_archive import bundle
from .test_issue_journal import ready
from .conftest import CASE
from mcis_service.investigation import archive as a,journal as j
from mcis_service.identity import local

def repack(p):return a.canonical({'sha256':hashlib.sha256(a.canonical(p)).hexdigest(),'payload':p})
def count(db):
    with db.session() as s:return len(list(s.scalars(select(a.ImportedArchive))))

@pytest.mark.parametrize('damage',['missing','extra','base64','duplicatecard','sourcecase','sourceepoch','versionbool','duplicateid'])
def test_strict_damage(bundle,damage):
    v,raw=bundle;t,_,_,token,_=v;p=json.loads(raw)['payload'];e=p['cards'][0]['events'][0]
    if damage=='missing':p['sources']={}
    elif damage=='extra':p['sources'][hashlib.sha256(b'x').hexdigest()]='eA=='
    elif damage=='base64':p['sources'][next(iter(p['sources']))]+='!'
    elif damage=='duplicatecard':p['cards'].append(p['cards'][0])
    elif damage=='sourcecase':e['sourceSnapshots'][0]['caseId']='FOREIGN'
    elif damage=='sourceepoch':e['sourceSnapshots'][0]['caseIncarnation']=str(uuid.uuid4())
    elif damage=='versionbool':e['sourceSnapshots'][0]['version']=True
    elif damage=='duplicateid':e['sourceIds']*=2;e['sourceSnapshots']*=2
    elif damage=='eventepoch':e['caseEpochUtc']='2000-01-01T00:00:00Z'
    with pytest.raises(HTTPException):a.restore_bundle(t.app.state.db,token,CASE,repack(p))
    assert count(t.app.state.db)==0

def test_commit_failure_atomic(bundle,monkeypatch):
    v,raw=bundle;t,_,_,token,_=v;db=t.app.state.db;old=Session.commit
    monkeypatch.setattr(Session,'commit',lambda _:(_ for _ in ()).throw(RuntimeError('injected')))
    with pytest.raises(RuntimeError):a.restore_bundle(db,token,CASE,raw)
    monkeypatch.setattr(Session,'commit',old)
    assert count(db)==0
    assert not a.restore_bundle(db,token,CASE,raw)['replayed']

def test_final_grant_revoke_rollsback(bundle,monkeypatch):
    v,raw=bundle;t,_,sub,token,_=v;old=j.auth;calls=0
    def auth(s,*args,**kwargs):
        nonlocal calls
        calls+=1
        if calls==2:j.grant(s,sub,CASE,enabled=False)
        return old(s,*args,**kwargs)
    monkeypatch.setattr(j,'auth',auth)
    with pytest.raises(HTTPException):a.restore_bundle(t.app.state.db,token,CASE,raw)
    assert count(t.app.state.db)==0

def test_historical_author_never_activated(bundle):
    v,raw=bundle;t,_,_,token,_=v;p=json.loads(raw)['payload'];fake=str(uuid.uuid4())
    for e in p['cards'][0]['events']:e['authorSubjectId']=fake
    with t.app.state.db.session() as s:before={table:s.execute(text('select count(*) from '+table)).scalar() for table in ('investigation_issue_events','investigation_issue_grants')}
    result=a.restore_bundle(t.app.state.db,token,CASE,repack(p));assert not result['activated']
    with t.app.state.db.session() as s:
        for table,n in before.items():assert s.execute(text('select count(*) from '+table)).scalar()==n
        assert s.get(local.Subject,fake) is None

def test_duplicate_json_and_size(bundle):
    v,raw=bundle;t,_,_,token,_=v
    for invalid in (b'{"sha256":"a","sha256":"b","payload":{}}',b' '* (a.MAX_BYTES+1)):
        with pytest.raises(HTTPException):a.restore_bundle(t.app.state.db,token,CASE,invalid)
    assert count(t.app.state.db)==0

def test_concurrent_replay(bundle):
    v,raw=bundle;t,_,_,token,_=v
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(lambda _:a.restore_bundle(t.app.state.db,token,CASE,raw),range(2)))
    assert sorted(x['replayed'] for x in results)==[False,True]
    assert count(t.app.state.db)==1

def test_initialization_explicit(ready):
    db=ready[0].app.state.db
    with db.engine.connect() as c:assert 'investigation_imported_archives' not in set(c.execute(text("select name from sqlite_master where type='table'")).scalars())

@pytest.mark.parametrize('op',['UPDATE','DELETE'])
def test_imported_immutable(bundle,op):
    v,raw=bundle;t,_,_,token,_=v;db=t.app.state.db;a.restore_bundle(db,token,CASE,raw)
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        with db.engine.begin() as c:c.execute(text('DELETE FROM investigation_imported_archives' if op=='DELETE' else "UPDATE investigation_imported_archives SET imported_by='changed'"))
    assert count(db)==1

def test_export_final_bytes_check(bundle,monkeypatch):
    v,_=bundle;t,r,_,token,_=v;old=j.source_current;calls=0
    def current(*args):
        nonlocal calls
        calls+=1
        if calls==2:(t.app.state.settings.blob_dir/CASE/r['evidence']['relativePath']).write_bytes(b'changed')
        return old(*args)
    monkeypatch.setattr(j,'source_current',current)
    with pytest.raises(HTTPException):a.export_bundle(t.app.state.db,t.app.state.settings,token,CASE)

def test_replay_rechecks_authority(bundle):
    v,raw=bundle;t,_,sub,token,_=v;db=t.app.state.db;a.restore_bundle(db,token,CASE,raw)
    with db.session() as s:local.revoke_session(s,token)
    for action in (lambda:a.restore_bundle(db,token,CASE,raw),lambda:a.read_imported(db,token,CASE,json.loads(raw)['sha256'])):
        with pytest.raises(HTTPException) as e:action()
        assert e.value.status_code==403
    assert count(db)==1


def test_historical_event_epoch_preserved_not_attested(bundle):
    v,raw=bundle;t,_,_,token,_=v;p=json.loads(raw)['payload']
    p['cards'][0]['events'][0]['caseEpochUtc']='2000-01-01T00:00:00Z'
    result=a.restore_bundle(t.app.state.db,token,CASE,repack(p))
    doc=a.read_imported(t.app.state.db,token,CASE,result['sha256'])
    assert not doc['activated'] and doc['status']=='imported_history_untrusted'
    assert doc['payload']['cards'][0]['events'][0]['caseEpochUtc']=='2000-01-01T00:00:00Z'
    assert doc['payload']['exportCaseEpochUtc']!=doc['payload']['cards'][0]['events'][0]['caseEpochUtc']

def test_source_budget_rejected_before_base64_allocation(bundle,monkeypatch):
    v,raw=bundle;t,_,_,token,_=v;p=json.loads(raw)['payload'];p['sources']={}
    # Metadata fits, but only one byte remains for encoded source data.
    monkeypatch.setattr(a,'MAX_BYTES',len(a.canonical(p))+129)
    monkeypatch.setattr(a.base64,'b64encode',lambda _:pytest.fail('must reject before allocating encoded bytes'))
    with pytest.raises(HTTPException) as e:a.export_bundle(t.app.state.db,t.app.state.settings,token,CASE)
    assert e.value.status_code==413
