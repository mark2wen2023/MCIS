"""Synthetic HTTP/SQLite visibility and real second-connection revocation ordering."""
import json,sqlite3,threading
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import event
from .test_evidence_intake_w42 import local,CASE,counts
from .test_package_export_policy import register,URL,INV,LEAD,RAW
from mcis_service.redaction.policy import default_policy
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.cases.models import CaseRow
from mcis_service.db import put_doc,get_doc
from mcis_service.evidence import recorded_content


def hidden():
    p=default_policy();p['fieldRules'][-1]['appliesTo'].append('Investigator');return p


def test_denial_precedes_read_and_audit(local,monkeypatch):
    c,app=local;item=register(c,confidentiality='Restricted')
    assert c.put(URL+'/access-policy',headers=LEAD,json=hidden()).status_code==200
    def never(*a):raise AssertionError('hidden file read')
    monkeypatch.setattr(recorded_content,'read_content',never)
    before=counts(app)
    r=c.get(URL+'/evidence/'+item['evidenceId']+'/content',headers=INV)
    assert r.status_code==403 and RAW not in r.content and counts(app)==before


def test_same_evidence_id_in_distinct_cases(local):
    c,app=local;other=CASE+'-OTHER'
    with app.state.db.session() as s:
        doc=get_doc(s,CaseRow,CASE,CASE);put_doc(s,CaseRow,other,other,{**doc,'caseId':other})
    a=register(c,confidentiality='Restricted');b=register(c,case=other,confidentiality='Restricted')
    assert a['evidenceId']==b['evidenceId']
    assert c.put(URL+'/access-policy',json=hidden(),headers=LEAD).status_code==200
    assert c.get(URL+'/evidence/'+a['evidenceId']+'/content',headers=INV).status_code==403
    assert c.get('/api/v1/cases/'+other+'/evidence/'+b['evidenceId']+'/content',headers=INV).content==RAW
    assert c.get(URL+'/export',headers=INV).status_code==403
    assert c.get('/api/v1/cases/'+other+'/export',headers=INV).status_code==200


def test_revoke_before_reservation_denies_without_access(local):
    c,app=local;item=register(c,confidentiality='Restricted')
    with app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',default_policy())
    db=sqlite3.connect(app.state.settings.data_dir/'test.db');db.execute('BEGIN IMMEDIATE')
    entered=threading.Event()
    @event.listens_for(app.state.db.engine,'before_cursor_execute')
    def observe(*args):
        if args[2]=='BEGIN IMMEDIATE':entered.set()
    before=counts(app)
    with ThreadPoolExecutor() as pool:
        future=pool.submit(c.get,URL+'/evidence/'+item['evidenceId']+'/content',headers=INV)
        assert entered.wait(3)
        db.execute('UPDATE access_policies SET doc=? WHERE case_id=?',(json.dumps(hidden()),CASE))
        db.commit();db.close()
        r=future.result(timeout=5)
    assert r.status_code==403 and counts(app)==before


def test_read_blocks_revoke_then_next_read_denies(local,monkeypatch):
    c,app=local;item=register(c,confidentiality='Restricted')
    @event.listens_for(app.state.db.engine,'checkout')
    def timeout(conn,*_):conn.execute('PRAGMA busy_timeout=100')
    entered=threading.Event();release=threading.Event();original=recorded_content.read_content
    def slow(path):
        entered.set();assert release.wait(3);return original(path)
    monkeypatch.setattr(recorded_content,'read_content',slow)
    with ThreadPoolExecutor() as pool:
        future=pool.submit(c.get,URL+'/evidence/'+item['evidenceId']+'/content',headers=INV)
        assert entered.wait(3)
        try:
            r=c.put(URL+'/access-policy',json=hidden(),headers=LEAD)
            assert r.status_code==503 and r.json()['detail']['commitState']=='not_committed'
        finally:release.set()
        read=future.result(timeout=5);assert read.status_code==200 and read.content==RAW
    monkeypatch.setattr(recorded_content,'read_content',original)
    assert c.put(URL+'/access-policy',json=hidden(),headers=LEAD).status_code==200
    before=counts(app)
    assert c.get(URL+'/evidence/'+item['evidenceId']+'/content',headers=INV).status_code==403
    assert c.get(URL+'/export',headers=INV).status_code==403 and counts(app)==before
