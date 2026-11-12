"""Independent synthetic content-boundary tests with real report generation/export."""
import copy,json,threading,io,zipfile
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text,select
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy,CATEGORIES
from mcis_service.reports import service,exporter
from mcis_service.reports.models import ReportRow,ReportAuditRow
from mcis_service.audit import service as audit
C='/api/v1/cases/SYN-162';H={'X-MCIS-Role':'LeadInvestigator'};SECRET='SYNTHETIC-ONLY-SENTINEL-162'
@pytest.fixture
def client(tmp_path):
 app=create_app(Settings(data_dir=tmp_path/'data',seed_demo=False))
 with app.state.db.session() as s:put_doc(s,CaseRow,'SYN-162','SYN-162',{'caseId':'SYN-162','title':'Synthetic','isFictionalDemo':True})
 with TestClient(app) as c:yield c

def policy(c,p):
 with c.app.state.db.session() as s:put_doc(s,AccessPolicyRow,'SYN-162','policy',p)
def snapshot(c):
 with c.app.state.db.session() as s:
  names=s.execute(text("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")).scalars().all()
  return {n:s.execute(text(f'SELECT * FROM "{n}"')).all() for n in names}
def create(c):
 out=c.post(C+'/reports',headers=H,json={'templateId':'imo-cic','lang':'bilingual'});assert out.status_code==201,out.text
 d=out.json();rid=d['reportId'];sid=d['sections'][0]['sectionId']
 out=c.patch(C+f'/reports/{rid}/sections/{sid}',headers=H,json={'action':'modify','reason':SECRET,'textZh':SECRET});assert out.status_code==200,out.text
 return rid,sid

def deny(r):
 assert r.status_code==403,r.text;assert SECRET not in r.text
 assert r.headers['cache-control']=='no-store'
@pytest.mark.parametrize('category',CATEGORIES)
@pytest.mark.parametrize('level',['Deny','Redacted',None])
def test_all_categories_gate_read_and_create_without_writes(client,category,level):
 p=default_policy()
 if level is None:del p['matrix']['LeadInvestigator'][category]
 else:p['matrix']['LeadInvestigator'][category]=level
 policy(client,p);before=snapshot(client)
 deny(client.get(C+'/reports',headers=H));deny(client.post(C+'/reports',headers=H,json={}))
 assert snapshot(client)==before

def test_all_paths_default_investigator_denial_and_no_side_effects(client):
 rid,sid=create(client);history=client.get(C+f'/reports/{rid}/audit',headers=H).json();snap=history[-1]['snapshotRef'].split(':')[1]
 paths=['/reports',f'/reports/{rid}',f'/reports/{rid}/audit',f'/report-snapshots/{snap}',f'/reports/{rid}/export?format=pdf',f'/reports/{rid}/export?format=docx','/gisis','/gisis/export?format=csv','/audit','/audit?order=desc&limit=1','/export']
 before=snapshot(client)
 for path in paths:deny(client.get(C+path))
 deny(client.get('/api/v1/report-templates?caseId=SYN-162'))
 for path in ['/reports','/reports/sections/colreg:draft',f'/reports/{rid}:generate','/gisis:validate']:deny(client.post(C+path,json={}))
 deny(client.patch(C+f'/reports/{rid}/sections/{sid}',json={'action':'confirm'}))
 assert snapshot(client)==before

def test_real_pdf_docx_and_audit_for_qualifying_lead(client):
 rid,_=create(client)
 for fmt in ['pdf','docx']:
  out=client.get(C+f'/reports/{rid}/export?format={fmt}',headers=H);assert out.status_code==200,out.text
  assert out.headers['cache-control']=='no-store'
  if fmt=='pdf':assert out.content.startswith(b'%PDF-')
  else:
   with zipfile.ZipFile(io.BytesIO(out.content)) as z:assert SECRET in z.read('word/document.xml').decode()
 assert SECRET in client.get(C+f'/reports/{rid}/audit',headers=H).text

@pytest.mark.parametrize('bad',['rule','unknown-method','null','unknown-level','missing-row'])
def test_field_rules_malformed_policy_no_fallback(client,bad):
 p=default_policy()
 if bad=='rule':p['fieldRules'][0]['appliesTo']=['LeadInvestigator']
 elif bad=='unknown-method':p['fieldRules'][0]['method']='future'
 elif bad=='null':p=None
 elif bad=='unknown-level':p['matrix']['LeadInvestigator']['audit']='future'
 else:del p['matrix']['LeadInvestigator']
 policy(client,p);deny(client.get(C+'/reports',headers=H))

def test_gate_before_case_load_and_internal_error_no_store(client,monkeypatch):
 def explode(*a,**k):raise RuntimeError(SECRET)
 monkeypatch.setattr(service,'case_info',explode)
 deny(client.get('/api/v1/cases/MISSING/reports'))
 out=client.get(C+'/reports',headers=H);assert out.status_code==500 and SECRET not in out.text and out.headers['cache-control']=='no-store'

def test_read_only_allows_read_not_write(client):
 rid,_=create(client);p=default_policy();p['matrix']['LeadInvestigator']['report_draft']='ReadOnly';policy(client,p)
 assert client.get(C+f'/reports/{rid}',headers=H).status_code==200
 before=snapshot(client);deny(client.post(C+f'/reports/{rid}:generate',headers=H,json={}));assert snapshot(client)==before

@pytest.mark.parametrize('kind',['snapshot-only','raw-line-only'])
def test_package_and_audit_legacy_history_no_report_row(client,kind):
 with client.app.state.db.session() as s:
  if kind=='snapshot-only':put_doc(s,ReportAuditRow,'SYN-162','RA-only',{'reason':SECRET})
  else:audit.append(s,case_id='SYN-162',operator='Synthetic',role='LeadInvestigator',action='report.old',category='Other',command='legacy',reason=SECRET,entity_type='other',entity_id='old')
 before=snapshot(client);deny(client.get(C+'/export'));assert snapshot(client)==before
 if kind=='raw-line-only':deny(client.get(C+'/audit'))

def test_recommendation_history_cannot_read_report_reason(client):
 rid,_=create(client);out=client.get(C+f'/recommendations/{rid}/history')
 assert out.status_code in (403,404) and SECRET not in out.text

def test_render_serializes_policy_update_and_later_denial(client,monkeypatch):
 rid,_=create(client);ready=threading.Event();release=threading.Event();written=threading.Event();original=exporter.export_report
 def render(*args,**kwargs):
  ready.set();assert release.wait(15);return original(*args,**kwargs)
 monkeypatch.setattr(exporter,'export_report',render)
 def revoke():
  p=default_policy();p['matrix']['LeadInvestigator']['evidence_meta']='Deny';policy(client,p);written.set()
 with ThreadPoolExecutor(2) as pool:
  download=pool.submit(client.get,C+f'/reports/{rid}/export?format=docx',headers=H);assert ready.wait(10)
  update=pool.submit(revoke);assert not written.wait(.2);release.set()
  assert download.result().status_code==200;update.result()
 deny(client.get(C+f'/reports/{rid}',headers=H))
