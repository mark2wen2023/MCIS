"""Actual API/SQLite tests; only synthetic cases/files and explicit failure hooks."""
import base64,io,json,sqlite3,threading,zipfile
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import event
from .test_evidence_intake_w42 import local,CASE
from .conftest import H
from mcis_service.db import put_doc,get_doc
from mcis_service.cases.models import CaseRow
from mcis_service.evidence.models import EvidenceRow
from mcis_service.audit.models import AuditEventRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.evidence import recorded_content
from mcis_service.package import mcase
URL=f'/api/v1/cases/{CASE}';LEAD=H('LeadInvestigator');INV=H();RAW=b'synthetic original case material'

def register(c,case=CASE,confidentiality='Normal',category='Other'):
    r=c.post(f'/api/v1/cases/{case}/evidence',headers=LEAD,json={'title':'synthetic','source':'synthetic','extractedBy':'synthetic','extractedUtc':'2026-01-01T00:00:00Z','relativePath':'evidence/EV-001/source.bin','contentBase64':base64.b64encode(RAW).decode(),'confidentiality':confidentiality,'category':category})
    assert r.status_code==201,r.text
    return r.json()
def counts(app):
    with app.state.db.session() as s:return s.query(AuditEventRow).count()
def policy(c,category,level='Deny',case=CASE):
    p=default_policy();p['matrix']['Investigator'][category]=level
    r=c.put(f'/api/v1/cases/{case}/access-policy',headers=LEAD,json=p);assert r.status_code==200,r.text
    return p

def test_plain_allowed_bytes_audit_and_chain(local):
    c,app=local;register(c);before=counts(app)
    r=c.get(URL+'/export',headers=INV);assert r.status_code==200,r.text
    files=mcase.read_zip(r.content)
    assert files['evidence/EV-001/source.bin']==RAW and mcase.verify_files(files)['isValid']
    assert counts(app)==before+1
    assert json.loads(files['audit/audit.jsonl'].splitlines()[-1])['action']=='package.export'

@pytest.mark.parametrize('category',['ais_sim','evidence_meta','audit','timeline','recommendations','agent_drafts'])
@pytest.mark.parametrize('level',['Deny','Redacted'])
def test_each_raw_category_denies_before_read_and_no_audit(local,monkeypatch,category,level):
    c,app=local;register(c);policy(c,category,level);before=counts(app)
    def no_read(*a):raise AssertionError('denied export reached blob read')
    monkeypatch.setattr(recorded_content,'read_content',no_read)
    r=c.get(URL+'/export',headers=INV)
    assert r.status_code==403 and r.json()['code']=='PACKAGE_CONTENT_FORBIDDEN'
    assert counts(app)==before and RAW not in r.content

@pytest.mark.parametrize('category',['evidence_meta','audit'])
def test_empty_case_no_audit_rows_still_denies(local,category):
    c,app=local;p=default_policy();p['matrix']['Investigator'][category]='Deny'
    with app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',p)
    assert counts(app)==0
    assert c.get(URL+'/export',headers=INV).status_code==403
    assert counts(app)==0

@pytest.mark.parametrize('mode',['restricted','vdr','field_rule'])
def test_per_evidence_gate(local,mode):
    c,app=local
    register(c,confidentiality='Restricted' if mode!='vdr' else 'Normal',category='VDR' if mode=='vdr' else 'Other')
    if mode=='restricted':policy(c,'testimony')
    elif mode=='vdr':policy(c,'vdr_audio','Redacted')
    else:
        p=default_policy();p['fieldRules'][-1]['appliesTo'].append('Investigator')
        assert c.put(URL+'/access-policy',headers=LEAD,json=p).status_code==200
    before=counts(app);r=c.get(URL+'/export',headers=INV)
    assert r.status_code==403 and counts(app)==before


def test_cross_case_policy_and_members(local):
    c,app=local;register(c);other=CASE+'-B'
    with app.state.db.session() as s:
        doc=get_doc(s,CaseRow,CASE,CASE);put_doc(s,CaseRow,other,other,{**doc,'caseId':other})
    register(c,other);policy(c,'evidence_meta',case=other)
    assert c.get(URL+'/export',headers=INV).status_code==200
    before=counts(app)
    assert c.get(f'/api/v1/cases/{other}/export',headers=INV).status_code==403
    assert counts(app)==before
    allowed=c.get(f'/api/v1/cases/{other}/export',headers=LEAD)
    assert allowed.status_code==200
    files=mcase.read_zip(allowed.content)
    assert json.loads(files['case.json'])['caseId']==other
    assert all(x['caseId']==other for x in json.loads(files['evidence/index.json']))


