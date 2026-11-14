import asyncio
import json
import pytest
from .test_internal_unreviewed_save import setup,counts
from .test_local_authority import provision
from .test_identity_http_trial import payload
from .conftest import C,CASE
from mcis_service.identity import http_trial as http,local


def invoke(target,token,*,body=b'{}',headers=None,path=None,method='POST',query=b'',events=None,on_receive=None):
    sent=[];reads=[]
    stream=list(events if events is not None else [{'type':'http.request','body':body}])
    async def receive():
        reads.append(True)
        if on_receive:on_receive()
        if not stream:raise AssertionError('excess body read')
        return stream.pop(0)
    async def send(event):sent.append(event)
    scope={'type':'http','method':method,'path':path or C+'/timeline/unreviewed-runs','query_string':query,
        'headers':headers if headers is not None else [(b'authorization',('Bearer '+token).encode()),(b'content-type',b'application/json')]}
    app=http.create_identity_trial_app(db=target.app.state.db,settings=target.app.state.settings)
    asyncio.run(app(scope,receive,send))
    return sent,reads


def check(sent,status):
    assert sent[0]['status']==status
    assert (b'cache-control',b'no-store') in sent[0]['headers']


def test_very_long_content_length_fails_closed(client,empty_client,monkeypatch):
    target,_,_=setup(client,empty_client,monkeypatch);_,token=provision(target)
    sent,reads=invoke(target,token,headers=[(b'authorization',('Bearer '+token).encode()),(b'content-type',b'application/json'),(b'content-length',b'9'*5000)])
    check(sent,413);assert not reads


def test_stream_limit_stops_receiving(client,empty_client,monkeypatch):
    target,_,_=setup(client,empty_client,monkeypatch);_,token=provision(target)
    events=[{'type':'http.request','body':b'x'*40000,'more_body':True}]*3
    sent,reads=invoke(target,token,events=events)
    check(sent,413);assert len(reads)==2 and counts(target)==(0,0)


@pytest.mark.parametrize('variant',['double-auth','double-type','fake-role','double-length'])
def test_duplicate_headers_and_fake_role(client,empty_client,monkeypatch,variant):
    target,_,_=setup(client,empty_client,monkeypatch);_,token=provision(target)
    headers=[(b'authorization',('Bearer '+token).encode()),(b'content-type',b'application/json')]
    if variant=='double-auth':headers.append((b'Authorization',('Bearer '+token).encode()))
    if variant=='double-type':headers.append((b'Content-Type',b'application/json'))
    if variant=='double-length':headers += [(b'content-length',b'2')]*2
    if variant=='fake-role':headers=[(b'x-mcis-role',b'LeadInvestigator'),(b'x-mcis-operator',b'owner'),(b'content-type',b'application/json')]
    sent,reads=invoke(target,token,headers=headers)
    check(sent,413 if variant=='double-length' else 400);assert not reads


def test_unauthorized_body_never_read(client,empty_client,monkeypatch):
    target,_,_=setup(client,empty_client,monkeypatch)
    sent,reads=invoke(target,'a'*43)
    check(sent,403);assert not reads


def test_revocation_while_body_arrives(client,empty_client,monkeypatch):
    target,_,body=setup(client,empty_client,monkeypatch);_,token=provision(target)
    def revoke():
        with target.app.state.db.session() as s:local.revoke_session(s,token)
    sent,_=invoke(target,token,body=json.dumps(payload(body)).encode(),on_receive=revoke)
    check(sent,403);assert counts(target)==(0,0)


@pytest.mark.parametrize('suffix',['/export','/audit','/access-policy','/evidence','/timeline/unreviewed-runs/','//timeline/unreviewed-runs','/timeline/%75nreviewed-runs'])
def test_concrete_route_bypass_refused(client,empty_client,monkeypatch,suffix):
    target,_,_=setup(client,empty_client,monkeypatch);_,token=provision(target)
    sent,reads=invoke(target,token,path=C+suffix)
    check(sent,404);assert not reads


def test_unknown_save_exception_sanitized(client,empty_client,monkeypatch):
    target,_,body=setup(client,empty_client,monkeypatch);_,token=provision(target)
    def fail(*args):raise RuntimeError('TOKEN '+token+' /secret/filename')
    monkeypatch.setattr(http,'save_authenticated_unreviewed',fail)
    sent,_=invoke(target,token,body=json.dumps(payload(body)).encode())
    check(sent,503)
    assert b'secret' not in sent[1]['body'] and token.encode() not in sent[1]['body']


def test_receive_timeout_is_bounded_error(client,empty_client,monkeypatch):
    target,_,_=setup(client,empty_client,monkeypatch);_,token=provision(target)
    async def timeout(awaitable,seconds):
        awaitable.close();assert 0<seconds<=10;raise TimeoutError()
    monkeypatch.setattr(http.asyncio,'wait_for',timeout)
    sent,reads=invoke(target,token)
    check(sent,408);assert not reads


def test_disconnect_no_save_or_response(client,empty_client,monkeypatch):
    target,_,_=setup(client,empty_client,monkeypatch);_,token=provision(target)
    sent,reads=invoke(target,token,events=[{'type':'http.disconnect'}])
    assert not sent and len(reads)==1 and counts(target)==(0,0)


def test_unknown_authorize_exception_no_body_or_leak(client,empty_client,monkeypatch):
    target,_,_=setup(client,empty_client,monkeypatch);_,token=provision(target)
    def fail(*args):raise RuntimeError('secret '+token)
    monkeypatch.setattr(http,'authorize_save',fail)
    sent,reads=invoke(target,token)
    check(sent,503);assert not reads and token.encode() not in sent[1]['body']


def test_valid_token_ignores_forged_role_operator(client,empty_client,monkeypatch):
    target,_,body=setup(client,empty_client,monkeypatch);subject,token=provision(target)
    headers=[(b'authorization',('Bearer '+token).encode()),(b'content-type',b'application/json'),
        (b'x-mcis-role',b'Public'),(b'x-mcis-operator',b'forged')]
    sent,_=invoke(target,token,headers=headers,body=json.dumps(payload(body)).encode())
    check(sent,200)
    from mcis_service.audit.service import all_lines
    with target.app.state.db.session() as s:
        lines=''.join(all_lines(s,CASE))
    assert subject in lines and 'forged' not in lines
