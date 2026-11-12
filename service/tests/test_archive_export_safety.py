"""Synthetic-only refusal of known incomplete backups; no import changes."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from mcis_service.main import create_app
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.interviews.models import InterviewRow
from mcis_service.reports.models import ReportRow,ReportAuditRow
from mcis_service.audit import service as audit
from mcis_service.package import mcase
from .conftest import make_settings,H
CID='SYN-ARCHIVE'
URL='/api/v1/cases/'+CID+'/export'
@pytest.fixture
def client(tmp_path):
 app=create_app(make_settings(tmp_path,seed=False))
 with app.state.db.session() as s:put_doc(s,CaseRow,CID,CID,{'caseId':CID,'title':'Synthetic','isFictionalDemo':True,'incidentTimeUtc':'2026-01-01T00:00:00Z','caseEpochUtc':'2026-01-01T00:00:00Z'})
 with TestClient(app) as c:yield c

def snapshot(c):
 with c.app.state.db.session() as s:
  names=s.execute(text("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")).scalars().all()
  return {n:s.execute(text(f'SELECT * FROM "{n}"')).all() for n in names}

@pytest.mark.parametrize('kind',['report','snapshot','gisis','interview','report-event','interview-event','snapshot-ref','unknown-line'])
@pytest.mark.parametrize('role',['LeadInvestigator','Investigator'])
def test_known_incomplete_refused_after_authorization_without_side_effects(client,monkeypatch,kind,role):
 with client.app.state.db.session() as s:
  if kind=='report':put_doc(s,ReportRow,CID,'RPT-SYN',{'reportId':'RPT-SYN','caseId':CID,'synthetic':'retained'})
  elif kind in ('snapshot','gisis'):put_doc(s,ReportAuditRow,CID,'RA-SYN',{'reportId':None if kind=='gisis' else 'RPT-MISSING','synthetic':'retained'})
  elif kind=='interview':put_doc(s,InterviewRow,CID,'IR-01',{'recordId':'IR-01','caseId':CID,'signed':False,'sourceSha256':''})
  elif kind=='unknown-line':
   audit.append_raw_line(s,CID,{'category':'Test','action':'history'},'{"category":"Test","category":"Report"}',1,'0'*64)
  else:
   audit.append(s,case_id=CID,operator='Synthetic',role='LeadInvestigator',action='history',category='Report' if kind=='report-event' else 'Interview' if kind=='interview-event' else 'Test',command='Synthetic',snapshot_ref='report-snapshot:RA-MISSING' if kind=='snapshot-ref' else None)
 before=snapshot(client)
 files_before=sorted(str(p) for p in client.app.state.settings.blob_dir.rglob('*'))
 def forbidden(*a,**k):raise AssertionError('must refuse before building files')
 monkeypatch.setattr(mcase,'build_files',forbidden)
 r=client.get(URL,headers=H(role))
 assert r.status_code==(409 if role=='LeadInvestigator' else 403),r.text
 assert r.json()['code']==('ARCHIVE_RESTORE_UNSUPPORTED' if role=='LeadInvestigator' else 'FORBIDDEN')
 assert r.headers['cache-control']=='no-store'
 assert snapshot(client)==before
 assert sorted(str(p) for p in client.app.state.settings.blob_dir.rglob('*'))==files_before