def test_embedded_foreign_case_binding_cannot_redirect(local):
    c,app=local;item=register(c)
    with app.state.db.session() as s:put_doc(s,EvidenceRow,CASE,item['evidenceId'],{**item,'caseId':'DIFFERENT-CASE'})
    before=counts(app);r=c.get(URL+'/export',headers=LEAD)
    assert r.status_code==409 and r.json()['code']=='PACKAGE_CASE_BINDING' and counts(app)==before

@pytest.mark.parametrize('mode',['unknown_member','serialization_fault'])
def test_late_failure_rolls_back_export_audit(local,monkeypatch,mode):
    c,app=local;register(c);original=mcase.build_files;before=counts(app)
    def build(*a):
        files=original(*a)
        if mode=='serialization_fault':raise ValueError('synthetic serialization failure')
        return {**files,'unclassified.bin':b'synthetic hidden material'}
    monkeypatch.setattr(mcase,'build_files',build)
    # NoStoreRoute converts injected error without echoing details.
    r=c.get(URL+'/export',headers=LEAD)
    assert r.status_code==(409 if mode=='unknown_member' else 500)
    assert counts(app)==before and b'synthetic hidden' not in r.content


def test_revoke_commits_before_export_reservation(local):
    c,app=local;register(c);p=default_policy();p['matrix']['Investigator']['audit']='Deny'
    with app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',default_policy())
    db=sqlite3.connect(app.state.settings.data_dir/'test.db');db.execute('BEGIN IMMEDIATE')
    entered=threading.Event()
    @event.listens_for(app.state.db.engine,'before_cursor_execute')
    def begin(*args):
        if args[2]=='BEGIN IMMEDIATE':entered.set()
    before=counts(app)
    with ThreadPoolExecutor() as pool:
        pending=pool.submit(c.get,URL+'/export',headers=INV);assert entered.wait(3)
        db.execute('UPDATE access_policies SET doc=? WHERE case_id=?',(json.dumps(p),CASE));db.commit();db.close()
        r=pending.result(timeout=5)
    assert r.status_code==403 and counts(app)==before


def test_export_reservation_blocks_concurrent_revoke_then_next_denies(local,monkeypatch):
    c,app=local;register(c)
    @event.listens_for(app.state.db.engine,'checkout')
    def timeout(conn,*_):conn.execute('PRAGMA busy_timeout=100')
    reached=threading.Event();release=threading.Event();original=recorded_content.read_content
    def slow(path):
        reached.set();assert release.wait(3);return original(path)
    monkeypatch.setattr(recorded_content,'read_content',slow)
    p=default_policy();p['matrix']['Investigator']['evidence_meta']='Deny'
    with ThreadPoolExecutor() as pool:
        pending=pool.submit(c.get,URL+'/export',headers=INV);assert reached.wait(3)
        try:
            denied=c.put(URL+'/access-policy',headers=LEAD,json=p)
            assert denied.status_code==503 and denied.json()['detail']['commitState']=='not_committed'
        finally:release.set()
        assert pending.result(timeout=5).status_code==200
    monkeypatch.setattr(recorded_content,'read_content',original)
    assert c.put(URL+'/access-policy',headers=LEAD,json=p).status_code==200
    before=counts(app);assert c.get(URL+'/export',headers=INV).status_code==403
    assert counts(app)==before

@pytest.mark.parametrize('bad',[{}, {'version':'1','matrix':{'Investigator':{'audit':'Anything'}},'categories':[],'fieldRules':[]}])
def test_malformed_stored_policy_is_not_defaulted(local,bad):
    c,app=local;register(c)
    with app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',bad)
    before=counts(app);r=c.get(URL+'/export',headers=INV)
    assert r.status_code==403 and counts(app)==before


def test_present_colreg_member_requires_full_category(local):
    from mcis_service.colreg.models import ColregAnalysisRow
    c,app=local;register(c)
    with app.state.db.session() as s:put_doc(s,ColregAnalysisRow,CASE,'current',{'caseId':CASE,'synthetic':'not a real COLREG finding'})
    policy(c,'colreg','Redacted');before=counts(app)
    assert c.get(URL+'/export',headers=INV).status_code==403
    assert counts(app)==before
