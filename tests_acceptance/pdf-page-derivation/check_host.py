"""Synthetic FastAPI/TestClient + real temporary SQLite + Poppler. No model/app seed."""
import base64, hashlib, importlib.util, io, sys, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'service'))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from PIL import Image
from mcis_service.db import Database,Base,put_doc,APPEND_ONLY_TABLES
from mcis_service.cases.models import CaseRow
from mcis_service.evidence.models import EvidenceRow,CustodyEventRow
from mcis_service.audit.models import AuditEventRow
from mcis_service.audit import service as audit
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.working_records_archive.models import ArchiveImportHistoryRow
from mcis_service.track_history.models import LocalReceipt
from mcis_service.evidence_intake import router as intake
from mcis_service.image_review.app import Record,Storage
from mcis_service.image_review import synthetic_pdf as host

spec=importlib.util.spec_from_file_location('pdf_fixture',ROOT/'tests_acceptance/pdf-page-derivation/check.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)

class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='w4-synthetic-http-');self.addCleanup(self.tmp.cleanup)
  path=Path(self.tmp.name);(path/'blobs').mkdir()
  self.db=Database('sqlite:///'+str(path/'db.sqlite'))
  Base.metadata.create_all(self.db.engine,tables=[m.__table__ for m in (CaseRow,EvidenceRow,CustodyEventRow,AuditEventRow,AccessPolicyRow,ArchiveImportHistoryRow,LocalReceipt)])
  Storage.metadata.create_all(self.db.engine)
  with self.db.engine.begin() as c:
   for t in (*APPEND_ONLY_TABLES,'image_ocr_review_records'):
    for op in ('UPDATE','DELETE'):
     c.execute(text(f"CREATE TRIGGER {t}_no_{op.lower()} BEFORE {op} ON {t} BEGIN SELECT RAISE(ABORT,'append-only'); END;"))
  self.app=FastAPI();self.app.state.db=self.db;self.app.state.settings=SimpleNamespace(blob_dir=path/'blobs')
  self.app.include_router(intake.router);self.app.include_router(host.router)
  self.client=TestClient(self.app,raise_server_exceptions=False)
  case=dict(caseId=host.CASE,schemaVersion='1.0.0',title='Synthetic PDF pages',accidentType='Synthetic',isFictionalDemo=True,caseEpochUtc='2026-02-01T12:00:00Z',incidentTimeUtc='2026-02-01T12:00:00Z',incidentLocation=dict(lonDeg=-130,latDeg=-30),displayTimeZoneOffsetMinutes=0)
  with self.db.session() as s:
   put_doc(s,CaseRow,host.CASE,host.CASE,case);put_doc(s,AccessPolicyRow,host.CASE,'policy',default_policy())
  self.raw=fixture.synthetic_pdf();self.assertEqual(hashlib.sha256(self.raw).hexdigest(),host.SOURCE)
  body=dict(profile='mcis-evidence-intake-v1',fileName='synthetic.pdf',title='Synthetic two-page PDF',source='fixture generator',extractedBy='Synthetic author',extractedUtc='2026-02-01T00:00:00Z',category='Document',confidentiality='Restricted',note='synthetic only',contentBase64=base64.b64encode(self.raw).decode())
  self.base='/api/v1/cases/'+host.CASE
  r=self.client.post(self.base+'/evidence-intakes:preview',json=body)
  self.assertEqual(r.status_code,200,r.text)
  r=self.client.post(self.base+'/evidence-intakes:commit',json={**body,'requestDigest':r.json()['requestDigest'],'confirmed':True})
  self.assertEqual(r.status_code,200,r.text);self.pin=r.json()
  self.run='OCR-synthetic-pdf'
  self.binding=host.SyntheticPdfBinding(self.run,0,self.pin['requestDigest'],self.pin['evidenceId'])
  self.url=self.base+'/image-reviews/'+self.run+'/synthetic-pdf-page'
 def seed(self,*,page=1,digest=host.SOURCE,revision=0):
  # Existing review state is a declared test fixture, not an OCR execution.
  doc={'bindings':{'pdf':self.pin['requestDigest']},'sourceVersions':{'pdf':{'evidenceId':self.pin['evidenceId'],'sha256':digest}},'candidate':{'source':{'pdf_sha256':digest,'pdf_page_1based':page}}}
  with self.db.session() as s:s.add(Record(case_id=host.CASE,run_id=self.run,revision=revision,doc=doc))
  self.app.state.synthetic_pdf_binding=self.binding
 def counts(self):
  with self.db.session() as s:return tuple(s.query(m).count() for m in (EvidenceRow,CustodyEventRow,AuditEventRow,Record))
 def reject(self,code,**kw):
  before=self.counts();r=self.client.post(self.url,json=kw.pop('json',{'expectedRevision':0}),**kw)
  self.assertEqual(r.status_code,code,r.text);self.assertNotIn('pngBase64',r.text);self.assertEqual(self.counts(),before)
 def tearDown(self):
  self.client.close();self.db.engine.dispose();self.tmp.cleanup()
 def test_success_one_access_and_reopen(self):
  self.seed();before=self.counts();r=self.client.post(self.url,json={'expectedRevision':0})
  self.assertEqual(r.status_code,200,r.text);d=r.json()
  self.assertEqual(set(d),{'caseId','runId','revision','description','pngBase64'})
  self.assertEqual((d['caseId'],d['runId'],d['revision']),(host.CASE,self.run,0))
  png=base64.b64decode(d['pngBase64']);desc=d['description']
  self.assertEqual(desc['sourceSha256'],host.SOURCE);self.assertEqual(desc['physicalPage'],1)
  self.assertEqual(desc['pageSha256'],hashlib.sha256(png).hexdigest())
  with Image.open(io.BytesIO(png)) as im:self.assertEqual(im.convert('RGB').getpixel((128,128)),(255,0,0))
  self.assertEqual(self.counts(),(before[0],before[1]+1,before[2]+1,before[3]))
  self.assertEqual(r.headers['cache-control'],'no-store')
  self.db.engine.dispose()
  with self.db.session() as s:
   events=s.query(CustodyEventRow).order_by(CustodyEventRow.seq).all()
   self.assertEqual([e.kind for e in events],['Register','Access'])
   self.assertTrue(audit.verify_chain([e.line for e in events])['valid'])
   self.assertTrue(audit.verify_chain(audit.all_lines(s,host.CASE))['valid'])
  self.assertEqual(next((Path(self.tmp.name)/'blobs').rglob('*.bin')).read_bytes(),self.raw)
 def test_default_off(self):self.reject(404)
 def test_wrong_case(self):
  self.seed();self.url=self.url.replace(host.CASE,'OTHER');self.reject(404)
 def test_wrong_run(self):
  self.seed();self.url=self.url.replace(self.run,'OCR-other');self.reject(404)
 def test_lost_permission(self):
  self.seed()
  with self.db.session() as s:
   p=default_policy();p['matrix']['Investigator']['evidence_meta']='Deny';put_doc(s,AccessPolicyRow,host.CASE,'policy',p)
  self.reject(403)
 def test_unauthorized_role(self):self.seed();self.reject(403,headers={'X-MCIS-Role':'Public'})
 def test_stale_request(self):self.seed();self.reject(409,json={'expectedRevision':1})
 def test_stale_current_revision(self):self.seed(revision=1);self.reject(409)
 def test_wrong_source_digest(self):self.seed(digest='0'*64);self.reject(409)
 def test_wrong_bound_page(self):self.seed(page=2);self.reject(409)
 def test_client_cannot_select_source_or_page(self):
  self.seed()
  for key,value in [('page',2),('path','anything'),('url','anything'),('sha256','0'*64)]:
   with self.subTest(key=key):self.reject(422,json={'expectedRevision':0,key:value})
 def test_changed_registered_bytes_refused(self):
  self.seed()
  original=next((Path(self.tmp.name)/'blobs').rglob('*.bin'))
  original.write_bytes(self.raw+b'changed')
  self.reject(409)
 def test_original_download_unchanged(self):
  self.seed();before=self.counts()
  r=self.client.post(self.base+'/evidence-intakes/'+self.pin['requestDigest']+':download',json={'purpose':'Synthetic original path regression'})
  self.assertEqual(r.status_code,200);self.assertEqual(r.content,self.raw)
  self.assertEqual(self.counts(),(before[0],before[1]+1,before[2]+1,before[3]))
 def test_audit_failure_rolls_back_access(self):
  self.seed()
  with self.db.engine.begin() as c:c.execute(text("CREATE TRIGGER fail_audit BEFORE INSERT ON audit_events BEGIN SELECT RAISE(ABORT,'test audit failure'); END;"))
  self.reject(500)
if __name__=='__main__':unittest.main(verbosity=2)
