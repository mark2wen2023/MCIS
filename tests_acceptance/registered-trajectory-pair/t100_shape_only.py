"""One existing storage-shape test, A-only prerequisite. No legacy suite dispatch."""
import os
os.environ['GIT_NO_LAZY_FETCH'] = '1'
import hashlib
import importlib.abc
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
PARENT = '540f9343c307385fb0e6d537119348c15a9947d0'
TRACKS = '2048c60fd6650c6f2c99a76a16be463a3895655d'
HERE = Path(__file__).resolve().parent


def fixed(ref, path):
    cmd = ['git', '-C', str(ROOT)]
    entry = subprocess.check_output(cmd + ['ls-tree', ref, '--', path]).decode().split()
    assert len(entry) == 4 and entry[:2] == ['100644', 'blob'] and entry[3] == path
    data = subprocess.check_output(cmd + ['show', ref + ':' + path])
    assert hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest() == entry[2]
    return data


def main():
    if not sys.flags.isolated or sys.flags.optimize or len(sys.argv) != 1:
        raise SystemExit('Use existing Python -I -B, without arguments or -O')
    # Check the entire existing Python test chain before ordinary runpy loading.
    for name in ('snapshot_reader_shape.py', 'raw_fixture_prepare.py', 'pilot_prepare.py', 'business.py'):
        assert (HERE / name).read_bytes() == fixed(PARENT, 'tests_acceptance/registered-trajectory-pair/' + name)
    existing = runpy.run_path(str(HERE / 'snapshot_reader_shape.py'))
    base, pilot = existing['base'], existing['pilot']
    assert existing['OLD'] is False
    paths = tuple(p for p in pilot['BASE'] if not p.startswith('tests_acceptance/'))
    paths += pilot['NEW']
    with tempfile.TemporaryDirectory(prefix='w16-t100-shape-only-') as folder:
        source = Path(folder)
        for path in paths:
            data = fixed(PARENT, path)
            if path not in pilot['NEW']:
                assert data == fixed(pilot['REF'], path)
            target = source / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        allowed = set(paths)
        names = set()
        for path in paths:
            if path.startswith('service/') and path.endswith('.py'):
                name = path[len('service/'):-3].replace('/', '.')
                names.add(name.removesuffix('.__init__'))
        assert not any(n == 'mcis_service' or n.startswith('mcis_service.') for n in sys.modules)
        class PinnedOnly(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if (fullname == 'mcis_service' or fullname.startswith('mcis_service.')) and fullname not in names:
                    raise ImportError('Outside pinned product whitelist: ' + fullname)
        sys.meta_path.insert(0, PinnedOnly())
        sys.path.insert(0, str(source / 'service'))
        from sqlalchemy import select, text
        from mcis_service.db import Database, Base, put_doc, APPEND_ONLY_TABLES
        from mcis_service.common.context import Ctx
        from mcis_service.common import contracts
        from mcis_service.cases.models import CaseRow
        from mcis_service.evidence.models import EvidenceRow, CustodyEventRow
        from mcis_service.audit.models import AuditEventRow
        from mcis_service.redaction.models import AccessPolicyRow
        from mcis_service.redaction.policy import default_policy
        from mcis_service.working_records_archive.models import ArchiveImportHistoryRow
        from mcis_service.track_history.models import LocalReceipt

        class OneShape(existing['StorageShape'], unittest.TestCase):
            # Inherit the existing test method and Raw.register unchanged.
            def setUp(self):
                self.cid = 'SYN-XREPO-001'
                self.db = Database('sqlite:///' + str(source / 'fresh.sqlite'))
                self.addCleanup(self.db.engine.dispose)
                models = (CaseRow, EvidenceRow, CustodyEventRow, AuditEventRow,
                          AccessPolicyRow, ArchiveImportHistoryRow, LocalReceipt)
                Base.metadata.create_all(self.db.engine, tables=[m.__table__ for m in models])
                with self.db.engine.begin() as c:
                    for table in APPEND_ONLY_TABLES:
                        for operation in ('UPDATE', 'DELETE'):
                            c.execute(text(f"CREATE TRIGGER IF NOT EXISTS {table}_no_{operation.lower()} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END;"))
                blobs = source / 'blobs'; blobs.mkdir()
                state = SimpleNamespace(db=self.db, settings=SimpleNamespace(blob_dir=blobs))
                self.ctx = Ctx(role='Investigator', operator='Synthetic prerequisite',
                               request=SimpleNamespace(app=SimpleNamespace(state=state)))
                case = {'caseId': self.cid, 'schemaVersion': '1.0.0', 'title': 'Synthetic T100 prerequisite',
                        'accidentType': 'Synthetic', 'isFictionalDemo': True,
                        'caseEpochUtc': '2026-02-01T12:00:00Z', 'incidentTimeUtc': '2026-02-01T12:00:00Z',
                        'incidentLocation': {'lonDeg': -130, 'latDeg': -30}, 'displayTimeZoneOffsetMinutes': 0}
                contracts.validate('case', case)
                # Explicit initial scaffold, not a policy rewrite or a real account.
                with self.db.session() as s:
                    put_doc(s, CaseRow, self.cid, self.cid, case)
                    put_doc(s, AccessPolicyRow, self.cid, 'policy', default_policy())
                raw = fixed(TRACKS, 'tests_acceptance/shared-trajectory-cross-repo-expanded/vessel-a.json')
                doc = json.loads(raw)
                self.assertEqual(doc['caseId'], self.cid)
                self.assertEqual(doc['vessel']['vesselId'], 'SYN-VESSEL-A')
                point = doc['points'][7]
                self.assertEqual(point['pointId'], 'A-t100')
                self.assertEqual(point['time']['alignedUtc'], '2026-02-01T12:01:40.000Z')
                self.assertIsNone(point['headingDeg']['value'])
                self.pins = [self.register(doc)]  # Original normal registration, exact Git bytes.
                self.assertEqual(self.pins[0]['sourceSha256'], hashlib.sha256(raw).hexdigest())
                self.assertEqual(self.counts(), (1, 1, 1))

            def counts(self):
                with self.db.session() as s:
                    return tuple(s.query(m).count() for m in (EvidenceRow, CustodyEventRow, AuditEventRow))

            def tearDown(self):
                # Additional observations; the inherited test checks each rejection delta.
                from mcis_service.reports.models import ReportRow, ReportAuditRow
                with self.db.session() as s:
                    policy = s.scalars(select(AccessPolicyRow)).one()
                    self.assertEqual(policy.doc, default_policy())
                    self.assertEqual(s.query(CaseRow).count(), 1)
                    self.assertEqual(s.query(ReportRow).count(), 0)
                    self.assertEqual(s.query(ReportAuditRow).count(), 4)
                    access = s.query(CustodyEventRow).filter_by(kind='Access').count()
                    self.assertEqual(access, 1)
                    self.assertEqual(self.counts(), (1, 2, 3))
                print(json.dumps({'scope': 'A-t100-only', 'outcome': 'UNSAVED',
                                  'registration': {'custody': 1, 'audit': 1},
                                  'hostSnapshotFixture': {'rows': 4, 'generationAudit': 1},
                                  'prepare': {'access': access, 'audit': 1},
                                  'totals': {'evidence': 1, 'custody': 2, 'audit': 3},
                                  'policyUnchanged': True, 'reportRows': 0,
                                  'generatorExecuted': False, 'reopenVerified': False}))

        suite = unittest.TestSuite([OneShape('test_absent_identity_and_rejections')])
        assert suite.countTestCases() == 1
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        for name, module in tuple(sys.modules.items()):
            if name == 'mcis_service' or name.startswith('mcis_service.'):
                path = Path(module.__file__).resolve()
                assert path.is_relative_to(source) and str(path.relative_to(source)) in allowed
        return result.wasSuccessful()


if __name__ == '__main__':
    raise SystemExit(0 if main() else 1)
