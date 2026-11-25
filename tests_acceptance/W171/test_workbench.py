"""Independent W17.1 black-box acceptance; synthetic cases, no mutation via GET."""
import copy
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,func
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.audit.models import AuditEventRow
from mcis_service.audit import service as audit

@pytest.fixture
def client(tmp_path):
    app=create_app(Settings(data_dir=tmp_path,seed_demo=False))
    with app.state.db.session() as s:
        for cid in ('CASE-A','CASE-B'):
            put_doc(s,CaseRow,cid,cid,{'caseId':cid,'title':cid})
    with TestClient(app) as c:yield c

def url(cid='CASE-A'):return f'/api/v1/cases/{cid}/access-workbench'
def save(client,cid='CASE-A',policy=None):
    with client.app.state.db.session() as s:put_doc(s,AccessPolicyRow,cid,'policy',policy if policy is not None else default_policy())
def event(s,cid='CASE-A',**override):
    d=dict(case_id=cid,operator='acceptance',role='LeadInvestigator',action='policy.update',category='Access',command='policy-test',entity_type='accessPolicy',entity_id='policy')
    d.update(override);return audit.append(s,**d)

@pytest.mark.parametrize('role',['Public','ExternalExpert','InterestedState','AgentService'])
def test_role_denial_identical_for_existing_and_absent(client,role):
    a=client.get(url(),headers={'X-MCIS-Role':role});b=client.get(url('MISSING'),headers={'X-MCIS-Role':role})
    assert a.status_code==b.status_code==403
    assert a.headers.get('cache-control')==b.headers.get('cache-control')=='no-store'
    assert a.json()==b.json()=={'code':'FORBIDDEN','message':'无权查看权限核验工作台'}

@pytest.mark.parametrize('level',['Deny','Redacted','Unknown',None])
def test_current_case_policy_gate(client,level):
    p=default_policy()
    if level is None:del p['matrix']['Investigator']['audit']
    else:p['matrix']['Investigator']['audit']=level
    save(client,policy=p)
    out=client.get(url());assert out.status_code==403
    assert set(out.json())=={'code','message'}


def test_default_saved_and_no_write(client):
    with client.app.state.db.session() as s:
        before=[s.scalar(select(func.count()).select_from(t)) for t in [CaseRow,AccessPolicyRow,AuditEventRow]]
    out=client.get(url());assert out.status_code==200
    assert out.headers.get('cache-control')=='no-store'
    assert out.json()['policySource']=='default' and out.json()['readOnly'] is True
    assert out.json()['identityMode']=='local-role-header' and out.json()['policy']==default_policy()
    with client.app.state.db.session() as s:
        assert before==[s.scalar(select(func.count()).select_from(t)) for t in [CaseRow,AccessPolicyRow,AuditEventRow]]
    save(client);assert client.get(url()).json()['policySource']=='saved'
    assert client.get(url('MISSING')).status_code==404

@pytest.mark.parametrize('n',[0,49,50,51])
def test_four_filters_case_isolation_latest_limit(client,n):
    with client.app.state.db.session() as s:
        for i in range(n):event(s,command=f'match-{i}')
        event(s,category='Case');event(s,action='policy.read');event(s,entity_type='case');event(s,entity_id='other');event(s,cid='CASE-B')
    d=client.get(url()).json()['policyAudit']
    assert d['limit']==50 and d['hasMore']==(n>50)
    assert [e['command'] for e in d['events']]==[f'match-{i}' for i in range(n-1,max(-1,n-51),-1)]
    assert all(e['caseId']=='CASE-A' for e in d['events'])


def test_policy_and_audit_are_one_snapshot(client,monkeypatch):
    """Real concurrency with deterministic sync points (Events), not sleeps-as-correctness.

    The endpoint reserves the SQLite writer (BEGIN IMMEDIATE) before its first read, so a second
    writer must wait until the reader's transaction ends. The racing writer therefore runs on its
    OWN thread: writing from inside the request thread (the previous scheduling) waited on the
    request's own write lock until busy timeout and surfaced as 'database is locked' (HTTP 500).
    """
    import threading
    from mcis_service.access_workbench import router as r
    save(client)
    original=r.get_doc
    reading=threading.Event();release=threading.Event();writer_ready=threading.Event();outcome={}
    def raced(session,model,cid,key):
        result=original(session,model,cid,key)
        if not reading.is_set():
            reading.set()  # policy read done; the endpoint's transaction is still open
            assert writer_ready.wait(10),'writer thread did not start'
            release.wait(10)
        return result
    def writer():
        reading.wait(10)
        writer_ready.set()
        try:
            # Commit from another database connection and thread while the reader is mid-request.
            with client.app.state.db.session() as other:
                policy=default_policy();policy['version']='2.0.0'
                put_doc(other,AccessPolicyRow,'CASE-A','policy',policy)
                event(other,command='version-2')
            outcome['ok']=True
        except Exception as e:  # recorded and asserted below, never swallowed
            outcome['error']=repr(e)
    monkeypatch.setattr(r,'get_doc',raced)
    thread=threading.Thread(target=writer,daemon=True);thread.start()
    result={}
    getter=threading.Thread(target=lambda:result.update(out=client.get(url())),daemon=True);getter.start()
    assert reading.wait(10) and writer_ready.wait(10)
    thread.join(timeout=0.5)
    assert thread.is_alive(),'concurrent writer must be blocked while the reader transaction is open'
    release.set();getter.join(15);thread.join(15)
    assert not getter.is_alive() and not thread.is_alive()
    assert outcome=={'ok':True},outcome
    out=result['out'];assert out.status_code==200,out.text
    d=out.json()
    assert (d['policy']['version'],[e['command'] for e in d['policyAudit']['events']]) in [('1.0.0',[]),('2.0.0',['version-2'])]
    after=client.get(url()).json()
    assert (after['policy']['version'],[e['command'] for e in after['policyAudit']['events']])==('2.0.0',['version-2'])
