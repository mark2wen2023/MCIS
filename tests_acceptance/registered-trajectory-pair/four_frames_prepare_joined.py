import asyncio,hashlib,json,os,runpy,secrets,subprocess,sys,tempfile
os.environ['GIT_NO_LAZY_FETCH']='1'
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
if not sys.flags.isolated or sys.flags.optimize:
    raise SystemExit('Use Python -I -B without -O; checks must remain enabled')
REF='d3fd9542249f214a5aa3776d7c0b8c7609ad81a7'
CLOCK_REF='8d68f6fa076b7acad90fab10e95ab88c6945a018'
PREPARE_REF='22c3c0fd06c5f6c85a4c41a3eabd6714965d6689'
FIXTURE_REF='2048c60fd6650c6f2c99a76a16be463a3895655d'
for fixed in (REF,CLOCK_REF,PREPARE_REF,FIXTURE_REF):
 subprocess.run(['git','cat-file','-e',fixed+'^{commit}'],cwd=ROOT,check=True)
# A test-only descendant is allowed; fixed parent bytes remain mandatory.
subprocess.run(['git','merge-base','--is-ancestor',REF,'HEAD'],cwd=ROOT,check=True)
for name in ('business.py','business_query.py'):
 path='tests_acceptance/registered-trajectory-pair/'+name
 assert subprocess.check_output(['git','show',CLOCK_REF+':'+path],cwd=ROOT)==subprocess.check_output(['git','show',REF+':'+path],cwd=ROOT)
for name in ('business.py','pilot_prepare.py','raw_fixture_prepare.py','business_query.py'):
 p='tests_acceptance/registered-trajectory-pair/'+name
 assert (ROOT/p).read_bytes()==subprocess.check_output(['git','show',REF+':'+p],cwd=ROOT)
