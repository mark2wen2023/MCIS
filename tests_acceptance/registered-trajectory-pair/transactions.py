"""Real temporary SQLite + extracted project transaction primitives.

No app/model/registry import. Receipt/policy/container remain synthetic stubs.
Only synthetic_access_probe is created; this is NOT custody/permission acceptance.
"""
import ast
from contextlib import contextmanager
from pathlib import Path
import runpy
import subprocess
import tempfile
import threading
import types
from typing import Iterator
import unittest

from sqlalchemy import create_engine, event, text as sql
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[2]
BASE = 'bdb0c6089c09c73e01d1da4b09cd4e748e92d157'
base_test = runpy.run_path(str(Path(__file__).with_name('check.py')))


def fixed(path):
    original = subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT,text=True)
    current = subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT,text=True)
    if current != original:
        raise RuntimeError('Transaction dependency changed; review required')
    return original


def extract(source, name, ns):
    tree=ast.parse(source)
    node=next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<fixed-production-ast>','exec'),ns)


class Transactions(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='mcis-pair-transaction-')
        ns=dict(create_engine=create_engine,event=event,sessionmaker=sessionmaker,
                contextmanager=contextmanager,Engine=Engine,Session=Session,Iterator=Iterator)
        extract(fixed('service/mcis_service/db.py'),'Database',ns)
        self.db=ns['Database']('sqlite:///'+str(Path(self.temporary.name)/'probe.sqlite'))
        with self.db.engine.begin() as c:
            c.execute(sql('CREATE TABLE synthetic_access_probe (evidence TEXT NOT NULL)'))
        self.fixture=base_test['Checks'](); self.fixture.setUp()
        self.ns=self.fixture.ns
        self.fixture.ctx.db=self.db
        extract(fixed('service/mcis_service/reports/access.py'),'begin',dict_ns := {'threading':threading})
        self.ns['begin']=dict_ns['begin']
        extract(fixed('service/mcis_service/evidence_intake/parser.py'),'text',self.ns)
        self.ns['WRITE_LOCK']=threading.RLock()
        base_test['compile_functions']((ROOT/base_test['PAIR']).read_text(), {'_load_registered_pair'}, self.ns)
        def authorize(ctx,s,cid):
            if not s.connection().connection.driver_connection.in_transaction:
                raise AssertionError('BEGIN must precede source/policy read')
            self.fixture.calls.append(('authorize',cid))
        def audit(s,**kw):
            s.execute(sql('INSERT INTO synthetic_access_probe(evidence) VALUES (:e)'),{'e':kw['evidence_id']})
            self.fixture.calls.append(('audit',kw['evidence_id']))
        self.ns['authorize']=authorize
        self.ns['evidence']=types.SimpleNamespace(append_custody=audit)

    def tearDown(self):
        self.db.engine.dispose()
        self.temporary.cleanup()

    def call(self):
        return self.ns['_load_registered_pair'](self.fixture.ctx,self.fixture.cid,self.fixture.pins,'synthetic read')

    def count(self):
        with self.db.engine.connect() as c:
            return c.execute(sql('SELECT COUNT(*) FROM synthetic_access_probe')).scalar_one()

    def test_success_delivered_after_commit(self):
        result=self.call()
        self.assertEqual(len(result),2)
        self.assertEqual(self.count(),2)

    def test_second_read_failure_rolls_back_first_access(self):
        self.fixture.fail_digest=self.fixture.pins[1]['requestDigest']
        with self.assertRaises(PermissionError): self.call()
        self.assertTrue(any(k=='audit' for k,v in self.fixture.calls))
        self.assertEqual(self.count(),0)

    def test_second_validation_failure_rolls_back_both_accesses(self):
        self.fixture.pins[1]=self.fixture.put(1,{})
        with self.assertRaisesRegex(ValueError,'TRAJECTORY_INVALID'): self.call()
        self.assertEqual(sum(k=='audit' for k,v in self.fixture.calls),2)
        self.assertEqual(self.count(),0)

    def test_before_commit_exception_no_delivery_and_rollback(self):
        class FailingCommit(Session):
            def commit(self): raise RuntimeError('synthetic before commit')
        self.db.SessionLocal=sessionmaker(bind=self.db.engine,class_=FailingCommit)
        with self.assertRaisesRegex(RuntimeError,'before commit'): self.call()
        self.assertEqual(self.count(),0)

    def test_after_commit_exception_no_delivery_not_claimed_rollback(self):
        class AmbiguousCommit(Session):
            def commit(self):
                super().commit()
                raise RuntimeError('synthetic after commit')
        self.db.SessionLocal=sessionmaker(bind=self.db.engine,class_=AmbiguousCommit)
        with self.assertRaisesRegex(RuntimeError,'after commit'): self.call()
        # Commit acknowledgement failure cannot undo a completed commit. No
        # successful pair is delivered; both probes exist, never one-half.
        self.assertEqual(self.count(),2)

    def test_purpose_rejected_before_database_work(self):
        with self.assertRaises(ValueError):
            self.ns['_load_registered_pair'](self.fixture.ctx,self.fixture.cid,self.fixture.pins,'')
        self.assertEqual(self.fixture.calls,[])
        self.assertEqual(self.count(),0)

if __name__=='__main__': unittest.main(verbosity=2)
