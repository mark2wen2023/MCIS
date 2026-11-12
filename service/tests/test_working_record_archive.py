"""Synthetic three-store working-record restoration; actual APIs, no core mocks."""
import base64,hashlib,json,uuid,io,zipfile,copy
from contextlib import contextmanager
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,text
from mcis_service.main import create_app
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.interviews.models import InterviewRow
from mcis_service.reports.models import ReportRow,ReportAuditRow
from mcis_service.working_records_archive.models import ArchivedManualReceiptRow,ArchiveImportHistoryRow,ArchiveArtifactRow
from .conftest import make_settings,H
from .test_package_intake_parser import base as base_files
CID='CASE-INTAKE';ROOT='/api/v1/cases/'+CID
HEAD=H('LeadInvestigator','Synthetic Recorder')

@contextmanager
def client_at(path,create=False):
 app=create_app(make_settings(path,seed=False))
 with TestClient(app)as c:
  if create:
   d=json.loads(base_files()['case.json']);d['isFictionalDemo']=True
   with app.state.db.session()as s:put_doc(s,CaseRow,CID,CID,d)
  yield c

def checked(c,method,url,body=None,status=200,headers=HEAD):
 r=getattr(c,method)(url,headers=headers,**({'json':body}if body is not None else{}))
 assert r.status_code==status,r.text
 return r

def populate(c):
 data=b'synthetic original evidence bytes\x00';b={'profile':'mcis-evidence-intake-v1','fileName':'synthetic.bin','contentBase64':base64.b64encode(data).decode(),
 'title':'Synthetic evidence','source':'Synthetic source','extractedBy':'Synthetic','extractedUtc':'2026-01-01T00:00:00Z','category':'Document','confidentiality':'Restricted','note':''}
 preview=checked(c,'post',ROOT+'/evidence-intakes:preview',b).json()
 receipt=checked(c,'post',ROOT+'/evidence-intakes:commit',{**b,'confirmed':True,'requestDigest':preview['requestDigest']},200).json()
 create={'requestId':str(uuid.uuid4()),'backupAcknowledged':True,'interviewee':{'intervieweeId':'SYN','name':'Synthetic','role':'Witness','affiliation':'Synthetic'},'startUtc':'2026-01-01T00:00:00Z','sourceEvidenceId':receipt['evidenceId']}
 r=checked(c,'post',ROOT+'/manual-interviews',create,201).json();rid=r['receipt']['recordId']
 d=checked(c,'get',ROOT+'/manual-interviews/'+rid).json()
 turn={'requestId':str(uuid.uuid4()),'backupAcknowledged':True,'expectedDigest':d['documentDigest'],'question':'  原始问题😀\n','answer':' 原始回答😀 ','sensitiveFragments':['😀']}
 checked(c,'post',ROOT+'/manual-interviews/'+rid+'/turns',turn,201)
 report=checked(c,'post',ROOT+'/reports',{'templateId':'imo-cic','lang':'bilingual'},201).json()
 sid=report['sections'][0]['sectionId']
 checked(c,'patch',ROOT+'/reports/'+report['reportId']+'/sections/'+sid,{'action':'confirm','reason':'Synthetic review'})
 return data,receipt,create,turn,rid,report['reportId']

def exported(c):
 r=checked(c,'get',ROOT+'/export');assert r.headers['cache-control']=='no-store';return r.content

def imported(c,raw):
 b={'contentBase64':base64.b64encode(raw).decode()}
 p=checked(c,'post','/api/v1/packages/intakes:preview',b).json()
 assert p['packageVersion']=='1.2.0'and p['workingRecordsExtension']['version']=='MCIS-WORKING-RECORDS-1'
 return checked(c,'post','/api/v1/packages/intakes:commit',{**b,'confirmed':True,'sourceSha256':hashlib.sha256(raw).hexdigest()}).json()

