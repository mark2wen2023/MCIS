"""Prepared adversarial synthetic tests; final execution awaits freeze."""
import copy
import pytest
from sqlalchemy import event
from helpers import *
from mcis_service.redaction.policy import CATEGORIES

@pytest.fixture
def source_package(tmp_path):
 with client(tmp_path/'source') as c:
  seed(c);fixture=populate(c);return export(c),fixture

def altered(raw,change):
 files=unzip(raw);doc=json.loads(files[MEMBER]);change(doc);files[MEMBER]=json.dumps(doc,ensure_ascii=False,separators=(',',':')).encode()
 manifest=json.loads(files['manifest.json'])
 for item in manifest['files']:
  data=files[item['relativePath']];item.update(sizeBytes=len(data),sha256=sha(data))
 files['manifest.json']=json.dumps(manifest).encode();buf=io.BytesIO()
 with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
  for path,data in files.items():z.writestr(path,data)
 return buf.getvalue()

@pytest.mark.parametrize('mutation',['case','duplicate-record','duplicate-version','parent-cycle','snapshot-seq','receipt-identity','unknown-field','wrong-source','lineage-dangling'])
def test_rehashed_semantic_corruption_refused_without_changes(source_package,tmp_path,mutation):
 raw,_=source_package
 def change(d):
  if mutation=='case':d['caseId']='OTHER'
  elif mutation=='duplicate-record':d['interviews'].append(copy.deepcopy(d['interviews'][0]))
  elif mutation=='duplicate-version':d['reports'][1]['doc']['version']=d['reports'][0]['doc']['version']
  elif mutation=='parent-cycle':d['reports'][0]['doc']['parentReportId']=d['reports'][0]['doc']['reportId']
  elif mutation=='snapshot-seq':d['reportSnapshots'][0]['doc']['auditSeq']=999999
  elif mutation=='receipt-identity':d['manualReceipts'][0]['receipt']['recordId']='IR-999'
  elif mutation=='unknown-field':d['undeclared']=True
  elif mutation=='wrong-source':d['interviews'][0]['doc']['sourceSha256']='f'*64
  else:d['lineage']['nodes']=[{'artifactSha256':'a'*64,'parentArtifactSha256s':[]}]
 corrupt=altered(raw,change)
 with client(tmp_path/'destination') as target:
  before=state(target)
  for commit in (False,True):
   r=intake(target,corrupt,commit);assert r.status_code==422,r.text;assert state(target)==before

@pytest.mark.parametrize('category',CATEGORIES)
def test_export_current_permission_before_history_details(source_package,tmp_path,category):
 from mcis_service.redaction.models import AccessPolicyRow
 from mcis_service.redaction.policy import default_policy
 raw,_=source_package
 with client(tmp_path/'destination') as c:
  r=intake(c,raw,True);assert r.status_code==200,r.text
  p=default_policy();p['matrix']['LeadInvestigator'][category]='Deny'
  with c.app.state.db.session() as s:put_doc(s,AccessPolicyRow,CID,'policy',p)
  before=state(c);r=c.get(BASE+'/export',headers=H);assert r.status_code==403 and 'reportCount' not in r.text
  assert state(c)==before

@pytest.mark.parametrize('table',['investigation_reports','report_operation_snapshots','archived_manual_interview_receipts','archive_import_history'])
def test_import_table_insert_fault_full_rollback_and_retry(source_package,tmp_path,table):
 from mcis_service.db import Base
 raw,_=source_package
 with client(tmp_path/'destination') as c:
  before=state(c)
  def fail(conn,cursor,statement,params,context,many):
   if statement.lower().startswith('insert into '+table):raise RuntimeError('Synthetic rollback test')
  event.listen(c.app.state.db.engine,'before_cursor_execute',fail)
  try:
   with TestClient(c.app,raise_server_exceptions=False) as raw_client:r=intake(raw_client,raw,True)
   assert r.status_code==500 and 'Synthetic rollback' not in r.text
  finally:event.remove(c.app.state.db.engine,'before_cursor_execute',fail)
  assert state(c)==before
  r=intake(c,raw,True);assert r.status_code==200,r.text

@pytest.mark.parametrize('phase',['publish','commit'])
def test_import_filesystem_publish_and_final_commit_rollback(source_package,tmp_path,monkeypatch,phase):
 from sqlalchemy.orm import Session
 raw,_=source_package
 with client(tmp_path/'destination') as c:
  before=state(c)
  def fail(*a,**k):raise RuntimeError('Synthetic final transaction failure')
  with monkeypatch.context() as patch:
   patch.setattr(Path,'rename',fail) if phase=='publish' else patch.setattr(Session,'commit',fail)
   with TestClient(c.app,raise_server_exceptions=False) as raw_client:r=intake(raw_client,raw,True)
   assert r.status_code==500 and 'Synthetic final transaction failure' not in r.text
  assert state(c)==before
  r=intake(c,raw,True);assert r.status_code==200,r.text

