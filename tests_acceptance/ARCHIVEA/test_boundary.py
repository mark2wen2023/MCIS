"""Independent synthetic archive-export safety acceptance; no real reports."""
import copy,hashlib
import pytest
from pathlib import Path
from sqlalchemy import text
from fastapi.testclient import TestClient
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.reports.models import ReportRow,ReportAuditRow
from mcis_service.interviews.models import InterviewRow
from mcis_service.audit import service as audit
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
CID='SYN-ARCHIVE-A';ROOT='/api/v1/cases/'+CID;HEAD={'X-MCIS-Role':'LeadInvestigator'}
def seed(app):
 with app.state.db.session() as s:put_doc(s,CaseRow,CID,CID,{'caseId':CID,'title':'Synthetic archive','isFictionalDemo':True,'incidentTimeUtc':'2026-01-01T00:00:00Z','caseEpochUtc':'2026-01-01T00:00:00Z'})
@pytest.fixture
def client(tmp_path):
 app=create_app(Settings(data_dir=tmp_path/'data',seed_demo=False));seed(app)
 with TestClient(app) as c:yield c

def state(c):
 with c.app.state.db.session() as s:
  names=s.execute(text("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")).scalars().all()
  db={n:s.execute(text(f'SELECT * FROM "{n}"')).all() for n in names}
 root=c.app.state.settings.data_dir
 files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and not any(str(p).endswith(x) for x in ('.db','.db-wal','.db-shm'))}
 return db,files

def add_report(c):
 r=c.post(ROOT+'/reports',headers=HEAD,json={'templateId':'imo-cic','lang':'zh'});assert r.status_code==201,r.text;return r.json()
def add_interview(c):
 r=c.post(ROOT+'/interviews',headers=HEAD,json={'interviewee':{'intervieweeId':'SYN-P','name':'Synthetic Person','role':'Witness','affiliation':'Synthetic'},'startUtc':'2026-01-01T00:00:00Z'});assert r.status_code==201,r.text;return r.json()
def blocked(c,code='ARCHIVE_RESTORE_UNSUPPORTED',status=409,headers=HEAD):
 before=state(c);r=c.get(ROOT+'/export',headers=headers)
 assert r.status_code==status,r.text
 if code:assert code in r.text
 assert r.headers['cache-control']=='no-store';assert state(c)==before
 assert 'Synthetic Person' not in r.text
 return r

def test_real_report_generation_never_silent_backup(client):
 add_report(client);blocked(client)
def test_real_legacy_transcript_never_unrestorable_backup(client):
 add_interview(client);blocked(client)
@pytest.mark.parametrize('kind',['orphan','gisis'])
def test_snapshot_only_without_report(client,kind):
 with client.app.state.db.session() as s:put_doc(s,ReportAuditRow,CID,'RA-SYN',{'reportId':None if kind=='gisis' else 'RPT-MISSING','sectionId':None,'sentenceId':None,'reason':'Synthetic','beforeValue':{},'afterValue':{},'summary':'Synthetic','auditSeq':999})
 blocked(client)
@pytest.mark.parametrize('kind',['report','interview','snapshotref','unknown'])
def test_residual_audit_only(client,kind):
 with client.app.state.db.session() as s:
  if kind=='unknown':audit.append_raw_line(s,CID,{},'{broken',1,'0'*64)
  else:audit.append(s,case_id=CID,operator='Synthetic',role='LeadInvestigator',action='report.generate' if kind=='report' else ('interview.turn' if kind=='interview' else 'other'),category='Other',command='Synthetic',snapshot_ref='report-snapshot:RA-MISSING' if kind=='snapshotref' else None)
 blocked(client)
@pytest.mark.parametrize('kind',['report','interview','orphan'])
def test_denied_no_archive_disclosure(client,kind):
 if kind=='report':add_report(client)
 elif kind=='interview':add_interview(client)
 else:
  with client.app.state.db.session() as s:put_doc(s,ReportAuditRow,CID,'RA-X',{'reportId':None,'auditSeq':999})
 r=blocked(client,code=None,status=403,headers={})
 assert 'UNSUPPORTED' not in r.text

def test_plain_basic_path_unchanged(client):
 r=client.get(ROOT+'/export',headers=HEAD);assert r.status_code==200 and r.content.startswith(b'PK'),r.text

def test_report_policy_revocation_precedes_unsupported(client):
 add_report(client);p=default_policy();p['matrix']['LeadInvestigator']['evidence_meta']='Deny'
 with client.app.state.db.session() as s:put_doc(s,AccessPolicyRow,CID,'policy',p)
 blocked(client,code=None,status=403)

@pytest.mark.parametrize('change',['missing','changed','denied'])
def test_transcript_source_precedes_archive_refusal(client,change):
 from mcis_service.evidence.models import EvidenceRow
 with client.app.state.db.session() as s:put_doc(s,EvidenceRow,CID,'EV-SYN',{'caseId':CID,'evidenceId':'EV-SYN','title':'Synthetic source','sha256':'a'*64,'confidentiality':'Normal'})
 r=client.post(ROOT+'/interviews',headers=HEAD,json={'interviewee':{'intervieweeId':'SYN-P','name':'Synthetic Person','role':'Witness','affiliation':'Synthetic'},'startUtc':'2026-01-01T00:00:00Z','evidenceId':'EV-SYN'});assert r.status_code==201,r.text
 with client.app.state.db.session() as s:
  if change=='missing':s.query(EvidenceRow).filter_by(case_id=CID).delete()
  elif change=='changed':put_doc(s,EvidenceRow,CID,'EV-SYN',{'caseId':CID,'evidenceId':'EV-SYN','title':'Synthetic source','sha256':'b'*64,'confidentiality':'Normal'})
  else:
   p=default_policy();p['matrix']['LeadInvestigator']['evidence_meta']='Deny';put_doc(s,AccessPolicyRow,CID,'policy',p)
 r=blocked(client,code='INTERVIEW_SOURCE_CHANGED' if change=='changed' else None,status=409 if change=='changed' else 403)
 assert 'ARCHIVE_RESTORE_UNSUPPORTED' not in r.text

def test_orphan_receipt_retains_dedicated_refusal(client):
 from uuid import uuid4
 r=client.post(ROOT+'/manual-interviews',headers=HEAD,json={'requestId':str(uuid4()),'backupAcknowledged':True,'interviewee':{'intervieweeId':'SYN-P','name':'Synthetic Person','role':'Witness','affiliation':'Synthetic'},'startUtc':'2026-01-01T00:00:00Z'});assert r.status_code==201,r.text
 with client.app.state.db.session() as s:s.query(InterviewRow).filter_by(case_id=CID).delete()
 blocked(client,code='INTERVIEW_RECEIPTS_BACKUP_UNSUPPORTED')

def test_no_assembly_or_export_audit_before_refusal(client,monkeypatch):
 from mcis_service.package import mcase
 add_report(client)
 def forbidden(*a,**k):raise AssertionError('must not assemble files or append export audit')
 monkeypatch.setattr(mcase,'build_files',forbidden);monkeypatch.setattr(mcase.audit,'append',forbidden)
 blocked(client)