def document_rows(c):
 with c.app.state.db.session()as s:
  return {m.__tablename__:[(r.key,r.created_utc,r.updated_utc,r.doc)for r in s.scalars(select(m).where(m.case_id==CID).order_by(m.key))]for m in (InterviewRow,ReportRow,ReportAuditRow)}

def test_three_store_roundtrip_and_inactive_receipts(tmp_path):
 with client_at(tmp_path/'a',True)as a:
  data,er,create,turn,rid,rpt=populate(a);before=document_rows(a);raw1=exported(a)
  with client_at(tmp_path/'b')as b:
   imported(b,raw1);assert document_rows(b)==before
   checked(b,'get',ROOT+'/manual-interviews/requests/'+turn['requestId'],status=409)
   checked(b,'post',ROOT+'/manual-interviews',create,status=409)
   checked(b,'get',ROOT+'/evidence-intakes/'+er['requestDigest'],status=409)
   checked(b,'get',ROOT+'/evidence/'+er['evidenceId']+'/content',status=409)
   downloaded=checked(b,'get',ROOT+'/archive-history/evidence/'+er['evidenceId']+'/content')
   assert downloaded.content==data and downloaded.headers['x-sha256']==hashlib.sha256(data).hexdigest()
   p=checked(b,'get',ROOT+'/archive-history/provenance/interview/'+rid).json()['provenance']
   assert p['sourceArchiveSha256']==hashlib.sha256(raw1).hexdigest()and p['changedSinceImport']is False
   raw2=exported(b)
   with client_at(tmp_path/'c')as c:
    imported(c,raw2);assert document_rows(c)==before
    checked(c,'get','/api/v1/packages/intakes/'+hashlib.sha256(raw1).hexdigest(),status=409)
    assert checked(c,'get',ROOT+'/archive-history/evidence/'+er['evidenceId']+'/content').content==data
    raw3=exported(c)
    with zipfile.ZipFile(io.BytesIO(raw3))as z:
     assert z.read('history/artifacts/'+hashlib.sha256(raw1).hexdigest()+'.bin')==raw1
     assert z.read('history/artifacts/'+hashlib.sha256(raw2).hexdigest()+'.bin')==raw2

@pytest.fixture
def origin(tmp_path):
 with client_at(tmp_path/'origin',True)as c:
  details=populate(c);raw=exported(c)
  yield c,details,raw,tmp_path

def mutate(raw,fn):
 from mcis_service.package.mcase import manifest_json
 with zipfile.ZipFile(io.BytesIO(raw))as z:files={n:z.read(n)for n in z.namelist()}
 path='working-records/backup.v1.json';d=json.loads(files[path]);fn(d,files)
 files[path]=json.dumps(d,ensure_ascii=False,separators=(',',':')).encode()
 files['manifest.json']=manifest_json(CID,{k:v for k,v in files.items()if k!='manifest.json'},'2026-01-01T00:00:00Z','1.2.0').encode()
 out=io.BytesIO()
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED)as z:
  for k,v in files.items():z.writestr(k,v)
 return out.getvalue()

def snapshot(c):
 with c.app.state.db.session()as s:
  tables=s.execute(text("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")).scalars().all()
  return {n:s.execute(text('SELECT * FROM "'+n+'"')).all()for n in tables}

