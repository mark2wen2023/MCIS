"""Only synthetic HTTP-created case/report; renderer is real except explicit fault/race tests."""
import hashlib,io,json,struct,zipfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.audit.models import AuditEventRow
from mcis_service.reports.models import ReportRow,ReportAuditRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.report_output import router as module
CID='OUTPUT-SYNTHETIC';BASE='/api/v1/cases/'+CID
H={'X-MCIS-Role':'LeadInvestigator','X-MCIS-Operator':'Synthetic Export'}
@pytest.fixture
def origin(tmp_path):
 app=create_app(Settings(data_dir=tmp_path,db_url=f'sqlite:///{tmp_path}/mcis.db',seed_demo=False))
 with TestClient(app)as c:
  r=c.post('/api/v1/cases',headers=H,json={'caseId':CID,'schemaVersion':'1.0.0','title':'Synthetic','accidentType':'Collision','isFictionalDemo':True,'caseEpochUtc':'2026-01-01T00:00:00Z','incidentTimeUtc':'2026-01-01T00:00:00Z','incidentLocation':{'lonDeg':121,'latDeg':31},'displayTimeZoneOffsetMinutes':0});assert r.status_code==201,r.text
  r=c.post(BASE+'/reports',headers=H,json={'templateId':'imo-cic','lang':'bilingual'});assert r.status_code==201,r.text
  report=r.json();path=BASE+'/reports/'+report['reportId']+'/output-bundle'
  yield c,report,path

def preview(c,path):
 r=c.get(path+':preview',headers=H);assert r.status_code==200,r.text;return r.json()
def body(c,path,fmt='docx'):
 return {'format':fmt,'lang':'zh','expectedReportDigest':preview(c,path)['reportDocumentSha256']}
def counts(c):
 with c.app.state.db.session()as s:
  return tuple(len(s.scalars(select(m)).all())for m in(AuditEventRow,ReportAuditRow))
def post(c,path,args,status=200):
 r=c.post(path,headers=H,json=args);assert r.status_code==status,r.text[:200];assert r.headers['cache-control']=='no-store';return r

@pytest.mark.parametrize('fmt',['pdf','docx'])
def test_real_single_render_bundle_and_legacy_archive(origin,fmt,monkeypatch,tmp_path):
 c,report,path=origin;args=body(c,path,fmt);before=counts(c);calls=[];original=module.render
 def tracked(doc,**kw):calls.append(1);return original(doc,**kw)
 monkeypatch.setattr(module,'render',tracked)
 r=post(c,path,args);assert len(calls)==1;assert counts(c)==tuple(x+1 for x in before)
 assert hashlib.sha256(r.content).hexdigest()==r.headers['x-sha256']
 with zipfile.ZipFile(io.BytesIO(r.content))as z:
  names=['report.'+fmt,'report.json','audit.json','manifest.json'];assert z.namelist()==names
  offset=0
  for i in z.infolist():
   assert i.header_offset==offset
   assert(i.create_system,i.create_version,i.extract_version,i.flag_bits,i.compress_type,i.internal_attr,i.external_attr)==(0,20,20,0,0,0,0x20)
   assert i.date_time==(1980,1,1,0,0,0)and i.extra==b''and i.comment==b''
   offset+=30+len(i.filename)+i.file_size
  assert r.content[offset:offset+4]==b'PK\x01\x02'
  assert r.content[-22:-18]==b'PK\x05\x06'
  document=z.read(names[0]);data=z.read('report.json');audit=json.loads(z.read('audit.json'));manifest=json.loads(z.read('manifest.json'))
  assert json.loads(data)==report and hashlib.sha256(data).hexdigest()==args['expectedReportDigest']
  for member in manifest['members']:
   raw=z.read(member['name']);assert len(raw)==member['byteLength'];assert hashlib.sha256(raw).hexdigest()==member['sha256']
  line=json.loads(audit['line']);reason=json.loads(line['reason']);snap=audit['snapshot']
  assert reason['reportDocumentSha256']==args['expectedReportDigest']
  assert reason['documentSha256']==hashlib.sha256(document).hexdigest()
  assert audit['lineSha256']==hashlib.sha256(audit['line'].encode()).hexdigest()
  assert line['snapshot_ref']=='report-snapshot:'+snap['key'];assert audit['seq']==line['seq']==snap['doc']['auditSeq']
  assert line['reason']==snap['doc']['reason']
  if fmt=='pdf':assert document.startswith(b'%PDF-')
  else:
   with zipfile.ZipFile(io.BytesIO(document))as dz:assert '调查'.encode() in dz.read('word/document.xml')
 # Newly shaped reason is still valid under existing backup/import, with no rendition table/files.
 package=c.get(BASE+'/export',headers=H);assert package.status_code==200,package.text[:200]
 import base64
 target=tmp_path/'target'
 with TestClient(create_app(Settings(data_dir=target,db_url=f'sqlite:///{target}/mcis.db',seed_demo=False)))as dest:
  payload={'contentBase64':base64.b64encode(package.content).decode()}
  response=dest.post('/api/v1/packages/intakes:preview',headers=H,json=payload)
  assert response.status_code==200,response.text
  assert response.json()['packageVersion']=='1.2.0'
  restored=dest.post('/api/v1/packages/intakes:commit',headers=H,json={**payload,'confirmed':True,'sourceSha256':hashlib.sha256(package.content).hexdigest()})
  assert restored.status_code==200,restored.text
  assert dest.get(BASE+'/reports/'+report['reportId'],headers=H).json()==report
 assert not list(c.app.state.settings.blob_dir.rglob('*.pdf'))

