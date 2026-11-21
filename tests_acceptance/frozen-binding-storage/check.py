"""Actual SQLite storage + real ReportAuditRow/ReportRow, no report service.
Authorization/media/generation sources remain the existing handmade Scope.
"""
import ast
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT=Path(__file__).resolve().parents[2]
BASE='0514755778127efa33c0b47b0fcb00e617cb753d'
FILES=['__init__.py','db.py','common/__init__.py','common/timeutil.py','reports/__init__.py','reports/models.py',
       'reports/sentence_binding.py','reports/generation_snapshot.py','reports/audio_reference_range.py',
       'reports/media_reference.py','reports/media_reference_reader.py']


def copy_sources(root):
    for name in FILES:
        path='service/mcis_service/'+name
        raw=subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT)
        if subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT)!=raw:
            raise RuntimeError('Fixed dependency changed')
        target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    path='service/mcis_service/reports/sentence_binding_store.py'
    (root/path).write_bytes((ROOT/path).read_bytes())


def run(root):
    sys.path.insert(0,str(root/'service'))
    from sqlalchemy import text,inspect
    from sqlalchemy.exc import IntegrityError
    from mcis_service.db import Database,Base,put_doc
    from mcis_service.reports.models import ReportAuditRow,ReportRow
    from mcis_service.reports.sentence_binding_store import SqliteBindingStore,_initialize_binding_storage,TABLE
    from mcis_service.reports.sentence_binding import BindingUnavailable,BindingCorrupt
    synthetic=runpy.run_path(str(ROOT/'tests_acceptance/frozen-sentence-binding/check.py'))
    Scope,prepare,decide=synthetic['Scope'],synthetic['prepare'],synthetic['decide']
    # Execute only the existing archive table-rejection function, with actual
    # SQLAlchemy inspect/session. Never import archive/service or export a case.
    archive=ast.parse(subprocess.check_output(['git','show',BASE+':service/mcis_service/working_records_archive/service.py'],cwd=ROOT,text=True))
    nodes=[n for n in archive.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('ALLOWED_TABLES','GLOBALS') for t in n.targets)]
    nodes += [n for n in archive.body if isinstance(n,ast.FunctionDef) and n.name=='reject_unsupported_tables']
    def fail(*args):raise RuntimeError('archive rejects unsupported state')
    archive_ns={'inspect':inspect,'sqltext':text,'fail':fail}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<production-archive-guard>','exec'),archive_ns)

    class Checks(unittest.TestCase):
        def setUp(self):
            self.temp=tempfile.TemporaryDirectory(dir=root);self.addCleanup(self.temp.cleanup)
            self.url='sqlite:///'+str(Path(self.temp.name)/'new.sqlite')
            self.db=Database(self.url);self.addCleanup(self.db.engine.dispose)
            Base.metadata.create_all(self.db.engine,tables=[ReportAuditRow.__table__,ReportRow.__table__])
            self.scope=Scope();self.key=self.scope.key;self.raw=prepare(scope=self.scope,key=self.key)
            with self.db.session() as s:
                put_doc(s,ReportAuditRow,self.key[0],self.key[1],self.scope.generation['snapshot'])
                put_doc(s,ReportRow,self.key[0],self.scope.report['reportId'],self.scope.report)
            _initialize_binding_storage(self.db.engine,enabled=True)

        def store(self,s,cid=None):return SqliteBindingStore(s,cid or self.key[0],enabled=True)
        def save(self,raw=None,key=None):
            with self.db.session() as s:return self.store(s).insert_if_absent(key or self.key,self.raw if raw is None else raw)

        def test_disabled_and_schema_reopen(self):
            with self.assertRaisesRegex(BindingUnavailable,'disabled'):_initialize_binding_storage(self.db.engine)
            with self.db.session() as s:
                with self.assertRaisesRegex(BindingUnavailable,'disabled'):SqliteBindingStore(s,self.key[0])
            self.save();_initialize_binding_storage(self.db.engine,enabled=True)
            # Dispose/reopen an actual engine, not merely refresh the UI/session.
            self.db.engine.dispose();self.db=Database(self.url);self.addCleanup(self.db.engine.dispose)
            with self.db.session() as s:self.assertEqual(self.store(s).get(self.key),self.raw)

        def test_insert_idempotence_conflict_and_original_text_absent(self):
            self.assertEqual(self.save(),self.raw);self.assertEqual(self.save(),self.raw)
            changed=json.loads(self.raw);changed['pin']['revision']=2
            changed=synthetic['b']['_bytes'](changed)
            stored=self.save(changed)
            with self.assertRaises(synthetic['b']['BindingConflict']):decide(key=self.key,proposed=changed,existing=stored)
            self.assertEqual(stored,self.raw)
            self.assertNotIn(b'Synthetic frozen sentence',stored)

        def test_sql_immutable_and_cross_case_parent(self):
            self.save()
            for sql in (f'UPDATE {TABLE} SET payload=payload',f'DELETE FROM {TABLE}'):
                with self.assertRaises(IntegrityError):
                    with self.db.session() as s:s.execute(text(sql))
            with self.db.session() as s:
                with self.assertRaisesRegex(BindingUnavailable,'case_mismatch'):self.store(s,'OTHER').get(self.key)
            altered=json.loads(self.raw);key=('OTHER',*self.key[1:]);altered['key']=list(key);altered['pin']['caseId']='OTHER'
            with self.assertRaises(IntegrityError):
                with self.db.session() as s:self.store(s,'OTHER').insert_if_absent(key,synthetic['b']['_bytes'](altered))
            broken=json.loads(self.raw);broken['pin']['caseId']='OTHER'
            with self.assertRaisesRegex(BindingCorrupt,'pin_key'):self.save(synthetic['b']['_bytes'](broken))

        def test_transaction_rollback(self):
            with self.assertRaisesRegex(RuntimeError,'synthetic abort'):
                with self.db.session() as s:
                    self.store(s).insert_if_absent(self.key,self.raw)
                    raise RuntimeError('synthetic abort')
            with self.db.session() as s:self.assertIsNone(self.store(s).get(self.key))

        def test_two_connections_atomic_winner(self):
            other=json.loads(self.raw);other['sentenceSha256']='f'*64;other=synthetic['b']['_bytes'](other)
            gate=threading.Barrier(2)
            def insert(raw):
                with self.db.session() as s:
                    store=self.store(s);gate.wait(timeout=5)
                    return store.insert_if_absent(self.key,raw)
            with ThreadPoolExecutor(2) as pool:results=list(pool.map(insert,[self.raw,other]))
            self.assertEqual(results[0],results[1]);self.assertIn(results[0],(self.raw,other))
            with self.db.session() as s:self.assertEqual(s.execute(text(f'SELECT COUNT(*) FROM {TABLE}')).scalar_one(),1)

        def test_new_generation_separate_and_parent_delete_restricted(self):
            self.save();later=Scope()
            later.report=deepcopy(self.scope.report)
            later.report.update(reportId='RPT-'+'2'*20,version=2,parentReportId=self.scope.report['reportId'])
            later.generation=synthetic['reports']['inputs'](later.report,2,previous=self.scope.report)
            later.key=(self.key[0],later.generation['snapshot']['snapshotId'],*self.key[2:])
            later.pin.update(generationSnapshotId=later.key[1],auditSeq=2,reportId=later.report['reportId'],version=2)
            newraw=prepare(scope=later,key=later.key)
            with self.db.session() as s:
                put_doc(s,ReportAuditRow,later.key[0],later.key[1],later.generation['snapshot'])
                s.flush()
                self.assertEqual(self.store(s).insert_if_absent(later.key,newraw),newraw)
                self.assertEqual(self.store(s).get(self.key),self.raw)
            with self.assertRaises(IntegrityError):
                with self.db.session() as s:
                    s.execute(text('DELETE FROM report_operation_snapshots WHERE case_id=:cid AND key=:sid'),{'cid':self.key[0],'sid':self.key[1]})

        def test_archive_default_registration_and_drift(self):
            self.assertNotIn(TABLE,Base.metadata.tables)
            self.save()
            with self.db.session() as s:
                with self.assertRaisesRegex(RuntimeError,'archive rejects'):archive_ns['reject_unsupported_tables'](s,self.key[0])
                archive_ns['reject_unsupported_tables'](s,'OTHER')
            with self.db.engine.begin() as c:c.exec_driver_sql(f'DROP TRIGGER {TABLE}_no_update')
            with self.assertRaisesRegex(BindingUnavailable,'schema_unreviewed'):_initialize_binding_storage(self.db.engine,enabled=True)

        def test_current_report_edit_and_revalidation_protocol(self):
            self.save()
            with self.db.session() as s:
                doc=deepcopy(self.scope.report);doc['title']='Synthetic current edit'
                put_doc(s,ReportRow,self.key[0],doc['reportId'],doc)
            # Handmade guards demonstrate required calling protocol only, not
            # real production permission checks or a unified authorized view.
            self.scope.denied='media'
            with self.assertRaises(PermissionError):prepare(scope=self.scope,key=self.key)
            self.scope.denied=None
            fresh=prepare(scope=self.scope,key=self.key)
            with self.db.session() as s:
                self.assertEqual(decide(key=self.key,proposed=fresh,existing=self.store(s).get(self.key)),'identical')

    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    forbidden=('mcis_service.main','mcis_service.models_registry','mcis_service.reports.service')
    if any(n in sys.modules for n in forbidden):raise RuntimeError('Forbidden business initialization')
    return result.wasSuccessful()

if __name__=='__main__':
    if not sys.flags.isolated:raise SystemExit('Use existing Python -I; no installation')
    with tempfile.TemporaryDirectory(prefix='mcis-binding-store-') as folder:
        root=Path(folder);copy_sources(root);ok=run(root)
    raise SystemExit(0 if ok else 1)