@pytest.mark.parametrize('change',[
 lambda d,f:d.update(version=2),
 lambda d,f:d.update(unknown=True),
 lambda d,f:d['interviews'][0]['doc'].update(sourceSha256='0'*64),
 lambda d,f:d['interviews'][0]['doc'].update(evidenceId='EV-OTHER'),
 lambda d,f:d['interviews'].append(copy.deepcopy(d['interviews'][0])),
 lambda d,f:d['interviews'][0].update(createdUtc='not UTC'),
 lambda d,f:d['reports'][0]['doc'].update(parentReportId='RPT-MISSING'),
 lambda d,f:d['reports'][0]['doc'].update(parentReportId=d['reports'][0]['key']),
 lambda d,f:d.update(reports=[]),
 lambda d,f:d.update(reportSnapshots=[]),
 lambda d,f:d['reportSnapshots'][0]['doc'].update(auditSeq=99999),
 lambda d,f:d['reportSnapshots'][0]['doc'].update(reason='forged reason'),
 lambda d,f:d['manualReceipts'][0]['receipt'].update(afterDigest='x'),
 lambda d,f:d['manualReceipts'].append(copy.deepcopy(d['manualReceipts'][0])),
 lambda d,f:d.update(importHistory=[]),
 lambda d,f:d['importHistory'][0]['metadata'].update(requestDigest='0'*64),
 lambda d,f:d['importHistory'][0]['metadata']['binding'].update(operator='Other'),
 lambda d,f:f.update({'unknown-state.json':b'{}'}),
 lambda d,f:f.update({'testimony/IR-01.json':b'{}'}),
 lambda d,f:f.update({'analysis/timeline.json':b'{"events":[{"eventId":"SYN"}]}'}),
 lambda d,f:d['reports'][0]['doc'].update(reportHref='#/report?case=OTHER&report='+d['reports'][0]['key']),
])
def test_mutated_archives_rejected_without_any_restore(origin,change):
 c,details,raw,path=origin;bad=mutate(raw,change)
 with client_at(path/'destination')as dest:
  before=snapshot(dest);b={'contentBase64':base64.b64encode(bad).decode(),'confirmed':True,'sourceSha256':hashlib.sha256(bad).hexdigest()}
  result=dest.post('/api/v1/packages/intakes:commit',headers=HEAD,json=b)
  assert result.status_code in (409,413,422),result.text
  assert result.headers['cache-control']=='no-store'and snapshot(dest)==before
  assert not(dest.app.state.settings.blob_dir/CID).exists()


def test_permissions_and_failure_rollback(origin,monkeypatch):
 from mcis_service.working_records_archive import service as archive
 c,details,raw,path=origin
 with client_at(path/'denied')as dest:
  before=snapshot(dest);b={'contentBase64':base64.b64encode(raw).decode()}
  checked(dest,'post','/api/v1/packages/intakes:preview',b,status=403,headers=H())
  assert snapshot(dest)==before
  original=archive.restore
  def failing(*a,**k):original(*a,**k);raise RuntimeError('SYNTHETIC_POST_FLUSH_FAILURE')
  monkeypatch.setattr(archive,'restore',failing)
  r=checked(dest,'post','/api/v1/packages/intakes:commit',{**b,'confirmed':True,'sourceSha256':hashlib.sha256(raw).hexdigest()},status=500)
  assert 'SYNTHETIC_POST_FLUSH_FAILURE'not in r.text and snapshot(dest)==before
  assert not(dest.app.state.settings.blob_dir/CID).exists()


def test_history_read_provenance_mutation_and_original_protection(origin):
 from mcis_service.redaction.models import AccessPolicyRow
 from mcis_service.redaction.policy import default_policy
 c,details,raw,path=origin;data,er,create,turn,rid,rpt=details
 with client_at(path/'restored')as d:
  imported(d,raw)
  for url in (ROOT+'/archive-history/provenance/interview/'+rid,ROOT+'/archive-history/provenance/report/'+rpt,ROOT+'/archive-history/evidence/'+er['evidenceId']+'/content',ROOT+'/evidence/'+er['evidenceId']+'/content'):
   r=checked(d,'get',url,status=403,headers=H());assert r.headers['cache-control']=='no-store'
  p=checked(d,'get',ROOT+'/archive-history/provenance/report/'+rpt).json()['provenance'];assert not p['changedSinceImport']
  current=checked(d,'get',ROOT+'/manual-interviews/'+rid).json()
  checked(d,'post',ROOT+'/manual-interviews/'+rid+'/turns',{'requestId':str(uuid.uuid4()),'backupAcknowledged':True,'expectedDigest':current['documentDigest'],'question':'new','answer':'new'},201)
  assert checked(d,'get',ROOT+'/archive-history/provenance/interview/'+rid).json()['provenance']['changedSinceImport']is True
  fresh={**create,'requestId':str(uuid.uuid4())};new=checked(d,'post',ROOT+'/manual-interviews',fresh,201).json()['receipt']['recordId']
  assert checked(d,'get',ROOT+'/archive-history/provenance/interview/'+new).json()['provenance']is None
  source=d.app.state.settings.blob_dir/CID/'_package_intake/source.mcase';source.write_bytes(b'corrupt synthetic')
  checked(d,'get',ROOT+'/archive-history/provenance/interview/'+new,status=409)