def test_unknown_case_table_never_silently_omitted(source_package,tmp_path):
 raw,_=source_package
 with client(tmp_path/'destination') as c:
  assert intake(c,raw,True).status_code==200
  with c.app.state.db.session() as s:
   s.execute(text('CREATE TABLE synthetic_uncontracted_state(case_id TEXT, data TEXT)'))
   s.execute(text('INSERT INTO synthetic_uncontracted_state VALUES (:cid,:data)'),{'cid':CID,'data':'Synthetic only'})
  before=state(c);r=c.get(BASE+'/export',headers=H);assert r.status_code==409 and r.json()['code']=='ARCHIVE_RESTORE_UNSUPPORTED',r.text;assert state(c)==before

def test_orphan_archived_identifiers_reserved_by_old_and_new_allocators(source_package,tmp_path):
 from mcis_service.interviews.models import InterviewRow
 from mcis_service.evidence.models import EvidenceRow
 raw,f=source_package
 with client(tmp_path/'destination') as c:
  assert intake(c,raw,True).status_code==200
  with c.app.state.db.session() as s:
   s.query(InterviewRow).filter_by(case_id=CID,key=f['recordId']).delete()
   s.query(EvidenceRow).filter_by(case_id=CID,key=f['evidenceId']).delete()
  old_body={'interviewee':f['manualBody']['interviewee'],'startUtc':'2026-01-01T00:00:00Z'}
  r=c.post(BASE+'/interviews',headers=H,json={**old_body,'recordId':f['recordId']});assert r.status_code==409,r.text
  r=c.post(BASE+'/interviews',headers=H,json=old_body);assert r.status_code==201 and r.json()['recordId']!=f['recordId'],r.text
  fresh={**f['manualBody'],'requestId':str(uuid.uuid4())};fresh.pop('sourceEvidenceId')
  r=c.post(BASE+'/manual-interviews',headers=H,json=fresh);assert r.status_code==201 and r.json()['receipt']['recordId']!=f['recordId'],r.text
  r=c.post(BASE+'/evidence',headers=H,json={'title':'Synthetic replacement','source':'Synthetic','extractedBy':'Synthetic','extractedUtc':'2026-01-01T00:00:00Z','contentBase64':base64.b64encode(b'Synthetic other bytes').decode(),'confidentiality':'Restricted'});assert r.status_code==201 and r.json()['evidenceId']!=f['evidenceId'],r.text
  newev=dict(f['evidenceBody']);newev.pop('requestDigest');newev.pop('confirmed');newev['title']='Synthetic different request'
  pre=c.post(BASE+'/evidence-intakes:preview',headers=H,json=newev);assert pre.status_code==200,pre.text
  r=c.post(BASE+'/evidence-intakes:commit',headers=H,json={**newev,'confirmed':True,'requestDigest':pre.json()['requestDigest']});assert r.status_code in (200,201) and r.json()['evidenceId']!=f['evidenceId'],r.text

def test_signed_restoration_preserves_flag_and_rejects_old_and_new_append(tmp_path):
 from mcis_service.interviews.models import InterviewRow
 with client(tmp_path/'A') as c:
  seed(c);f=populate(c)
  with c.app.state.db.session() as s:
   row=s.query(InterviewRow).filter_by(case_id=CID,key=f['recordId']).one();d=dict(row.doc);d['signed']=True;put_doc(s,InterviewRow,CID,f['recordId'],d)
  raw=export(c)
 with client(tmp_path/'B') as c:
  assert intake(c,raw,True).status_code==200
  current=c.get(BASE+'/manual-interviews/'+f['recordId'],headers=H).json();assert current['record']['signed'] is True
  before=state(c)
  r=c.post(BASE+'/interviews/'+f['recordId']+'/turns',headers=H,json={'question':'Synthetic','answer':'Synthetic'});assert r.status_code==409 and r.json()['code']=='INTERVIEW_SIGNED',r.text
  r=c.post(BASE+'/manual-interviews/'+f['recordId']+'/turns',headers=H,json={'requestId':str(uuid.uuid4()),'backupAcknowledged':True,'expectedDigest':current['documentDigest'],'question':'Synthetic','answer':'Synthetic'});assert r.status_code==409 and r.json()['code']=='INTERVIEW_SIGNED',r.text
  assert state(c)==before
