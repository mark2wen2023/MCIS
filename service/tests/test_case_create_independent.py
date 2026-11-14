"""Independent same-process concurrency and transactional rollback checks."""
from concurrent.futures import ThreadPoolExecutor
import threading
import pytest
from sqlalchemy import text
from .conftest import C,CASE,H


def counts(target):
    with target.app.state.db.session() as s:
        return tuple(s.execute(text(q),{'c':CASE}).scalar() for q in [
            'SELECT COUNT(*) FROM cases WHERE case_id=:c',
            "SELECT COUNT(*) FROM audit_events WHERE case_id=:c AND action='case.create'"])

@pytest.mark.parametrize('role',['Public','AgentService','ExternalExpert','InterestedState'])
def test_unprivileged_create_has_no_case_or_audit(client,empty_client,role):
    body=client.get(C,headers=H()).json()
    assert empty_client.post('/api/v1/cases',headers=H(role),json=body).status_code==403
    assert counts(empty_client)==(0,0)


def test_four_concurrent_creates_one_case_one_audit(client,empty_client):
    body=client.get(C,headers=H()).json();start=threading.Barrier(4)
    def post(n):
        start.wait(timeout=5)
        return empty_client.post('/api/v1/cases',headers=H(),json={**body,'title':str(n)})
    with ThreadPoolExecutor(max_workers=4) as pool:responses=list(pool.map(post,range(4)))
    assert sorted(r.status_code for r in responses)==[201,409,409,409]
    assert counts(empty_client)==(1,1)
    winner=next(r.json()['title'] for r in responses if r.status_code==201)
    assert empty_client.get(C,headers=H()).json()['title']==winner


def test_audit_failure_rolls_back_case_and_retry_is_clean(client,empty_client,monkeypatch):
    from mcis_service.cases import router
    body=client.get(C,headers=H()).json();seen=[];original=router.audit.append
    def fail(s,**kwargs):
        original(s,**kwargs)
        seen.append(s.execute(text('SELECT COUNT(*) FROM cases WHERE case_id=:c'),{'c':CASE}).scalar())
        raise RuntimeError('injected after audit append')
    with monkeypatch.context() as patch:
        patch.setattr(router.audit,'append',fail)
        try:
            response=empty_client.post('/api/v1/cases',headers=H(),json=body)
            assert response.status_code==500
        except RuntimeError as e:assert str(e)=='injected after audit append'
    assert seen==[1]
    assert counts(empty_client)==(0,0)
    assert empty_client.post('/api/v1/cases',headers=H(),json=body).status_code==201
    assert counts(empty_client)==(1,1)


def test_commit_failure_rolls_back_case_and_audit(client,empty_client,monkeypatch):
    from sqlalchemy.orm import Session
    body=client.get(C,headers=H()).json();seen=[]
    def fail(s):
        s.flush()
        seen.append(s.execute(text('SELECT COUNT(*) FROM cases WHERE case_id=:c'),{'c':CASE}).scalar())
        raise RuntimeError('injected commit failure')
    with monkeypatch.context() as patch:
        patch.setattr(Session,'commit',fail)
        try:
            response=empty_client.post('/api/v1/cases',headers=H(),json=body)
            assert response.status_code==500
        except RuntimeError as e:assert str(e)=='injected commit failure'
    assert seen==[1]
    assert counts(empty_client)==(0,0)
    assert empty_client.post('/api/v1/cases',headers=H(),json=body).status_code==201
    assert counts(empty_client)==(1,1)