def test_unknown_case_table_and_orphan_snapshot_prevent_export(origin):
 c,details,raw,path=origin
 with c.app.state.db.session()as s:
  s.execute(text('CREATE TABLE future_case_state(case_id TEXT,payload TEXT)'))
  s.execute(text('INSERT INTO future_case_state VALUES(:cid,:payload)'),{'cid':CID,'payload':'Synthetic'})
 before=snapshot(c);r=c.get(ROOT+'/export',headers=HEAD)
 assert r.status_code in (409,422)and snapshot(c)==before


def test_history_download_failure_does_not_append_access(origin):
 c,details,raw,path=origin;data,er,*_=details
 with client_at(path/'restored')as d:
  imported(d,raw);before=snapshot(d)
  p=d.app.state.settings.blob_dir/CID/('raw/evidence-intakes/'+er['requestDigest']+'/source.bin');p.write_bytes(b'bad')
  checked(d,'get',ROOT+'/archive-history/evidence/'+er['evidenceId']+'/content',status=409)
  assert snapshot(d)==before


def test_legacy_import_cannot_bypass_extension(origin):
 c,details,raw,path=origin
 with client_at(path/'dest')as d:
  before=snapshot(d)
  r=d.post('/api/v1/cases:import',headers=HEAD,content=raw)
  assert r.status_code==422 and r.json()['code']=='WORKING_IMPORT_ENTRY'and snapshot(d)==before


def test_export_final_validation_failure_rolls_back_new_audit(origin,monkeypatch):
 from mcis_service.package_intake import parser
 c,details,raw,path=origin;before=snapshot(c);original=parser.parse_package;calls=0
 def failed(*a,**k):
  nonlocal calls
  calls+=1
  if calls==2:raise RuntimeError('SYNTHETIC_FINAL_EXPORT_FAILURE')
  return original(*a,**k)
 monkeypatch.setattr(parser,'parse_package',failed)
 checked(c,'get',ROOT+'/export',status=500)
 assert calls==2 and snapshot(c)==before


def test_report_versions_full_review_gisis_and_hfacs_coexist(origin):
 from mcis_service.hfacs_drafts.router import run_core
 c,details,raw,path=origin;*_,rpt=details
 report=checked(c,'get',ROOT+'/reports/'+rpt).json()
 section=report['sections'][0];sentence=section['sentences'][0]
 checked(c,'patch',ROOT+'/reports/'+rpt+'/sections/'+section['sectionId'],{'action':'modify','sentenceId':sentence['sentenceId'],'reason':'Synthetic change','textZh':'合成修改','textEn':'Synthetic modified'})
 regenerated=checked(c,'post',ROOT+'/reports/'+rpt+':generate',{'templateId':'imo-cic','lang':'bilingual'},201).json()
 checked(c,'get',ROOT+'/reports/'+rpt+'/export?format=docx')
 checked(c,'post',ROOT+'/gisis:validate',{'values':{},'export':True,'format':'json'},422)
 checked(c,'get',ROOT+'/gisis/export?format=json')
 code=run_core({'action':'taxonomy'})['categories'][0]['code']
 body={'requestId':str(uuid.uuid4()),'expectedDigest':None,'draft':{'scope':'Synthetic','entries':[{'id':'synthetic','categoryCode':code,'description':'Hypothesis','rationale':'Not confirmed'}]},'expectedSources':[]}
 checked(c,'post',ROOT+'/human-factors/hfacs:save',body)
 before=document_rows(c);raw=exported(c)
 with client_at(path/'restore')as d:
  summary=imported(d,raw);assert summary['hfacsExtension']is not None
  assert document_rows(d)==before
  assert checked(d,'get',ROOT+'/reports/'+regenerated['reportId']).json()['parentReportId']==rpt
  raw2=exported(d)
  assert len(raw2)>0