@pytest.mark.parametrize('change',['report','deny','policy-readable'])
def test_render_outside_transaction_and_recheck(origin,change,monkeypatch):
 c,report,path=origin;args=body(c,path);before=counts(c)
 def racing(doc,**kw):
  # Independent connection can commit while renderer runs; not a mutation on the held Session.
  with c.app.state.db.session()as s:
   if change=='report':
    row=s.scalars(select(ReportRow)).one();d=dict(row.doc);d['createdBy']='Synthetic change';put_doc(s,ReportRow,CID,row.key,d)
   else:
    p=default_policy()
    if change=='deny':p['matrix']['LeadInvestigator']['audit']='Deny'
    else:p['version']='synthetic-new-policy'
    put_doc(s,AccessPolicyRow,CID,'policy',p)
  return b'synthetic-render-result'
 monkeypatch.setattr(module,'render',racing)
 r=post(c,path,args,403 if change=='deny' else 409)
 assert counts(c)==before

@pytest.mark.parametrize('failure',['render','size','audit-size','zip','append'])
def test_no_success_event_on_failure(origin,failure,monkeypatch):
 c,report,path=origin;args=body(c,path);before=counts(c)
 monkeypatch.setattr(module,'render',lambda *a,**k:b'synthetic')
 if failure=='render':
  def fail(*a,**k):raise ValueError('private path')
  monkeypatch.setattr(module,'render',fail);status=503
 elif failure=='size':monkeypatch.setattr(module,'OUTPUT_LIMIT',1);status=413
 elif failure=='audit-size':monkeypatch.setattr(module,'AUDIT_LIMIT',1);status=413
 elif failure=='zip':monkeypatch.setattr(module,'ZIP_LIMIT',1);status=413
 else:
  old=module.service.append_operation
  def fail(*a,**k):old(*a,**k);raise RuntimeError('synthetic after append')
  monkeypatch.setattr(module.service,'append_operation',fail);status=500
 r=post(c,path,args,status);assert 'private path'not in r.text;assert counts(c)==before

@pytest.mark.parametrize('role',['Investigator','Public','AgentService'])
def test_deny_before_render_and_existence(origin,role,monkeypatch):
 c,report,path=origin
 def no(*a,**k):raise AssertionError('must not render')
 monkeypatch.setattr(module,'render',no)
 for url in(path,path.replace(report['reportId'],'MISSING')):
  r=c.post(url,headers={**H,'X-MCIS-Role':role},json={});assert r.status_code==403
  assert c.get(url+':preview',headers={**H,'X-MCIS-Role':role}).status_code==403

@pytest.mark.parametrize('raw',[b'{}',b'{"format":"pdf","format":"docx"}',b'{"format":[]}',b'{"x":NaN}',b'\xef\xbb\xbf{}',b'{"x":"\\ud800"}',b'{"x":1}'])
def test_strict_body(origin,raw):
 c,_,path=origin;r=c.post(path,headers={**H,'Content-Type':'application/json'},content=raw);assert r.status_code==422

def test_expected_digest_stale_never_renders(origin,monkeypatch):
 c,_,path=origin;args=body(c,path);args['expectedReportDigest']='0'*64
 def no(*a,**k):raise AssertionError('must not render')
 monkeypatch.setattr(module,'render',no);assert post(c,path,args,409).json()['code']=='REPORT_OUTPUT_CHANGED'

@pytest.mark.parametrize('bad',['case','key','missing-source'])
def test_current_source_rows_checked_not_assumed_by_report_gate(origin,bad):
 from mcis_service.interviews.models import InterviewRow
 c,_,path=origin
 with c.app.state.db.session()as s:
  doc={'caseId':CID,'recordId':'IR-SYNTH','evidenceId':'MISSING','sourceSha256':'a'*64}
  if bad=='case':doc['caseId']='OTHER'
  if bad=='key':doc['recordId']='OTHER'
  put_doc(s,InterviewRow,CID,'IR-SYNTH',doc)
 r=c.get(path+':preview',headers=H);assert r.status_code in(403,409),r.text


