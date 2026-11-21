"""Real archive build refusal on synthetic SQLite; no service/app/HTTP.

No replacement policy/build functions. Supplied role is synthetic test input,
NOT authenticated identity. Only the unsupported-state refusal path is tested.
"""
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[2]
BASE='73a1fa7fc75c03a71c035925873b0a1af74b7d27'
# Exact source inputs, never enumerate/copy data or seed directories.
MODULES='''config common/context common/contracts common/csjson
reports/access interviews/access redaction/gateway redaction/policy redaction/models
working_records_archive/service working_records_archive/validation working_records_archive/models
cases/models interviews/models evidence/models evidence/service manual_interviews/models
package/mcase package_intake/router package_intake/parser evidence_intake/parser
agents/models audit/models audit/service colreg/models environment/models environment/service
recommendations/models timeline/models'''.split()
PACKAGES='''agents audit cases colreg environment evidence interviews manual_interviews
package package_intake redaction recommendations timeline working_records_archive evidence_intake'''.split()


def fixed(path):
    value=subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT)
    if subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT)!=value:
        raise RuntimeError('Reviewed source changed')
    return value


def run(root):
    previous=runpy.run_path(str(ROOT/'tests_acceptance/frozen-binding-storage/check.py'))
    previous['copy_sources'](root)
    store='service/mcis_service/reports/sentence_binding_store.py'
    if (root/store).read_bytes()!=fixed(store):raise RuntimeError('Storage differs from reviewed base')
    for name in MODULES+[p+'/__init__' for p in PACKAGES]:
        path='service/mcis_service/'+name+'.py'
        target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(fixed(path))
    sys.path.insert(0,str(root/'service'))
    from fastapi import HTTPException
    from sqlalchemy import text
    from mcis_service.db import Database,Base,put_doc
    from mcis_service.reports.models import ReportRow,ReportAuditRow
    from mcis_service.cases.models import CaseRow
    from mcis_service.evidence.models import EvidenceRow,CustodyEventRow
    from mcis_service.interviews.models import InterviewRow
    from mcis_service.audit.models import AuditEventRow
    from mcis_service.redaction.models import AccessPolicyRow
    from mcis_service.redaction.policy import default_policy
    from mcis_service.reports.sentence_binding_store import SqliteBindingStore,_initialize_binding_storage
    from mcis_service.working_records_archive.service import build
    pure=runpy.run_path(str(ROOT/'tests_acceptance/frozen-sentence-binding/check.py'))

    class Check(unittest.TestCase):
        def setUp(self):
            self.temp=tempfile.TemporaryDirectory(dir=root);self.addCleanup(self.temp.cleanup)
            self.folder=Path(self.temp.name);self.blobs=self.folder/'empty-blobs';self.blobs.mkdir()
            self.db=Database('sqlite:///'+str(self.folder/'synthetic.sqlite'));self.addCleanup(self.db.engine.dispose)
            tables=[m.__table__ for m in (ReportRow,ReportAuditRow,CaseRow,EvidenceRow,CustodyEventRow,InterviewRow,AuditEventRow,AccessPolicyRow)]
            Base.metadata.create_all(self.db.engine,tables=tables)
            self.scope=pure['Scope']();self.key=self.scope.key
            self.raw=pure['prepare'](scope=self.scope,key=self.key)
            with self.db.session() as s:
                put_doc(s,ReportAuditRow,self.key[0],self.key[1],self.scope.generation['snapshot'])
                put_doc(s,ReportRow,self.key[0],self.scope.report['reportId'],self.scope.report)
                # Explicit policy fixture, not the implicit default at read time.
                put_doc(s,AccessPolicyRow,self.key[0],'policy',default_policy())
            _initialize_binding_storage(self.db.engine,enabled=True)
            with self.db.session() as s:SqliteBindingStore(s,self.key[0],enabled=True).insert_if_absent(self.key,self.raw)

        def state(self):
            with self.db.engine.connect() as c:
                # SQL dump of only our generated test database, never a real DB.
                return tuple(c.connection.driver_connection.iterdump())

        def refusal(self,role,code,case=None,mutate=False):
            before=self.state();result=None
            # Catch outside Database.session so actual exception triggers rollback.
            try:
                with self.db.session() as s:
                    if mutate:
                        doc=dict(self.scope.report);doc['title']='synthetic pending change'
                        put_doc(s,ReportRow,self.key[0],doc['reportId'],doc)
                    result=build(s,self.blobs,SimpleNamespace(role=role),case or self.key[0])
            except HTTPException as exc:
                self.assertEqual(exc.detail['code'],code)
                if code=='WORKING_ARCHIVE_INVALID':
                    self.assertEqual(exc.detail['message'],'存在未支持的业务状态，不能部分归档')
                self.assertEqual(exc.status_code,403 if code=='FORBIDDEN' else 404 if code=='CASE_NOT_FOUND' else 422)
            else:self.fail('Archive unexpectedly returned')
            self.assertIsNone(result)
            self.assertEqual(self.state(),before)
            self.assertEqual(list(self.blobs.rglob('*')),[])
            with self.db.session() as s:
                self.assertEqual(SqliteBindingStore(s,self.key[0],enabled=True).get(self.key),self.raw)
                for table in ('audit_events','custody_events'):
                    self.assertEqual(s.execute(text('SELECT COUNT(*) FROM '+table)).scalar_one(),0)

        def test_real_build_rejects_binding_without_artifact(self):
            self.refusal('LeadInvestigator','WORKING_ARCHIVE_INVALID')
        def test_real_policy_precedes_unsupported_state(self):
            self.refusal('Public','FORBIDDEN')
        def test_existing_investigator_policy_not_relaxed(self):
            self.refusal('Investigator','FORBIDDEN')
        def test_refusal_rolls_back_pending_report_change(self):
            self.refusal('LeadInvestigator','WORKING_ARCHIVE_INVALID',mutate=True)
        def test_other_case_not_blocked_by_this_binding(self):
            # No export success claimed: other case has no CaseRow and returns404.
            self.refusal('LeadInvestigator','CASE_NOT_FOUND',case='SYN-OTHER')

    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Check))
    forbidden=('mcis_service.main','mcis_service.models_registry','mcis_service.reports.service','mcis_service.audio_review.app')
    if any(n in sys.modules for n in forbidden):raise RuntimeError('Forbidden initialization')
    loaded=[m for n,m in sys.modules.items() if n=='mcis_service' or n.startswith('mcis_service.')]
    for m in loaded:
        if not Path(m.__file__).resolve().is_relative_to(root):raise RuntimeError('Module escaped source copy')
    return result.wasSuccessful()

if __name__=='__main__':
    if not sys.flags.isolated:raise SystemExit('Use reviewed existing Python -I')
    with tempfile.TemporaryDirectory(prefix='mcis-binding-archive-') as folder:ok=run(Path(folder))
    raise SystemExit(0 if ok else 1)
