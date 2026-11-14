import asyncio,json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from .test_issue_archive import bundle
from .test_issue_journal import ready
from .test_issue_archive_http import URL
from .test_identity_http_trial import trial,headers
from .test_identity_http_trial_independent import invoke,check
from .conftest import CASE
from mcis_service.investigation import archive,journal,archive_http_trial as transport
from mcis_service.identity import http_trial
from mcis_service.protected_app import create_protected_app

def count(t):
    with t.app.state.db.session() as s:return len(list(s.scalars(select(archive.ImportedArchive))))

def test_write_authorized_before_receive(bundle):
    v,raw=bundle;t,_,sub,token,_=v
    with t.app.state.db.session() as s:journal.grant(s,sub,CASE,enabled=False)
    sent,reads=invoke(t,token,path=URL+'/import',body=raw)
    check(sent,403);assert not reads and count(t)==0

@pytest.mark.parametrize('kind',['auth','type','length','transfer','operator'])
def test_duplicate_headers_no_read(bundle,kind):
    v,raw=bundle;t,_,_,token,_=v
    hs=[(b'authorization',('Bearer '+token).encode()),(b'content-type',b'application/json')]
    if kind=='auth':hs.append((b'Authorization',('Bearer '+token).encode()))
    elif kind=='type':hs.append((b'Content-Type',b'application/json'))
    elif kind=='length':hs.extend([(b'content-length',b'2')]*2)
    elif kind=='transfer':hs.append((b'transfer-encoding',b'chunked'))
    else:hs.append((b'x-mcis-operator',b'owner'))
    sent,reads=invoke(t,token,path=URL+'/import',body=raw,headers=hs)
    check(sent,413 if kind=='length' else 400);assert not reads and count(t)==0

def test_actual_chunk_budget(bundle):
    v,_=bundle
    sent,reads=invoke(v[0],v[3],path=URL+'/import',events=[{'type':'http.request','body':b'x'*(archive.MAX_BYTES//2+1),'more_body':True}]*3)
    check(sent,413);assert len(reads)==2 and count(v[0])==0

def test_declared_length_mismatch(bundle):
    v,raw=bundle;hs=[(b'authorization',('Bearer '+v[3]).encode()),(b'content-type',b'application/json'),(b'content-length',b'2')]
    sent,_=invoke(v[0],v[3],path=URL+'/import',body=raw,headers=hs)
    check(sent,422);assert count(v[0])==0

def test_revoke_while_receiving(bundle):
    v,raw=bundle;t,_,sub,token,_=v
    def revoke():
        with t.app.state.db.session() as s:journal.grant(s,sub,CASE,enabled=False)
    sent,_=invoke(t,token,path=URL+'/import',body=raw,on_receive=revoke)
    check(sent,403);assert count(t)==0

def test_disconnect_no_commit(bundle):
    v,_=bundle;sent,_=invoke(v[0],v[3],path=URL+'/import',events=[{'type':'http.disconnect'}])
    assert not sent and count(v[0])==0

def test_cancel_receive_no_commit(bundle):
    v,_=bundle;t=v[0];app=http_trial.create_identity_trial_app(db=t.app.state.db,settings=t.app.state.settings)
    async def receive():raise asyncio.CancelledError()
    async def send(_):pytest.fail('no result after receive cancellation')
    scope={'type':'http','method':'POST','path':URL+'/import','headers':[(b'authorization',('Bearer '+v[3]).encode()),(b'content-type',b'application/json')]}
    with pytest.raises(asyncio.CancelledError):asyncio.run(app(scope,receive,send))
    assert count(t)==0

def test_timeout_before_restore(bundle,monkeypatch):
    v,_=bundle
    async def timeout(coro,*args):coro.close();raise TimeoutError('private')
    monkeypatch.setattr(transport.asyncio,'wait_for',timeout)
    sent,_=invoke(v[0],v[3],path=URL+'/import')
    check(sent,408);assert count(v[0])==0 and b'private' not in sent[-1]['body']

def test_committed_response_failure_retry(bundle,monkeypatch):
    v,raw=bundle;t=v[0];old=archive.restore_bundle
    def lost(*args):old(*args);raise RuntimeError('SECRET '+v[3])
    monkeypatch.setattr(archive,'restore_bundle',lost)
    with trial(t) as api:r=api.post(URL+'/import',headers=headers(v[3]),content=raw)
    assert r.status_code==503 and 'UNCONFIRMED' in r.text and v[3] not in r.text and count(t)==1
    monkeypatch.setattr(archive,'restore_bundle',old)
    with trial(t) as api:r=api.post(URL+'/import',headers=headers(v[3]),content=raw)
    assert r.json()['replayed'] and not r.json()['activated'] and count(t)==1

@pytest.mark.parametrize('path',[URL+'/export',URL,URL+'/'+'a'*64])
def test_head_no_materialization(bundle,path,monkeypatch):
    v,_=bundle
    monkeypatch.setattr(archive,'export_bundle',lambda *a:pytest.fail('HEAD must not materialize'))
    sent,reads=invoke(v[0],v[3],path=path,method='HEAD')
    check(sent,404);assert not reads and sent[-1]['body']==b''

def test_default_not_mounted(bundle):
    with TestClient(create_protected_app()) as api:assert api.get(URL).status_code==503

def test_export_exact_bytes_security_headers(bundle):
    v,raw=bundle
    with trial(v[0]) as api:r=api.get(URL+'/export',headers=headers(v[3]))
    assert r.content==raw and isinstance(r.json(),dict)
    assert r.headers['content-disposition']=='attachment; filename="mcis-issue-history.json"'
    assert r.headers['x-content-type-options']=='nosniff' and r.headers['cache-control']=='no-store'
    assert int(r.headers['content-length'])==len(raw)

def test_case_name_does_not_capture_catalog(bundle):
    v,_=bundle;sent,_=invoke(v[0],v[3],path='/api/v1/trial/cases/issue-archives-example/sources',method='GET')
    check(sent,403)

def test_no_implicit_import_schema(ready):
    from sqlalchemy import text
    t,_,_,token,_=ready
    with trial(t) as api:r=api.get(URL,headers=headers(token))
    assert r.status_code==503
    with t.app.state.db.engine.connect() as c:assert 'investigation_imported_archives' not in set(c.execute(text("select name from sqlite_master where type='table'")).scalars())