def test_stale_source_policy_and_reserved_ids(origin):
 from sqlalchemy import delete
 from mcis_service.evidence.models import EvidenceRow
 from mcis_service.redaction.models import AccessPolicyRow
 from mcis_service.redaction.policy import default_policy
 c,details,raw,path=origin;data,er,create,turn,rid,rpt=details
 with client_at(path/'restore')as d:
  imported(d,raw)
  with d.app.state.db.session()as s:
   s.execute(delete(InterviewRow).where(InterviewRow.case_id==CID))
   s.execute(delete(EvidenceRow).where(EvidenceRow.case_id==CID))
  # IDs remain unavailable even if current objects disappear.
  create.pop('sourceEvidenceId');create['requestId']=str(uuid.uuid4())
  new=checked(d,'post',ROOT+'/manual-interviews',create,201).json()['receipt']['recordId'];assert new!=rid
  checked(d,'post',ROOT+'/interviews',{'recordId':rid,'interviewee':create['interviewee'],'startUtc':create['startUtc']},409)
  from mcis_service.evidence import service as es
  with d.app.state.db.session()as s:assert es.next_id(s,CID)!=er['evidenceId']
  checked(d,'get',ROOT+'/evidence/'+er['evidenceId']+'/intake',status=409)
  p=default_policy();p['matrix']['LeadInvestigator']['personal']='Deny'
  with d.app.state.db.session()as s:put_doc(s,AccessPolicyRow,CID,'policy',p)
  checked(d,'get',ROOT+'/archive-history/provenance/interview/'+new,status=403)
  checked(d,'get',ROOT+'/evidence/'+er['evidenceId']+'/content',status=403)


def test_concurrent_same_package_commit_and_rollback(origin):
 from concurrent.futures import ThreadPoolExecutor
 c,details,raw,path=origin
 with client_at(path/'restore')as d:
  b={'contentBase64':base64.b64encode(raw).decode(),'confirmed':True,'sourceSha256':hashlib.sha256(raw).hexdigest()}
  with ThreadPoolExecutor(2)as pool:responses=list(pool.map(lambda _:d.post('/api/v1/packages/intakes:commit',headers=HEAD,json=b),range(2)))
  assert [r.status_code for r in responses]==[200,200]
  assert sorted(r.json()['replayed']for r in responses)==[False,True]
  with d.app.state.db.session()as s:
   assert len(s.scalars(select(ArchivedManualReceiptRow)).all())==2


def test_nonempty_sim_commands_and_unknown_blob_refuse(origin):
 c,details,raw,path=origin
 root=c.app.state.settings.blob_dir/CID;bad=root/'not-in-manifest.json';bad.write_bytes(b'{"synthetic":true}')
 before=snapshot(c);r=c.get(ROOT+'/export',headers=HEAD)
 assert r.status_code in (409,422)and snapshot(c)==before
 bad.unlink()
 with c.app.state.db.session()as s:
  s.execute(text("INSERT INTO sim_commands(case_id,seq,doc) VALUES(:cid,1,'{}')"),{'cid':CID})
 before=snapshot(c);r=c.get(ROOT+'/export',headers=HEAD)
 assert r.status_code in (409,422)and snapshot(c)==before


