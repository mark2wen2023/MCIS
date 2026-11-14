import asyncio
import json
import uuid
import pytest
from fastapi.testclient import TestClient
from .test_issue_journal import ready
from .test_issue_http_trial import URL,body
from .test_identity_http_trial import trial,headers
from .test_identity_http_trial_independent import invoke,check
from .test_issue_journal_independent import count
from .conftest import CASE
from mcis_service.identity import local
from mcis_service.investigation import journal, http_trial as issue_http
from mcis_service.protected_app import create_protected_app


def test_authorization_before_body(ready):
    t,_,subject,token,_=ready
    with t.app.state.db.session() as s:journal.grant(s,subject,CASE,enabled=False)
    sent,reads=invoke(t,token,path=URL,body=json.dumps(body(ready)).encode())
    check(sent,403);assert reads==[] and count(t)==0


@pytest.mark.parametrize('variant',['auth','content-type','content-length','role','operator','transfer'])
def test_header_ambiguity_no_receive(ready,variant):
    t,_,_,token,_=ready
    hs=[(b'authorization',('Bearer '+token).encode()),(b'content-type',b'application/json')]
    if variant=='auth':hs.append((b'Authorization',('Bearer '+token).encode()))
    elif variant=='content-type':hs.append((b'Content-Type',b'application/json'))
    elif variant=='content-length':hs.extend([(b'content-length',b'2')]*2)
    elif variant=='role':hs.append((b'x-mcis-role',b'LeadInvestigator'))
    elif variant=='operator':hs.append((b'x-mcis-operator',b'owner'))
    else:hs.append((b'transfer-encoding',b'chunked'))
    sent,reads=invoke(t,token,path=URL,headers=hs)
    check(sent,413 if variant=='content-length' else 400)
    assert not reads and count(t)==0


def test_stream_budget_stops_before_third_chunk(ready):
    t,_,_,token,_=ready
    sent,reads=invoke(t,token,path=URL,events=[{'type':'http.request','body':b'x'*40000,'more_body':True}]*3)
    check(sent,413);assert len(reads)==2 and count(t)==0


def test_body_receive_revoke_grant(ready):
    t,_,subject,token,_=ready
    def revoke():
        with t.app.state.db.session() as s:journal.grant(s,subject,CASE,enabled=False)
    sent,_=invoke(t,token,path=URL,body=json.dumps(body(ready)).encode(),on_receive=revoke)
    check(sent,403);assert count(t)==0


def test_nested_duplicate_json_rejected(ready):
    t,_,_,token,i=ready
    content=json.dumps(body(ready)).replace('"note": "初判"','"note":"one","note":"two"')
    # ensure_ascii output means replace value via exact JSON form instead.
    content='{"issueId":'+json.dumps(i)+',"operationId":'+json.dumps(str(uuid.uuid4()))+',"entry":{"kind":"judgment","note":"one","note":"two"}}'
    sent,_=invoke(t,token,path=URL,body=content.encode())
    check(sent,422);assert count(t)==0


def test_disconnect_no_write(ready):
    sent,_=invoke(ready[0],ready[3],path=URL,events=[{'type':'http.disconnect'}])
    assert not sent and count(ready[0])==0


def test_timeout_sanitized(ready,monkeypatch):
    async def timeout(awaitable,*args):
        awaitable.close()
        raise TimeoutError('private notes')
    monkeypatch.setattr(issue_http.asyncio,'wait_for',timeout)
    sent,_=invoke(ready[0],ready[3],path=URL)
    check(sent,408);assert b'private' not in sent[-1]['body'] and count(ready[0])==0


def test_unexpected_write_exception_is_unknown_not_echoed(ready,monkeypatch):
    def fail(*args):raise RuntimeError('SECRET '+ready[3]+' /private/file')
    monkeypatch.setattr(journal,'append',fail)
    with trial(ready[0]) as api:r=api.post(URL,headers=headers(ready[3]),json=body(ready))
    assert r.status_code==503 and r.json()['code']=='ISSUE_WRITE_UNCONFIRMED_RETRY_SAME_OPERATION'
    assert ready[3] not in r.text and 'private' not in r.text


