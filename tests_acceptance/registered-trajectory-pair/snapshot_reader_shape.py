"""Synthetic fixed storage-shape fixtures, NOT execution of the report generator.
Real temporary SQLite, raw registration, session verification and prepare only.
No service/sources import, HTTP, export, historical repair or binding persistence.
"""
import os
os.environ['GIT_NO_LAZY_FETCH']='1'
import asyncio, hashlib, json, runpy, secrets, subprocess, sys, tempfile
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PARENT='17247747272fb53623b144e199260f59d6befcbd'
raw=runpy.run_path(str(Path(__file__).with_name('raw_fixture_prepare.py')))
pilot=raw['pilot'];base=pilot['base']
OLD='--old-reader' in sys.argv

class StorageShape:
 register=raw['Raw'].register
 def test_absent_identity_and_rejections(self):
  from sqlalchemy import select,text
  from fastapi import HTTPException
  from mcis_service.db import Base,put_doc
  from mcis_service.reports.models import ReportRow,ReportAuditRow
  from mcis_service.reports.pilot_trajectory_prepare import PilotTrajectoryPrepare,PrepareUnavailable,OPERATION
  from mcis_service.reports.generation_snapshot import GenerationSnapshotUnavailable
  from mcis_service.common.local_review_pilot import PilotSessions,PilotSession
  from mcis_service.audit import service as audit
  from mcis_service.evidence.models import CustodyEventRow
  Base.metadata.create_all(self.db.engine,tables=[ReportRow.__table__,ReportAuditRow.__table__])
  rid='RPT-'+'1'*20;sid='RA-'+'1'*32
  sentence=dict(sentenceId='synthetic-sentence',status='Draft',source='Generated',textZh='合成私有正文',textEn='PRIVATE SYNTHETIC PROSE',generatedText=dict(textZh='合成私有正文',textEn='PRIVATE SYNTHETIC PROSE'),reviewedBy=None,reviewedAt=None,reviews=[],missing=False,citations=[])
  section=dict(sectionId='synthetic-section',titleZh='合成',titleEn='Synthetic',dataSources=[],sentences=[sentence],**{k:deepcopy(v) for k,v in sentence.items() if k not in ('sentenceId','citations')})
  report=dict(reportId=rid,familyId=rid,parentReportId=None,caseId=self.cid,templateId='imo-cic',lang='bilingual',version=1,status='Draft',isFictionalDemo=True,realDataStatus='fictional',createdBy='synthetic',createdUtc='2026-01-01T00:00:00Z',sections=[section],disclaimerZh='合成',disclaimerEn='Synthetic',reportHref='#/report')
  with self.db.session() as s:
   event=audit.append(s,case_id=self.cid,operator='Synthetic fixture author',role='Investigator',action='report.generate',category='Report',command='Storage-shape fixture; generator NOT executed',entity_type='report',entity_id=rid,snapshot_ref='report-snapshot:'+sid)
   snap=dict(reportId=rid,sectionId=None,sentenceId=None,reason='',beforeValue=None,afterValue=report,summary='synthetic storage-shape fixture',auditSeq=event.seq)
   put_doc(s,ReportAuditRow,self.cid,sid,snap)
   # Independent fixture rows; never repair or mutate the first row.
   for digit,doc in [('2',{**deepcopy(snap),'snapshotId':None}),('3',{**deepcopy(snap),'snapshotId':sid}),('4',deepcopy(snap))]:
    put_doc(s,ReportAuditRow,self.cid,'RA-'+digit*32,doc)
  token=secrets.token_urlsafe(32);digest=hashlib.sha256(token.encode()).hexdigest();subject='Synthetic shape subject'
  grants=frozenset(((self.cid,OPERATION),(self.cid,'evidence.original.access')))
  sessions=PilotSessions({digest:PilotSession(subject,'LeadInvestigator',20,grants)},clock=lambda:10,report_reference_subject=subject)
  key=(self.cid,sid,'synthetic-section','synthetic-sentence')
  def prepare(**patch):
   cfg=dict(enabled=True,sessions=sessions,db=self.db,settings=self.ctx.settings,subject=subject,key=key,pin=self.pins[0]);cfg.update(patch)
   return asyncio.run(PilotTrajectoryPrepare(**cfg).prepare(token))
  with self.db.session() as s:
   before_docs={r.key:deepcopy(r.doc) for r in s.scalars(select(ReportAuditRow))}
  before=self.counts()
  if OLD:
   with self.assertRaisesRegex(PrepareUnavailable,'generation_identity_mismatch'):prepare()
   self.assertEqual(self.counts(),before)
  else:
   result=prepare()
   self.assertEqual(result['generationSnapshotId'],sid);self.assertEqual(result['original'],self.pins[0])
   self.assertEqual(result['locator'],{'jsonPointer':'/points/7'});self.assertFalse(result['saved'])
   self.assertNotIn('PRIVATE',json.dumps(result));self.assertNotIn('正文',json.dumps(result,ensure_ascii=False))
   self.assertEqual(self.counts(),(before[0],before[1]+1,before[2]+1))
  baseline=self.counts()
  for digit in ('2','3'):
   with self.assertRaisesRegex(PrepareUnavailable,'generation_identity_mismatch'):prepare(key=(self.cid,'RA-'+digit*32,*key[2:]))
   self.assertEqual(self.counts(),baseline)
  error=PrepareUnavailable if OLD else GenerationSnapshotUnavailable
  with self.assertRaises(error):prepare(key=(self.cid,'RA-'+'4'*32,*key[2:]))
  self.assertEqual(self.counts(),baseline)
  with self.assertRaises(PrepareUnavailable):prepare(key=('SYN-OTHER',*key[1:]))
  denied=PilotSessions({digest:PilotSession(subject,'Investigator',20,grants)},clock=lambda:10,report_reference_subject=subject)
  with self.assertRaises(HTTPException):prepare(sessions=denied)
  self.assertEqual(self.counts(),baseline)
  with self.db.session() as s:
   self.assertEqual(s.query(ReportRow).count(),0)
   self.assertEqual({r.key:r.doc for r in s.scalars(select(ReportAuditRow))},before_docs)
   self.assertIsNone(s.execute(text("SELECT name FROM sqlite_master WHERE name='frozen_sentence_bindings_v1'")).first())
   rows=s.scalars(select(CustodyEventRow).order_by(CustodyEventRow.seq)).all()
   access=[r for r in rows if r.kind=='Access'];self.assertEqual(len(access),0 if OLD else 1)
   if access:self.assertEqual(access[0].operator,subject)
   self.assertTrue(audit.verify_chain([r.line for r in rows])['valid'])
   self.assertTrue(audit.verify_chain(audit.all_lines(s,self.cid))['valid'])
  self.assertFalse(any(n in sys.modules for n in ('mcis_service.reports.service','mcis_service.reports.sources')))
  print(json.dumps({'fixture':'fixed-storage-shape','generatorExecuted':False,'oldReader':OLD,'prepareAccessAdded':len(access),'prepareAuditAdded':baseline[2]-before[2],'reportRows':0,'snapshotFixtures':len(before_docs),'snapshotsUnchanged':True,'bindingTable':False,'http':False,'realLogin':False}))

if __name__=='__main__':
 if not sys.flags.isolated or sys.flags.optimize:raise SystemExit('Use -I -B without -O')
 for p in ('service.py','sources.py'):
  path='service/mcis_service/reports/'+p
  assert (ROOT/path).read_bytes()==subprocess.check_output(['git','show',PARENT+':'+path],cwd=ROOT)
 with tempfile.TemporaryDirectory(prefix='snapshot-reader-shape-') as folder:
  source=base['materialize'](Path(folder),ref=pilot['REF'],paths=pilot['BASE'])
  for p in pilot['NEW']:
   data=(ROOT/p).read_bytes();fixed=subprocess.check_output(['git','show',PARENT+':'+p],cwd=ROOT)
   if not p.endswith('/pilot_trajectory_prepare.py'):assert data==fixed
   elif OLD:data=fixed
   dest=source/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
  ok=base['run'](source,extra_cases=(StorageShape,pilot['Pilot']),allowed_paths=pilot['BASE']+pilot['NEW'])
 raise SystemExit(0 if ok else 1)
