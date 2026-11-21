"""Actual pilot session verification + temporary SQLite; no app/login/HTTP."""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import runpy
import secrets
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
base=runpy.run_path(str(Path(__file__).with_name('business.py')))
REF='db90fdf73de7bd26ba75819f0102fc03d0789faf'
BASE=base['PATHS']+('service/mcis_service/trajectory_exchange/registered_query.py','contracts/schemas/report.schema.json')
NEW=tuple('service/mcis_service/'+p for p in ['common/local_review_pilot.py','common/verified_case_context.py','reports/generation_snapshot.py','reports/pilot_trajectory_prepare.py'])

class Pilot:
    def test_scoped_prepare_and_denials(self):
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
        before=self.counts()
        result=prepare()
        self.assertEqual(result['status'],'proposed_reference_pending_human_review')
        self.assertEqual(result['locator'],{'jsonPointer':'/points/7'})
        self.assertEqual(result['original'],self.pins[0]);self.assertFalse(result['saved'])
        self.assertNotIn('PRIVATE',json.dumps(result));self.assertNotIn('正文',json.dumps(result,ensure_ascii=False));self.assertNotIn('position',result)
        self.assertEqual(self.counts(),(before[0],before[1]+1,before[2]+1))
        baseline=self.counts()
        with self.assertRaises(PrepareUnavailable):prepare(_credential='')
        with self.assertRaises(PrepareUnavailable):prepare(pin={**self.pins[0],'sourceSha256':'f'*64})
        self.assertEqual(self.counts(),baseline)  # existing rollback policy after unsuccessful assembly
        # Real Session commit failure injection: transaction body executes, no result escapes.
        from sqlalchemy import event
        from sqlalchemy.orm import Session
        def fail_commit(session):
            raise RuntimeError('synthetic commit rejection')
        event.listen(Session,'before_commit',fail_commit)
        try:
            with self.assertRaisesRegex(RuntimeError,'synthetic commit rejection'):prepare()
        finally:
            event.remove(Session,'before_commit',fail_commit)
        self.assertEqual(self.counts(),baseline)
        # Expire between original read and final grant check, without replacing verifier.
        ticks=iter([10.0,10.0,20.0,20.0])
        expiring=PilotSessions({digest:entry},clock=lambda:next(ticks),report_reference_subject=subject)
        with self.assertRaises(PrepareUnavailable):prepare(sessions=expiring)
        self.assertEqual(self.counts(),baseline)
        for patch in [dict(enabled=False),dict(subject='other'),dict(key=('SYN-OTHER',sid,'synthetic-section','synthetic-sentence')),dict(pin={**self.pins[0],'caseId':'SYN-OTHER'})]:
            with self.subTest(patch=list(patch)),self.assertRaises(PrepareUnavailable):prepare(**patch)
            self.assertEqual(self.counts(),baseline)
        missing=PilotSessions({digest:PilotSession(subject,'Investigator',20.0,frozenset([(self.cid,'evidence.original.access')]))},clock=lambda:clock[0])
        with self.assertRaises(PrepareUnavailable):prepare(sessions=missing)
        clock[0]=20.0
        with self.assertRaises(PrepareUnavailable):prepare()
        clock[0]=10.0;sessions.revoke(digest)
        with self.assertRaises(PrepareUnavailable):prepare()
        sessions=PilotSessions({digest:entry},clock=lambda:clock[0],report_reference_subject=subject)
        for category in ['report_draft','evidence_meta']:
            policy=default_policy();policy['matrix']['LeadInvestigator'][category]='Deny'
            with self.db.session() as s:put_doc(s,AccessPolicyRow,self.cid,'policy',policy)
            with self.subTest(category=category),self.assertRaises(HTTPException):prepare()
            self.assertEqual(self.counts(),baseline)
        with self.db.session() as s:
            put_doc(s,AccessPolicyRow,self.cid,'policy',default_policy())
        # No request/header enters prepare; hostile legacy transport headers ignored.
        self.ctx.request.headers={'X-MCIS-Role':'LeadInvestigator','X-MCIS-Operator':'forged'}
        for role in ('Investigator','Public'):
            bad_role=PilotSessions({digest:PilotSession(subject,role,20.0,grants)},clock=lambda:clock[0],report_reference_subject=subject)
            with self.subTest(role=role),self.assertRaises(HTTPException):prepare(sessions=bad_role)
        self.assertEqual(self.counts(),baseline)
        with self.db.session() as s:
            self.assertEqual(s.query(ReportRow).count(),0)
            self.assertEqual(s.query(ReportAuditRow).count(),1)
            self.assertEqual(s.scalars(select(ReportAuditRow)).one().doc,snap)
            self.assertIsNone(s.execute(text("SELECT name FROM sqlite_master WHERE name='frozen_sentence_bindings_v1'")).first())
            self.assertTrue(audit.verify_chain(audit.all_lines(s,self.cid))['valid'])
            custody=s.scalars(select(CustodyEventRow).where(CustodyEventRow.case_id==self.cid).order_by(CustodyEventRow.seq)).all()
            self.assertTrue(audit.verify_chain([r.line for r in custody])['valid'])
            access=[r for r in custody if r.kind=='Access']
            self.assertEqual(len(access),1)
            self.assertEqual(access[0].operator,subject)

if __name__=='__main__':
    if not sys.flags.isolated:raise SystemExit('Use existing Python -I')
    with tempfile.TemporaryDirectory(prefix='pilot-reference-') as folder:
        source=base['materialize'](Path(folder),ref=REF,paths=BASE)
        for p in NEW:
            target=source/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/p).read_bytes())
        ok=base['run'](source,extra_cases=(Pilot,),allowed_paths=BASE+NEW)
    raise SystemExit(0 if ok else 1)