def test_renderer_mutation_cannot_change_captured_document(origin,monkeypatch):
 c,report,path=origin;args=body(c,path)
 def mutate(doc,**kw):doc['lang']='en';doc['createdBy']='mutated renderer';return b'synthetic'
 monkeypatch.setattr(module,'render',mutate)
 with zipfile.ZipFile(io.BytesIO(post(c,path,args).content))as z:assert json.loads(z.read('report.json'))==report
 assert c.get(BASE+'/reports/'+report['reportId'],headers=H).json()==report


def test_error_after_commit_keeps_event_no_false_noncommit_marker(origin,monkeypatch):
 c,_,path=origin;args=body(c,path);before=counts(c);original=module.generate
 monkeypatch.setattr(module,'render',lambda *a,**k:b'synthetic')
 def committed(*a,**kw):original(*a,**kw);raise RuntimeError('synthetic response loss')
 monkeypatch.setattr(module,'generate',committed)
 r=post(c,path,args,500);assert 'x-mcis-write-outcome'not in r.headers
 assert counts(c)==tuple(x+1 for x in before)


def test_true_sql_commit_failure_rolls_back_export(origin,monkeypatch):
 from sqlalchemy.orm import Session
 c,_,path=origin;args=body(c,path);before=counts(c);original=Session.commit
 def failing(s):
  if any(getattr(r,'action',None)=='report.export'for r in s.identity_map.values()):raise RuntimeError('synthetic commit failure')
  return original(s)
 # append audit object may be GC'd from identity_map; use before_commit DB inspection instead.
 from sqlalchemy import event
 def before_commit(s):
  if s.info.get('synthetic_export_added'):raise RuntimeError('synthetic commit failure')
 old=module.service.append_operation
 def append(s,*a,**kw):result=old(s,*a,**kw);s.info['synthetic_export_added']=True;return result
 monkeypatch.setattr(module.service,'append_operation',append)
 event.listen(Session,'before_commit',before_commit)
 try:post(c,path,args,500)
 finally:event.remove(Session,'before_commit',before_commit)
 assert counts(c)==before


@pytest.mark.parametrize('pair',[('pdf','pdf'),('pdf','docx'),('pdf','legacy-pdf')])
def test_real_concurrent_renderers_and_legacy_export(origin,pair):
 from concurrent.futures import ThreadPoolExecutor
 from mcis_service.reports import exporter
 from threading import Barrier
 c,report,path=origin;args=body(c,path);barrier=Barrier(2);before=counts(c)
 # Cold cache exercises actual font-register/cache path without a global DB lock around new rendering.
 exporter._font.cache_clear()
 def run(fmt):
  barrier.wait(timeout=5)
  if fmt=='legacy-pdf':return c.get(BASE+'/reports/'+report['reportId']+'/export?format=pdf&lang=zh',headers=H)
  return c.post(path,headers=H,json={**args,'format':fmt})
 with ThreadPoolExecutor(max_workers=2)as pool:responses=list(pool.map(run,pair))
 assert all(r.status_code==200 for r in responses),[(r.status_code,r.text[:100])for r in responses if r.status_code!=200]
 assert counts(c)==tuple(x+2 for x in before)
 for r,fmt in zip(responses,pair):
  if fmt=='legacy-pdf':assert r.content.startswith(b'%PDF-');continue
  with zipfile.ZipFile(io.BytesIO(r.content))as z:
   data=z.read('report.'+fmt)
   if fmt=='pdf':assert data.startswith(b'%PDF-')
   else:
    with zipfile.ZipFile(io.BytesIO(data))as d:assert 'word/document.xml'in d.namelist()


@pytest.mark.parametrize('mode',['media','body-limit','report-limit','nonfinite','depth'])
def test_budgets_and_stored_validation_before_render(origin,mode,monkeypatch):
 c,report,path=origin;args=body(c,path);before=counts(c)
 def no(*a,**k):raise AssertionError('must not render')
 monkeypatch.setattr(module,'render',no)
 if mode=='media':
  r=c.post(path,headers={**H,'Content-Type':'text/plain'},content='{}');assert r.status_code==415
 elif mode=='body-limit':
  r=c.post(path,headers={**H,'Content-Type':'application/json'},content=b' '*1025);assert r.status_code==413
 elif mode=='report-limit':
  monkeypatch.setattr(module,'REPORT_LIMIT',1)
  assert c.get(path+':preview',headers=H).status_code==413
  post(c,path,args,413)
 else:
  with c.app.state.db.session()as s:
   d=dict(report)
   if mode=='nonfinite':d['unknown']=float('nan')
   else:
    v=[]
    for _ in range(65):v=[v]
    d['unknown']=v
   put_doc(s,ReportRow,CID,report['reportId'],d)
  assert c.get(path+':preview',headers=H).status_code==422
  post(c,path,args,422)
 assert counts(c)==before

