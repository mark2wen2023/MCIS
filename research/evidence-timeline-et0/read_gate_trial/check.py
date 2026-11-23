"""Real temporary SQLite read + separate ET0 postcondition control, NOT integration."""
import argparse,asyncio,base64,hashlib,importlib.util,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from copy import deepcopy
ROOT=Path(__file__).resolve().parent
PINS=json.loads((ROOT/'pins.json').read_text())
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def export(destination,args):
 for p in PINS:
  if args.dependencies:raw=(args.dependencies/p['path']).read_bytes()
  else:
   raw=subprocess.check_output(['git','-C',str(args.repo),'--no-replace-objects','show',p['ref']+':'+p['path']],env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0',GIT_OPTIONAL_LOCKS='0'),timeout=15)
  if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=p['blob']:raise ValueError('PIN_MISMATCH:'+p['path'])
  target=destination/p['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)

class Body:
 """Only request transport is replaced; actual intake functions execute."""
 headers={'content-type':'application/json'}
 def __init__(self,obj):self.raw=json.dumps(obj).encode()
 async def stream(self):yield self.raw

RESULT={}
def run(source):
 sys.path.insert(0,str(source/'service'))
 from sqlalchemy import text,select
 from fastapi import HTTPException
 from mcis_service.db import Database,Base,put_doc,APPEND_ONLY_TABLES
 from mcis_service.common.context import Ctx
 from mcis_service.common import contracts
 from mcis_service.cases.models import CaseRow
 from mcis_service.evidence.models import EvidenceRow,CustodyEventRow
 from mcis_service.audit.models import AuditEventRow
 from mcis_service.audit import service as audit
 from mcis_service.redaction.models import AccessPolicyRow
 from mcis_service.redaction.policy import default_policy
 from mcis_service.working_records_archive.models import ArchiveImportHistoryRow
 from mcis_service.track_history.models import LocalReceipt
 from mcis_service.evidence_intake import router as intake
 host_path=source/'research/evidence-timeline-et0/host_trial'
 old=load(host_path/'check.py','pinned_host_checks');adapter=load(host_path/'adapter.py','pinned_adapter')
 T,S=old.dependencies(directory=source/'research/evidence-timeline-et0')

 class Checks(unittest.TestCase):
  def setUp(self):
   self.tmp=tempfile.TemporaryDirectory(prefix='read-gate-',dir=source);self.addCleanup(self.tmp.cleanup)
   self.root=Path(self.tmp.name);self.blobs=self.root/'blobs';self.blobs.mkdir()
   self.url='sqlite:///'+str(self.root/'fresh.sqlite');self.db=Database(self.url);self.addCleanup(lambda:self.db.engine.dispose())
   tables=[m.__table__ for m in (CaseRow,EvidenceRow,CustodyEventRow,AuditEventRow,AccessPolicyRow,ArchiveImportHistoryRow,LocalReceipt)]
   Base.metadata.create_all(self.db.engine,tables=tables)
   with self.db.engine.begin() as conn:
    for table in APPEND_ONLY_TABLES:
     for op in ('UPDATE','DELETE'):
      conn.execute(text(f"CREATE TRIGGER {table}_no_{op.lower()} BEFORE {op} ON {table} BEGIN SELECT RAISE(ABORT, 'append-only'); END;"))
   self.state=SimpleNamespace(db=self.db,settings=SimpleNamespace(blob_dir=self.blobs))
   self.ctx=Ctx('Investigator','Synthetic read-gate operator',SimpleNamespace(app=SimpleNamespace(state=self.state)))
   # Fixed B raw bytes, not compact reserialization. No schema/fixture modifications.
   self.raw=(source/'tests_acceptance/shared-trajectory-cross-repo-expanded/vessel-b.json').read_bytes()
   self.doc=json.loads(self.raw);self.cid=self.doc['caseId']
   case=dict(caseId=self.cid,schemaVersion='1.0.0',title='Synthetic post-read gate',accidentType='Synthetic',isFictionalDemo=True,caseEpochUtc='2026-02-01T12:00:00Z',incidentTimeUtc='2026-02-01T12:00:00Z',incidentLocation=dict(lonDeg=-130,latDeg=-30),displayTimeZoneOffsetMinutes=0)
   contracts.validate('case',case)
   with self.db.session() as s:
    put_doc(s,CaseRow,self.cid,self.cid,case);put_doc(s,AccessPolicyRow,self.cid,'policy',default_policy())
   payload=dict(profile='mcis-evidence-intake-v1',fileName='synthetic.json',title='Synthetic fixed original',source='Handmade fixture, not authenticated evidence',extractedBy='Synthetic author',extractedUtc='2026-02-01T00:00:00Z',category='Other',confidentiality='Restricted',note='synthetic',contentBase64=base64.b64encode(self.raw).decode())
   preview=asyncio.run(intake.preview_input(self.cid,Body(payload),self.ctx))
   self.receipt=asyncio.run(intake.commit_input(self.cid,Body(dict(payload,requestDigest=preview['requestDigest'],confirmed=True)),self.ctx))
   self.assertEqual(self.receipt['sourceSha256'],hashlib.sha256(self.raw).hexdigest())

  def snapshot(self):
   with self.db.engine.connect() as c:
    names=c.execute(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")).scalars().all()
    return {name:[tuple(row) for row in c.execute(text('SELECT * FROM "'+name+'" ORDER BY 1'))] for name in names}
  def files(self):return {str(f.relative_to(self.blobs)):hashlib.sha256(f.read_bytes()).hexdigest() for f in self.blobs.rglob('*') if f.is_file()}
  def separate_et0(self):
   # Deliberately separate fixture: registered V1 is NOT rewritten into ET0 rows.
   config,proposal=old.fixture();config['reviews']={};config['selected']={}
   before=deepcopy((config,proposal))
   out=adapter.TrialHost(**config,timeline=T,scoped=S).compare(proposal)
   self.assertEqual((config,proposal),before)
   self.assertEqual(out['relation'],'undetermined')
   self.assertTrue(all(r['reason']=='NO_REVIEW' for r in out['sources']))
   self.assertFalse(out['authorityVerified']);self.assertFalse(out['saved'])
   return out

  def test_committed_access_does_not_supply_calibration(self):
   initial=self.snapshot();files=self.files();before_et0=self.separate_et0()
   response=asyncio.run(intake.download(self.cid,self.receipt['requestDigest'],Body({'purpose':'Synthetic read only; not calibration review'}),self.ctx))
   self.assertEqual(response.body,self.raw)
   self.assertEqual(response.headers['x-sha256'],hashlib.sha256(self.raw).hexdigest())
   # Engine disposal and new connection prove successful post-commit readback.
   self.db.engine.dispose();self.db=Database(self.url);self.state.db=self.db
   after=self.snapshot();self.assertEqual(set(after),set(initial))
   for table in initial:
    if table in ('custody_events','audit_events'):self.assertEqual(len(after[table]),len(initial[table])+1)
    else:self.assertEqual(after[table],initial[table],table)
   self.assertEqual(self.files(),files)
   with self.db.session() as s:
    accesses=s.scalars(select(CustodyEventRow).where(CustodyEventRow.kind=='Access')).all()
    self.assertEqual(len(accesses),1);self.assertEqual(accesses[0].sha256,self.receipt['sourceSha256']);self.assertEqual(accesses[0].evidence_id,self.receipt['evidenceId'])
    actions=[x.action for x in s.scalars(select(AuditEventRow).order_by(AuditEventRow.seq))]
    self.assertEqual(actions,['custody.register','custody.access'])
    self.assertTrue(audit.verify_chain(audit.all_lines(s,self.cid))['valid'])
    custody=s.scalars(select(CustodyEventRow).order_by(CustodyEventRow.seq)).all();self.assertTrue(audit.verify_chain([x.line for x in custody])['valid'])
   returned=json.loads(response.body)
   self.assertNotIn('rows',returned);self.assertNotIn('sourceId',returned)
   clock=returned['points'][12]['time'];self.assertEqual(clock['status'],'corrected');self.assertEqual(clock['correctionSeconds'],12)
   after_et0=self.separate_et0();self.assertEqual(before_et0,after_et0)
   self.assertEqual(self.snapshot(),after) # Pure ET0 check performs no DB write.
   RESULT.update(read={'sourceCommit':'db90fdf73de7bd26ba75819f0102fc03d0789faf','sourceSha256':self.receipt['sourceSha256'],'accessAdded':1,'custodyAdded':1,'auditAdded':1,'reopened':True,'otherTablesUnchanged':True,'originalFilesUnchanged':True,'actualCalibrationApprovals':0},et0={'commit':'8a2478f66b6a41c753e3b71c6e1d95d4bf76a82c','relation':after_et0['relation'],'reviewSelections':0,'authorityVerified':False},integration='NOT_CONNECTED: registered V1 and separate ET0 fixture; no raw-time conversion',http=False,realIdentity=False,model=False,published=False)

  def test_denied_read_no_delivery_or_access(self):
   before=self.snapshot();files=self.files()
   denied=Ctx('ExternalExpert','Synthetic denied role',self.ctx.request)
   with self.assertRaises(HTTPException) as err:asyncio.run(intake.download(self.cid,self.receipt['requestDigest'],Body({'purpose':'Synthetic denial'}),denied))
   self.assertEqual(err.exception.status_code,403)
   self.assertEqual(self.snapshot(),before);self.assertEqual(self.files(),files)
   self.assertEqual(self.separate_et0()['relation'],'undetermined')

 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
 allowed={p['path'] for p in PINS}
 for name,module in tuple(sys.modules.items()):
  if name=='mcis_service' or name.startswith('mcis_service.'):
   file=Path(module.__file__).resolve();relative=str(file.relative_to(source))
   if relative not in allowed:raise RuntimeError('unexpected import '+relative)
 if 'mcis_service.main' in sys.modules or 'mcis_service.models_registry' in sys.modules:raise RuntimeError('app import')
 print(json.dumps({'testsRun':result.testsRun,'passed':result.wasSuccessful(),'result':RESULT},indent=2))
 return result.wasSuccessful()

if __name__=='__main__':
 if not sys.flags.isolated or sys.flags.optimize:raise SystemExit('Use -I -B without -O')
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--repo',type=Path);g.add_argument('--dependencies',type=Path);args=p.parse_args()
 with tempfile.TemporaryDirectory(prefix='et0-read-gate-source-') as folder:
  source=Path(folder);export(source,args);ok=run(source)
 raise SystemExit(0 if ok else 1)