def test_orphan_manual_receipts_are_preserved_without_reusing_ids(tmp_path):
 from sqlalchemy import delete
 with client_at(tmp_path/'source',True)as c:
  b={'requestId':str(uuid.uuid4()),'backupAcknowledged':True,'interviewee':{'intervieweeId':'SYN','name':'Synthetic','role':'Witness','affiliation':'Synthetic'},'startUtc':'2026-01-01T00:00:00Z'}
  r=checked(c,'post',ROOT+'/manual-interviews',b,201).json();rid=r['receipt']['recordId']
  with c.app.state.db.session()as s:s.execute(delete(InterviewRow).where(InterviewRow.case_id==CID))
  raw=exported(c)
  with client_at(tmp_path/'dest')as d:
   imported(d,raw)
   checked(d,'get',ROOT+'/manual-interviews/requests/'+b['requestId'],status=409)
   b['requestId']=str(uuid.uuid4())
   assert checked(d,'post',ROOT+'/manual-interviews',b,201).json()['receipt']['recordId']!=rid
   with d.app.state.db.session()as s:
    saved=s.scalars(select(ArchivedManualReceiptRow)).one().doc
    assert saved['receipt']==r['receipt']


def test_legacy_hash_preserved_but_append_stays_blocked(tmp_path):
 with client_at(tmp_path/'source',True)as c:
  b={'requestId':str(uuid.uuid4()),'backupAcknowledged':True,'interviewee':{'intervieweeId':'SYN','name':'Synthetic','role':'Witness','affiliation':'Synthetic'},'startUtc':'2026-01-01T00:00:00Z'}
  rid=checked(c,'post',ROOT+'/manual-interviews',b,201).json()['receipt']['recordId']
  with c.app.state.db.session()as s:
   row=s.scalars(select(InterviewRow)).one();row.doc={**row.doc,'sourceSha256':'a'*64}
  before=document_rows(c);raw=exported(c)
  with client_at(tmp_path/'dest')as d:
   imported(d,raw);assert document_rows(d)==before
   current=checked(d,'get',ROOT+'/manual-interviews/'+rid).json();assert current['sourceBinding']=='legacy-unverified'
   checked(d,'post',ROOT+'/manual-interviews/'+rid+'/turns',{'requestId':str(uuid.uuid4()),'backupAcknowledged':True,'expectedDigest':current['documentDigest'],'question':'new','answer':'new'},409)

@pytest.mark.parametrize('status',[403,413,503,422])
def test_working_hfacs_specific_failure_preserves_status_and_audit(origin,monkeypatch,status):
 from mcis_service.hfacs_drafts import archive
 from mcis_service.hfacs_drafts.router import PreviewError
 c,details,raw,path=origin;before=snapshot(c)
 def unavailable(*a,**k):raise PreviewError(status,'SYNTHETIC_HFACS_FAILURE','Synthetic blocked')
 monkeypatch.setattr(archive,'build',unavailable)
 r=checked(c,'get',ROOT+'/export',status=409 if status==422 else status)
 assert r.json()['code']==('ARCHIVE_RESTORE_UNSUPPORTED'if status==422 else'SYNTHETIC_HFACS_FAILURE')
 assert snapshot(c)==before


@pytest.mark.parametrize("version,leftover",[("1.0.0",False),("1.1.0",False),("1.2.0",False),("1.0.0",True)])
def test_old_package_custody_credentials_cannot_reactivate(origin,version,leftover):
 from mcis_service.package.mcase import manifest_json
 c,details,raw,path=origin
 with zipfile.ZipFile(io.BytesIO(raw))as z:files={n:z.read(n)for n in z.namelist()if n not in ('working-records/backup.v1.json','manifest.json')}
 if leftover:files['working-records/unknown.json']=b'{}'
 files['manifest.json']=manifest_json(CID,files,'2026-01-01T00:00:00Z',version).encode()
 out=io.BytesIO()
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED)as z:
  for k,v in files.items():z.writestr(k,v)
 legacy=out.getvalue()
 with client_at(path/'dest')as d:
  before=snapshot(d)
  assert d.post('/api/v1/cases:import',content=legacy,headers=HEAD).status_code==422
  assert d.post('/api/v1/packages/intakes:preview',headers=HEAD,json={'contentBase64':base64.b64encode(legacy).decode()}).status_code==422
  assert snapshot(d)==before