@pytest.mark.parametrize('field,value',[('afterValue',{'sha256':'0'*64}),('sectionId','forged'),('summary','forged'),('extra','forged'),('auditSeq',True)])
def test_persisted_snapshot_fault_rolls_back_before_zip(origin,monkeypatch,field,value):
 c,_,path=origin;args=body(c,path);before=counts(c);old=module.service.append_operation
 def corrupt(s,*a,**kw):
  seq=old(s,*a,**kw)
  row=s.scalars(select(ReportAuditRow).where(ReportAuditRow.doc['auditSeq'].as_integer()==seq)).one()
  row.doc={**row.doc,field:value};s.flush();return seq
 monkeypatch.setattr(module.service,'append_operation',corrupt)
 monkeypatch.setattr(module,'render',lambda *a,**k:b'synthetic')
 post(c,path,args,422);assert counts(c)==before


def test_utf8_media_and_output_side_budgets(origin,monkeypatch):
 c,_,path=origin;args=body(c,path);before=counts(c)
 r=c.post(path,headers={**H,'Content-Type':'application/json; charset=latin1'},json=args);assert r.status_code==415
 monkeypatch.setattr(module,'render',lambda *a,**k:b'synthetic')
 monkeypatch.setattr(module,'MANIFEST_LIMIT',1)
 r=c.post(path,headers={**H,'Content-Type':'application/json; charset=utf-8'},json=args);assert r.status_code==413
 assert counts(c)==before

@pytest.mark.parametrize('category',list(default_policy()['categories']))
def test_each_full_content_category_required(origin,category):
 c,_,path=origin
 with c.app.state.db.session()as s:
  p=default_policy();p['matrix']['LeadInvestigator'][category]='Deny';put_doc(s,AccessPolicyRow,CID,'policy',p)
 assert c.get(path+':preview',headers=H).status_code==403
 assert c.post(path,headers=H,json={}).status_code==403


def test_source_content_change_allowed_but_current_binding_rechecked(origin,monkeypatch):
 from mcis_service.evidence.models import EvidenceRow
 c,_,path=origin
 with c.app.state.db.session()as s:put_doc(s,EvidenceRow,CID,'EV-SYNTH',{'caseId':CID,'evidenceId':'EV-SYNTH','title':'original','sha256':'a'*64,'confidentiality':'Restricted'})
 args=body(c,path)
 def changed(doc,**kw):
  with c.app.state.db.session()as s:
   row=s.scalars(select(EvidenceRow)).one();row.doc={**row.doc,'title':'updated source title'}
  return b'synthetic'
 monkeypatch.setattr(module,'render',changed)
 post(c,path,args)
 def corrupt(doc,**kw):
  with c.app.state.db.session()as s:
   row=s.scalars(select(EvidenceRow)).one();row.doc={**row.doc,'caseId':'OTHER'}
  return b'synthetic'
 monkeypatch.setattr(module,'render',corrupt)
 before=counts(c);post(c,path,args,409);assert counts(c)==before


def test_new_output_contract_routes_independent_of_old_reports(origin):
 import yaml
 from mcis_service.config import PROJECT_ROOT
 c,_,_=origin
 spec=yaml.safe_load((PROJECT_ROOT/'contracts/openapi.yaml').read_text())
 def selected(paths):
  return {(method.upper(),path)for path,item in paths.items()for method,operation in item.items()
          if method in('get','post')and isinstance(operation,dict)and'report-output'in operation.get('tags',[])}
 actual=selected(c.app.openapi()['paths']);declared=selected(spec['paths'])
 assert len(actual)==2 and actual==declared


def test_large_valid_policy_does_not_inherit_report_byte_cap(origin,monkeypatch):
 c,_,path=origin
 policy=default_policy();policy['fieldRules'][0]['description']='Synthetic policy description '+('x'* (module.REPORT_LIMIT+100))
 with c.app.state.db.session()as s:put_doc(s,AccessPolicyRow,CID,'policy',policy)
 # The rule applies only to other roles, so Lead retains the same complete permissions.
 args=body(c,path)
 monkeypatch.setattr(module,'render',lambda *a,**kw:b'synthetic')
 post(c,path,args)
 assert module.canonical_hash(policy)==hashlib.sha256(module.canonical(policy,3*module.REPORT_LIMIT)).hexdigest()
