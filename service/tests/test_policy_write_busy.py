"""Real SQLite contention and explicitly simulated transaction failures."""
import sqlite3, threading, time
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from fastapi.testclient import TestClient
from .test_evidence_intake_w42 import local, CASE
from .conftest import H
from mcis_service.redaction.policy import default_policy
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.audit.models import AuditEventRow
from mcis_service.db import put_doc
from mcis_service.redaction import write_access

URL=f'/api/v1/cases/{CASE}/access-policy'
@pytest.fixture
def setup(local):
    _,app=local
    with app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',default_policy())
    @event.listens_for(app.state.db.engine,'checkout')
    def short_timeout(conn,*_):conn.execute('PRAGMA busy_timeout=100')  # Test-only100ms.
    with TestClient(app,raise_server_exceptions=False) as c:yield c,app

def body():
    p=default_policy();p['matrix']['Investigator']['evidence_meta']='Deny';return p

def policy(c):return c.get(URL,headers=H()).json()['matrix']['Investigator']['evidence_meta']
def audits(app):
    with app.state.db.session() as s:return s.query(AuditEventRow).filter_by(action='policy.update').count()
def busy(code=sqlite3.SQLITE_BUSY):
    e=sqlite3.OperationalError('synthetic fault');e.sqlite_errorcode=code
    return OperationalError('synthetic statement',{},e)


def test_actual_timeout_rollback_and_manual_fresh_retry(setup):
    c,app=setup;db=sqlite3.connect(app.state.settings.data_dir/'test.db');db.execute('BEGIN IMMEDIATE')
    try:
        t=time.perf_counter();r=c.put(URL,headers=H('LeadInvestigator'),json=body())
        assert time.perf_counter()-t>=.08
        assert r.status_code==503 and r.json()['code']=='POLICY_WRITE_BUSY',r.text
        assert r.json()['detail']=={'commitState':'not_committed','retryable':True}
        assert policy(c)=='ReadWrite' and audits(app)==0
    finally:db.rollback();db.close()
    latest=c.get(URL,headers=H()).json();latest['matrix']['Investigator']['evidence_meta']='Deny'
    assert c.put(URL,headers=H('LeadInvestigator'),json=latest).status_code==200
    assert policy(c)=='Deny' and audits(app)==1


def test_cross_connection_wait_then_commit(setup):
    c,app=setup;db=sqlite3.connect(app.state.settings.data_dir/'test.db');db.execute('BEGIN IMMEDIATE')
    with ThreadPoolExecutor() as pool:
        f=pool.submit(c.put,URL,headers=H('LeadInvestigator'),json=body())
        time.sleep(.03);assert not f.done();db.rollback();db.close()
        assert f.result(timeout=3).status_code==200
    assert policy(c)=='Deny' and audits(app)==1

@pytest.mark.parametrize('after',[False,True])
def test_commit_errors_are_unknown_not_retryable(setup,monkeypatch,after):
    c,app=setup;original=Session.commit;fired=[]
    def commit(s):
        if s.info.get('_mcis_reserved_writer') and not fired:
            fired.append(True)
            if after:original(s)  # Actually persist before simulated connection/error report.
            raise busy()
        return original(s)
    monkeypatch.setattr(Session,'commit',commit)
    r=c.put(URL,headers=H('LeadInvestigator'),json=body())
    assert r.status_code==500 and r.json()['code']=='INTERNAL_ERROR'
    assert 'retryable' not in r.text and 'not_committed' not in r.text and fired==[True]
    assert policy(c)==('Deny' if after else 'ReadWrite')
    assert audits(app)==(1 if after else 0)


def test_body_error_after_policy_write_rolls_back_not_reclassified(setup,monkeypatch):
    c,app=setup
    from mcis_service.redaction import router
    def fault(*a,**kw):raise busy()
    monkeypatch.setattr(router.audit,'append',fault)
    r=c.put(URL,headers=H('LeadInvestigator'),json=body())
    assert r.status_code==500 and 'not_committed' not in r.text
    assert policy(c)=='ReadWrite' and audits(app)==0


def test_failed_rollback_cannot_claim_retryable(setup,monkeypatch):
    c,app=setup;db=sqlite3.connect(app.state.settings.data_dir/'test.db');db.execute('BEGIN IMMEDIATE')
    original=Session.rollback;calls=[]
    def fail_once(s):
        if not calls:calls.append(True);raise RuntimeError('synthetic rollback failure')
        return original(s)
    monkeypatch.setattr(Session,'rollback',fail_once)
    try:r=c.put(URL,headers=H('LeadInvestigator'),json=body())
    finally:db.rollback();db.close()
    assert r.status_code==500 and 'not_committed' not in r.text
    assert policy(c)=='ReadWrite' and audits(app)==0

@pytest.mark.parametrize('kind',['text_only','other_code','invalidated'])
def test_no_message_matching_or_unknown_connection_claim(setup,monkeypatch,kind):
    c,app=setup;e=busy(sqlite3.SQLITE_IOERR)
    if kind=='text_only':e=OperationalError('',{},sqlite3.OperationalError('database is locked'))
    if kind=='invalidated':e=busy();e.connection_invalidated=True
    def fail(s):raise e
    monkeypatch.setattr(write_access,'begin',fail)
    r=c.put(URL,headers=H('LeadInvestigator'),json=body())
    assert r.status_code==500 and 'not_committed' not in r.text

@pytest.mark.parametrize('code',[sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED,sqlite3.SQLITE_BUSY_SNAPSHOT])
def test_numeric_lock_code_classification_simulated(setup,monkeypatch,code):
    c,app=setup
    def fail(s):raise busy(code)
    monkeypatch.setattr(write_access,'begin',fail)
    assert c.put(URL,headers=H('LeadInvestigator'),json=body()).status_code==503
    assert policy(c)=='ReadWrite' and audits(app)==0