def test_create_revision_not_override_and_append_zero_rejected(ready):
    t,_,_,token,i=ready
    with trial(t) as api:
        r=api.post(URL,headers=headers(token),json={**body(ready),'expectedRevision':1})
        assert r.status_code==422
        r=api.post(URL+'/'+i+'/events',headers=headers(token),json={'operationId':str(uuid.uuid4()),'expectedRevision':0,'entry':{'kind':'judgment','note':'first'}})
        assert r.status_code==422
    assert count(t)==0


def test_path_not_body_chooses_issue(ready):
    t,_,_,token,i=ready
    with trial(t) as api:
        assert api.post(URL,headers=headers(token),json=body(ready)).status_code==201
        response=api.post(URL+'/'+i+'/events',headers=headers(token),json={'issueId':str(uuid.uuid4()),'operationId':str(uuid.uuid4()),'expectedRevision':1,'entry':{'kind':'judgment','note':'other'}})
    assert response.status_code==422 and count(t)==1


def test_source_corruption_denied_http(ready):
    t,r,_,token,_=ready;b=body(ready);b['entry']['sourceIds']=[r['evidenceId']]
    (t.app.state.settings.blob_dir/CASE/r['evidence']['relativePath']).write_bytes(b'changed')
    with trial(t) as api:response=api.post(URL,headers=headers(token),json=b)
    assert response.status_code==409 and '初判' not in response.text and count(t)==0


def test_default_entry_not_enabled(ready):
    with TestClient(create_protected_app()) as api:
        for method in ('GET','POST','HEAD'):
            r=api.request(method,URL,headers=headers(ready[3]))
            assert r.status_code==503
            if method=='HEAD':assert not r.content


def test_issue_case_name_does_not_shadow_source_catalog(ready):
    with trial(ready[0]) as api:
        r=api.get('/api/v1/trial/cases/issues-example/sources',headers=headers(ready[3]))
    assert r.status_code==403  # catalog authorizes nonexistent/foreign case uniformly


def test_no_implicit_journal_setup(client,empty_client,monkeypatch):
    from sqlalchemy import text
    from .test_internal_unreviewed_save import setup
    from .test_local_authority import provision
    t,_,_=setup(client,empty_client,monkeypatch);_,token=provision(t)
    with trial(t) as api:
        r=api.post(URL,headers=headers(token),json={'issueId':str(uuid.uuid4()),'operationId':str(uuid.uuid4()),'entry':{'kind':'judgment','note':'try'}})
        assert r.status_code==503
        assert api.get(URL,headers=headers(token)).status_code==503
    with t.app.state.db.engine.connect() as c:
        names=set(c.execute(text("select name from sqlite_master where type='table'")).scalars())
    assert 'investigation_issue_events' not in names and 'investigation_issue_grants' not in names


def test_subject_without_case_membership_gets_no_metadata(ready):
    t,_,_,token,i=ready
    with trial(t) as api:assert api.post(URL,headers=headers(token),json=body(ready)).status_code==201
    with t.app.state.db.session() as s:
        other=local.create_subject(s);other_token=local.issue_session(s,other)
    with trial(t) as api:
        for path in (URL,URL+'/'+i,URL.replace(CASE,'FOREIGN')):
            r=api.get(path,headers=headers(other_token))
            assert r.status_code==403 and '初判' not in r.text and i not in r.text


def test_head_unknown_and_encoded_paths_do_not_read(ready):
    t,_,_,token,i=ready
    for path in (URL+'/'+i+'/',URL.replace('/issues','/%69ssues'),URL.replace('/issues','//issues')):
        sent,reads=invoke(t,token,path=path,method='HEAD')
        check(sent,404);assert not reads and sent[-1]['body']==b''