raw=runpy.run_path(str(ROOT/'tests_acceptance/registered-trajectory-pair/raw_fixture_prepare.py'))
pilot=raw['pilot'];result=None
class Joined:
    register=raw['Raw'].register
    def test_four_frames_then_prepare_same_registration(self):
        from mcis_service.common.local_review_pilot import PilotSessions,PilotSession
        from mcis_service.reports.pilot_trajectory_prepare import PilotTrajectoryPrepare,PrepareUnavailable,OPERATION
        from mcis_service.reports.models import ReportRow,ReportAuditRow
        from mcis_service.db import Base,put_doc
        from mcis_service.audit import service as audit
        from mcis_service.redaction.models import AccessPolicyRow
        from mcis_service.evidence.models import CustodyEventRow
        from mcis_service.redaction.policy import default_policy
        from sqlalchemy import select,text
        from fastapi import HTTPException
        Base.metadata.create_all(self.db.engine,tables=[ReportRow.__table__,ReportAuditRow.__table__])
        rid='RPT-'+'1'*20;sid='RA-'+'1'*32
        sentence=dict(sentenceId='synthetic-sentence',status='Draft',source='Generated',textZh='合成私有正文不外泄',textEn='PRIVATE SYNTHETIC PROSE',generatedText=dict(textZh='合成私有正文不外泄',textEn='PRIVATE SYNTHETIC PROSE'),reviewedBy=None,reviewedAt=None,reviews=[],missing=False,citations=[])
        section=dict(sectionId='synthetic-section',titleZh='合成',titleEn='Synthetic',dataSources=[],sentences=[sentence],**{k:deepcopy(v) for k,v in sentence.items() if k not in ('sentenceId','citations')})
        report=dict(reportId=rid,familyId=rid,parentReportId=None,caseId=self.cid,templateId='imo-cic',lang='bilingual',version=1,status='Draft',isFictionalDemo=True,realDataStatus='fictional',createdBy='synthetic',createdUtc='2026-01-01T00:00:00Z',sections=[section],disclaimerZh='合成',disclaimerEn='Synthetic',reportHref='#/report')
        with self.db.session() as s:
            event=audit.append(s,case_id=self.cid,operator='Fixture author',role='Investigator',action='report.generate',category='Report',command='Synthetic generation fixture, not generator execution',entity_type='report',entity_id=rid,snapshot_ref='report-snapshot:'+sid)
            snap=dict(snapshotId=sid,reportId=rid,sectionId=None,sentenceId=None,reason='',beforeValue=None,afterValue=report,summary='synthetic',auditSeq=event.seq)
            put_doc(s,ReportAuditRow,self.cid,sid,snap)
        token=secrets.token_urlsafe(32);digest=hashlib.sha256(token.encode()).hexdigest();clock=[10.0]
        subject='Synthetic pilot subject'
        grants=frozenset([(self.cid,OPERATION),(self.cid,'evidence.original.access')])
        entry=PilotSession(subject,'LeadInvestigator',20.0,grants)
        with self.assertRaises(ValueError):PilotSessions({digest:entry}) # default operation absent
        sessions=PilotSessions({digest:entry},clock=lambda:clock[0],report_reference_subject=subject)
        def prepare(_credential=token,**patch):
            config=dict(enabled=True,sessions=sessions,db=self.db,settings=self.ctx.settings,subject=subject,key=(self.cid,sid,'synthetic-section','synthetic-sentence'),pin=self.pins[0]);config.update(patch)
            return asyncio.run(PilotTrajectoryPrepare(**config).prepare(_credential))
        global result
        from mcis_service.trajectory_exchange.registered_query import _query_registered_pair
        from mcis_service.common.context import Ctx
        from mcis_service.trajectory_exchange.registered_pair import RegisteredPairError
        pins=deepcopy(self.pins)
        def access_count():
            with self.db.session() as s:return s.query(CustodyEventRow).filter_by(kind='Access').count()
        self.assertEqual(access_count(),0)
        frames=[]
        samples=[('12:01:40.000',[7,12]),('12:02:01.000',[10,None]),('12:02:04.250',[None,None]),('12:02:07.500',[11,None])]
        for n,(clock_text,indices) in enumerate(samples,1):
            utc='2026-02-01T'+clock_text+'Z'
            f=_query_registered_pair(self.ctx,self.cid,pins,'Synthetic joined four frames',utc)
            self.assertEqual(f['caseId'],self.cid)
            self.assertEqual(f['alignedUtc'],utc)
            self.assertEqual(len(f['vessels']),2)
            if n==1:
                self.assertEqual(f['vessels'][0]['headingDeg'],{'value':None,'kind':'missing'})
            self.assertEqual(access_count(),n*2)
            for i,(v,index) in enumerate(zip(f['vessels'],indices)):
                self.assertEqual(v['original'],pins[i]);self.assertFalse(v['courseUsedAsHeading'])
                if index is not None:
                    self.assertEqual(v['status'],'input_point');self.assertEqual(v['locator'],{'jsonPointer':f'/points/{index}'})
                    self.assertEqual(v['time'],{k:self.docs[i]['points'][index]['time'][k] for k in ('sourceUtc','alignedUtc','correctionSeconds','status')})
                elif i==0:
                    self.assertEqual(v['status'],'declared_gap');self.assertEqual(v['locator'],{'jsonPointer':'/sampling/missingIntervals/1'})
                else:
                    self.assertEqual(v['status'],'no_observation_at_time');self.assertIsNone(v['locator'])
                if index is None:self.assertIsNone(v['position'])
            frames.append({'utc':utc,'statuses':[v['status'] for v in f['vessels']],'accessTotal':access_count()})
        out=prepare()
        self.assertEqual(out['original'],pins[0]);self.assertEqual(out['locator'],{'jsonPointer':'/points/7'})
        self.assertEqual(out['alignedUtc'],frames[0]['utc']);self.assertFalse(out['saved'])
        self.assertEqual(access_count(),9);baseline=self.counts()
        with self.assertRaisesRegex(RegisteredPairError,'CASE_MISMATCH'):
            _query_registered_pair(self.ctx,'SYN-OTHER',pins,'Synthetic wrong case',frames[0]['utc'])
        denied=Ctx('ExternalExpert','synthetic-denied',self.ctx.request)
        with self.assertRaises(HTTPException):
            _query_registered_pair(denied,self.cid,pins,'Synthetic denied role',frames[0]['utc'])
        with self.assertRaises(PrepareUnavailable):prepare(key=('SYN-OTHER',sid,'synthetic-section','synthetic-sentence'))
        without=PilotSessions({digest:PilotSession(subject,'LeadInvestigator',20.0,frozenset([(self.cid,'evidence.original.access')]))},clock=lambda:clock[0],report_reference_subject=subject)
        with self.assertRaises(PrepareUnavailable):prepare(sessions=without)
        self.assertEqual(self.counts(),baseline);self.assertEqual(access_count(),9)
        with self.db.session() as s:
            self.assertEqual(s.query(ReportRow).count(),0);self.assertEqual(s.query(ReportAuditRow).count(),1)
            self.assertIsNone(s.execute(text("SELECT name FROM sqlite_master WHERE name='frozen_sentence_bindings_v1'")).first())
            rows=s.scalars(select(CustodyEventRow).order_by(CustodyEventRow.seq)).all()
            accesses=[r for r in rows if r.kind=='Access']
            self.assertEqual([(r.evidence_id,r.sha256) for r in accesses],[(p['evidenceId'],p['sourceSha256']) for p in pins]*4+[(pins[0]['evidenceId'],pins[0]['sourceSha256'])])
            self.assertEqual(accesses[-1].operator,subject)
            self.assertTrue(audit.verify_chain([r.line for r in rows])['valid'])
            self.assertTrue(audit.verify_chain(audit.all_lines(s,self.cid))['valid'])
        self.assertNotIn('PRIVATE',json.dumps(out));self.assertNotIn('正文',json.dumps(out,ensure_ascii=False))
        result={'result':'PASS','caseId':self.cid,'frames':frames,'prepareAccessAdded':1,'finalAccess':9,'custodyRows':baseline[1],'auditRows':baseline[2],'reportRows':0,'snapshotFixtureRows':1,'bindingTableExists':False,'denialsNoExtraWrites':True,'sameRegisteredPins':True,'http':False,'realLogin':False,'generatorExecuted':False}
if not sys.flags.isolated:raise SystemExit('Use -I')
with tempfile.TemporaryDirectory(prefix='joined-source-') as folder:
 source=pilot['base']['materialize'](Path(folder),ref=pilot['REF'],paths=pilot['BASE'])
 for path in pilot['NEW']:
  data=(ROOT/path).read_bytes()
  assert data==subprocess.check_output(['git','show',PREPARE_REF+':'+path],cwd=ROOT)
  target=source/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 ok=pilot['base']['run'](source,extra_cases=(Joined,),allowed_paths=pilot['BASE']+pilot['NEW'])
if ok:print(json.dumps(result))
raise SystemExit(0 if ok else 1)
