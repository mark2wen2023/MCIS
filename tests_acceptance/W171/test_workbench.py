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
    """Real concurrency with deterministic Event sync and an observable lock check.

    The endpoint reserves the SQLite writer (BEGIN IMMEDIATE) before its first read.
    A zero-timeout BEGIN IMMEDIATE on a separate connection must see SQLITE_BUSY while
    that transaction is open. The racing writer then runs on its own thread and commits
    only after the reader is released. GET itself does not write audit rows: the one new
    policy.update event is produced by the concurrent writer.
    """
    import sqlite3,threading
    from mcis_service.access_workbench import router as r
    save(client)
    original=r.get_doc
    reading=threading.Event();release=threading.Event();outcome={};threads=[]
    def raced(session,model,cid,key):
        result=original(session,model,cid,key)
        if not reading.is_set():
            reading.set()
            assert release.wait(10) is True,'release.wait() did not succeed while the reader held the transaction'
        return result
    def writer():
        try:
            with client.app.state.db.session() as other:
                policy=default_policy();policy['version']='2.0.0'
                put_doc(other,AccessPolicyRow,'CASE-A','policy',policy)
                event(other,command='version-2')
            outcome['ok']=True
        except Exception as e:
            outcome['error']=repr(e)
    def policy_update_commands():
        with client.app.state.db.session() as s:
            evs=audit.list_events(s,'CASE-A',category='Access',action='policy.update',
                                  entity_type='accessPolicy',entity_id='policy',newest_first=True)
            return [e['command'] for e in evs]
    assert policy_update_commands()==[]
    monkeypatch.setattr(r,'get_doc',raced)
    result={}
    getter=threading.Thread(target=lambda:result.update(out=client.get(url())),daemon=True)
    threads.append(getter);getter.start()
    try:
        assert reading.wait(10) is True,'reader did not reach the mid-transaction sync point'
        db_path=client.app.state.db.engine.url.database
        assert db_path,db_path
        probe=sqlite3.connect(db_path,timeout=0)
        probe.isolation_level=None
        try:
            try:
                probe.execute('BEGIN IMMEDIATE')
                raise AssertionError('expected SQLITE_BUSY from BEGIN IMMEDIATE timeout=0 while the reader holds the reserved writer')
            except sqlite3.OperationalError as e:
                msg=str(e).lower()
                assert 'locked' in msg or 'busy' in msg,e
                outcome['busy']=str(e)
        finally:
            probe.close()
        thread=threading.Thread(target=writer,daemon=True)
        threads.append(thread);thread.start()
    finally:
        release.set()
        for t in threads:
            t.join(15)
            assert not t.is_alive(),'thread still alive after join: '+t.name
    assert outcome.get('ok') is True and 'error' not in outcome,outcome
    assert 'busy' in outcome,outcome
    out=result['out'];assert out.status_code==200,out.text
    d=out.json()
    assert d['policy']['version']=='1.0.0' and [e['command'] for e in d['policyAudit']['events']]==[]
    assert policy_update_commands()==['version-2']
    after=client.get(url());assert after.status_code==200,after.text
    a=after.json()
    assert a['policy']['version']=='2.0.0' and [e['command'] for e in a['policyAudit']['events']]==['version-2']
    assert policy_update_commands()==['version-2']  # the follow-up GET is read-only and adds no audit row


