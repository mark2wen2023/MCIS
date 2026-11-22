"""Local synthetic acceptance only. Real intake/read; test-host identity, no login."""
import os
os.environ['GIT_NO_LAZY_FETCH'] = '1'
import asyncio
import base64
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = 'db90fdf73de7bd26ba75819f0102fc03d0789faf'
HARNESS = 'c7f933d9d5a3fea6c4f3d706fe1f091475c3eb24'
DRAFT = '194ee6be7a4b31c0e23b5615b5d60cd9b0667ed0'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def copy_fixed(ref, path, destination):
    entry = git('ls-tree', ref, '--', path).decode().split()
    if len(entry) != 4 or entry[:2] != ['100644', 'blob'] or entry[3] != path:
        raise RuntimeError('Expected fixed ordinary blob')
    raw = git('show', ref + ':' + path)
    if hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest() != entry[2]:
        raise RuntimeError('Git bytes mismatch')
    target = destination / path
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(raw)
    return target


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def run(source, allowed, fixture):
    sys.path.insert(0, str(source / 'service'))
    from fastapi import HTTPException
    from sqlalchemy import select, text
    from mcis_service.db import Database, Base, put_doc, APPEND_ONLY_TABLES, WRITE_LOCK
    from mcis_service.common.context import Ctx
    from mcis_service.common import contracts
    from mcis_service.cases.models import CaseRow
    from mcis_service.evidence.models import EvidenceRow, CustodyEventRow
    from mcis_service.audit.models import AuditEventRow
    from mcis_service.audit.service import verify_chain, all_lines
    from mcis_service.redaction.models import AccessPolicyRow
    from mcis_service.redaction.policy import default_policy
    from mcis_service.working_records_archive.models import ArchiveImportHistoryRow
    from mcis_service.track_history.models import LocalReceipt
    from mcis_service.evidence_intake import router as intake
    from mcis_service.reports.access import begin

    class Body:
        headers = {'content-type': 'application/json'}
        def __init__(self, value): self.raw = json.dumps(value).encode()
        async def stream(self): yield self.raw

    class Checks(unittest.TestCase):
        def test_registered_bytes_to_unsaved_draft(self):
            with tempfile.TemporaryDirectory(dir=source) as folder:
                root = Path(folder); blobs = root / 'blobs'; blobs.mkdir()
                db = Database('sqlite:///' + str(root / 'fresh.sqlite'))
                self.addCleanup(db.engine.dispose)
                models = (CaseRow, EvidenceRow, CustodyEventRow, AuditEventRow,
                          AccessPolicyRow, ArchiveImportHistoryRow, LocalReceipt)
                Base.metadata.create_all(db.engine, tables=[m.__table__ for m in models])
                with db.engine.begin() as c:
                    for table in APPEND_ONLY_TABLES:
                        for op in ('UPDATE', 'DELETE'):
                            c.execute(text(f"CREATE TRIGGER IF NOT EXISTS {table}_no_{op.lower()} BEFORE {op} ON {table} "
                                           f"BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END;"))
                state = SimpleNamespace(db=db, settings=SimpleNamespace(blob_dir=blobs))
                request = SimpleNamespace(app=SimpleNamespace(state=state))
                # Same explicit synthetic Ctx convention as pinned business.py, NOT session/login.
                ctx = Ctx(role='Investigator', operator='Synthetic local reader', request=request)
                cid = 'synthetic-case'
                case = {'caseId': cid, 'schemaVersion': '1.0.0', 'title': 'Synthetic UTF8 test',
                        'accidentType': 'Synthetic', 'isFictionalDemo': True,
                        'caseEpochUtc': '2026-02-01T12:00:00Z', 'incidentTimeUtc': '2026-02-01T12:00:00Z',
                        'incidentLocation': {'lonDeg': -130, 'latDeg': -30}, 'displayTimeZoneOffsetMinutes': 0}
                # Case/policy setup is the existing business-test scaffold, not evidence rows.
                with db.session() as s:
                    for target in (cid, 'synthetic-other'):
                        doc = {**case, 'caseId': target}; contracts.validate('case', doc)
                        put_doc(s, CaseRow, target, target, doc)
                        put_doc(s, AccessPolicyRow, target, 'policy', default_policy())
                body = {'profile': 'mcis-evidence-intake-v1', 'fileName': 'synthetic.txt',
                        'title': 'Synthetic text', 'source': 'Handmade synthetic fixture',
                        'extractedBy': 'Synthetic author', 'extractedUtc': '2026-02-01T00:00:00Z',
                        'category': 'Document', 'confidentiality': 'Restricted', 'note': 'No real report',
                        'contentBase64': base64.b64encode(fixture.RAW).decode()}
                preview = asyncio.run(intake.preview_input(cid, Body(body), ctx))
                receipt = asyncio.run(intake.commit_input(cid, Body({**body,
                    'requestDigest': preview['requestDigest'], 'confirmed': True}), ctx))
                self.assertEqual(receipt['sourceSha256'], fixture.PIN)

                def counts():
                    with db.session() as s:
                        return tuple(s.query(m).count() for m in (EvidenceRow, CustodyEventRow, AuditEventRow))

                def read(context, target):
                    # Purpose validated by same production primitive used in download; no route invocation.
                    purpose = intake.text('Synthetic local UTF8 draft review', 1000)
                    intake.text(context.operator, 200, multiline=False)
                    with WRITE_LOCK:
                        with db.session() as s:
                            begin(s)
                            found = intake._read_original_for_access(context, s, target, receipt['requestDigest'], purpose)
                    return found  # Only after transaction committed.

                self.assertEqual(counts(), (1, 1, 1))
                before = counts()
                with self.assertRaises(HTTPException) as wrong:
                    read(ctx, 'synthetic-other')
                self.assertEqual(wrong.exception.status_code, 404)
                denied = Ctx(role='ExternalExpert', operator='Synthetic denied reader', request=request)
                with self.assertRaises(HTTPException) as refusal:
                    read(denied, cid)
                self.assertEqual(refusal.exception.status_code, 403)
                self.assertEqual(counts(), before)
                registered, raw = read(ctx, cid)
                self.assertEqual(raw, fixture.RAW)
                self.assertEqual(registered['sourceSha256'], hashlib.sha256(raw).hexdigest())
                self.assertEqual(registered['evidenceId'], receipt['evidenceId'])
                self.assertEqual(registered['caseId'], cid)
                self.assertEqual(counts(), (1, 2, 2))
                # Alias is local host-owned test mapping, NOT production evidence identity or authority.
                # The actual receipt remains here; neither extractor proposal nor UI supplies this map.
                host, rubric, proposal = fixture.fixture()
                binding = {'caseId': registered['caseId'], 'sourceId': host['sourceId'],
                           'rawSha256': registered['sourceSha256']}
                self.assertEqual(binding, rubric['binding'])
                local_source = {host['sourceId']: {k: registered[k] for k in
                    ('caseId', 'evidenceId', 'requestDigest', 'sourceSha256')}}
                draft = fixture.p.project_utf8(raw, proposal, host=binding, rubric=rubric)
                self.assertEqual(len(draft['nodes']), 3)
                self.assertFalse(draft['saved']); self.assertFalse(draft['authorityVerified'])
                self.assertFalse(draft['scenarioReady']); self.assertEqual(draft['edges'], [])
                for node in draft['nodes']:
                    src = node['source']
                    self.assertEqual(local_source[src['sourceId']]['sourceSha256'], src['rawSha256'])
                    self.assertEqual(raw[src['byteStart']:src['byteEndExclusive']].decode(), node['text'])
                    self.assertNotIn('page', src)
                self.assertEqual(counts(), (1, 2, 2))
                with db.session() as s:
                    accesses = s.scalars(select(CustodyEventRow).where(CustodyEventRow.kind == 'Access')).all()
                    self.assertEqual(len(accesses), 1)
                    self.assertEqual(accesses[0].sha256, fixture.PIN)
                    self.assertEqual(accesses[0].evidence_id, receipt['evidenceId'])
                    self.assertEqual(s.query(AuditEventRow).filter_by(action='custody.access').count(), 1)
                    self.assertTrue(verify_chain(all_lines(s, cid))['valid'])
                    custody = s.scalars(select(CustodyEventRow).where(CustodyEventRow.case_id == cid).order_by(CustodyEventRow.seq)).all()
                    self.assertTrue(verify_chain([r.line for r in custody])['valid'])
                    tables = set(s.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).scalars())
                    self.assertEqual(tables, {m.__tablename__ for m in models})
                print(json.dumps({'syntheticOnly': True, 'registration': 1, 'access': 1,
                    'wrongCaseStatus': 404, 'deniedStatus': 403, 'rejectionAccessDelta': 0,
                    'auditChainValid': True, 'rawSha256': fixture.PIN, 'draftNodes': 3,
                    'saved': False, 'productionSourceBinding': False}, sort_keys=True))

    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    for name, loaded in tuple(sys.modules.items()):
        if name == 'mcis_service' or name.startswith('mcis_service.'):
            path = Path(loaded.__file__).resolve()
            if not path.is_relative_to(source) or str(path.relative_to(source)) not in allowed:
                raise RuntimeError('Unexpected production import')
    return result.wasSuccessful()


if __name__ == '__main__':
    if not sys.flags.isolated: raise SystemExit('Use existing Python -I -B')
    with tempfile.TemporaryDirectory(prefix='registered-utf8-') as folder:
        source = Path(folder)
        harness = module('pinned_business', copy_fixed(HARNESS,
            'tests_acceptance/registered-trajectory-pair/business.py', source))
        allowed = tuple(p for p in harness.PATHS if not p.startswith('tests_acceptance/'))
        for path in allowed: copy_fixed(PRODUCT, path, source)
        for path in ('research/semantic_support/evaluate.py',
                     'tests_acceptance/synthetic-utf8-locator/check.py',
                     'tests_acceptance/synthetic-report-draft/project.py',
                     'tests_acceptance/synthetic-report-draft/check_utf8_joined.py'):
            copy_fixed(DRAFT, path, source)
        fixture = module('pinned_utf8_fixture', source / 'tests_acceptance/synthetic-report-draft/check_utf8_joined.py')
        ok = run(source, allowed, fixture)
    raise SystemExit(0 if ok else 1)
