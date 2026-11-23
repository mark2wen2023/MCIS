"""Portable W11 synthetic registration + text location; no ECFC binding or login."""
import os
os.environ['GIT_NO_LAZY_FETCH'] = '1'
import argparse
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

ROOT = None
FIXTURE = Path(__file__).resolve().with_name('communication.txt')
RAW_SHA = '418be9609b46a00062c41fb49073911986098e9a61e010f4311aa86946ecd3ea'
TRACKS = '2048c60fd6650c6f2c99a76a16be463a3895655d'
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


def run(source, allowed, locator, raw_input):
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
        def test_registration_fixed_read_and_t109_locator(self):
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
                cid = 'SYN-XREPO-001'
                case = {'caseId': cid, 'schemaVersion': '1.0.0', 'title': 'Synthetic W11 communication test',
                        'accidentType': 'Synthetic', 'isFictionalDemo': True,
                        'caseEpochUtc': '2026-02-01T12:00:00Z', 'incidentTimeUtc': '2026-02-01T12:00:00Z',
                        'incidentLocation': {'lonDeg': -130, 'latDeg': -30}, 'displayTimeZoneOffsetMinutes': 0}
                # Case/policy setup is the existing business-test scaffold, not evidence rows.
                with db.session() as s:
                    for target in (cid, 'SYN-OTHER'):
                        doc = {**case, 'caseId': target}; contracts.validate('case', doc)
                        put_doc(s, CaseRow, target, target, doc)
                        put_doc(s, AccessPolicyRow, target, 'policy', default_policy())
                body = {'profile': 'mcis-evidence-intake-v1', 'fileName': 'communication.txt',
                        'title': 'Synthetic text', 'source': 'Handmade synthetic fixture',
                        'extractedBy': 'Synthetic author', 'extractedUtc': '2026-02-01T00:00:00Z',
                        'category': 'Document', 'confidentiality': 'Restricted', 'note': 'No real report',
                        'contentBase64': base64.b64encode(raw_input).decode()}
                preview = asyncio.run(intake.preview_input(cid, Body(body), ctx))
                receipt = asyncio.run(intake.commit_input(cid, Body({**body,
                    'requestDigest': preview['requestDigest'], 'confirmed': True}), ctx))
                self.assertEqual(receipt['sourceSha256'], RAW_SHA)

                def counts():
                    with db.session() as s:
                        return tuple(s.query(m).count() for m in (EvidenceRow, CustodyEventRow, AuditEventRow))

                def read(context, target, expected_pin):
                    # Purpose validated by same production primitive used in download; no route invocation.
                    purpose = intake.text('Synthetic local UTF8 draft review', 1000)
                    intake.text(context.operator, 200, multiline=False)
                    with WRITE_LOCK:
                        with db.session() as s:
                            begin(s)
                            found = intake._read_original_for_access(context, s, target, expected_pin['requestDigest'], purpose)
                            # Test-host fixed pin comparison, not a new production authorization API.
                            actual = {key: found[0][key] for key in ('caseId','evidenceId','requestDigest','sourceSha256')}
                            if actual != expected_pin:
                                raise ValueError('FIXED_PIN_MISMATCH')
                    return found  # Only after transaction committed.

                pin = {key: receipt[key] for key in ('caseId','evidenceId','requestDigest','sourceSha256')}
                self.assertEqual(pin, {'caseId':'SYN-XREPO-001', 'evidenceId':'EV-001',
                    'requestDigest':'3614bb7f78bc8f89a2434a6b5c5ddde2215fd6371cf6222adcc9beda6aade6df',
                    'sourceSha256':RAW_SHA})
                self.assertEqual(counts(), (1, 1, 1))
                before = counts()
                with self.assertRaises(HTTPException) as wrong:
                    read(ctx, 'SYN-OTHER', pin)
                self.assertEqual(wrong.exception.status_code, 404)
                denied = Ctx(role='ExternalExpert', operator='Synthetic denied reader', request=request)
                with self.assertRaises(HTTPException) as refusal:
                    read(denied, cid, pin)
                self.assertEqual(refusal.exception.status_code, 403)
                self.assertEqual(counts(), before)
                for field, value in (('evidenceId', 'SYN-WRONG-EVIDENCE'), ('sourceSha256', '0' * 64)):
                    with self.subTest(field=field), self.assertRaisesRegex(ValueError, '^FIXED_PIN_MISMATCH$'):
                        read(ctx, cid, {**pin, field: value})
                    self.assertEqual(counts(), before)  # helper Access is rolled back with mismatch.
                registered, raw = read(ctx, cid, pin)
                self.assertEqual(raw, raw_input)
                self.assertEqual(registered['sourceSha256'], hashlib.sha256(raw).hexdigest())
                self.assertEqual(registered['evidenceId'], receipt['evidenceId'])
                self.assertEqual(registered['caseId'], cid)
                self.assertEqual(counts(), (1, 2, 2))
                quote = '2026-02-01T12:01:49.000Z'
                citation = {'paragraph':3, 'start':6, 'length':len(quote), 'quote':quote}
                location = locator.locate(raw, citation, expected_sha256=registered['sourceSha256'])
                self.assertEqual(raw[location['byteStart']:location['byteEndExclusive']].decode(), quote)
                self.assertFalse(location['authorityVerified'])
                self.assertNotIn('page', location)
                for wrong_time in ('2026-02-01T12:01:40.000Z', '2026-02-01T12:01:50.000Z'):
                    with self.subTest(wrong_time=wrong_time), self.assertRaisesRegex(ValueError, '^quote_location$'):
                        locator.locate(raw, {**citation, 'quote':wrong_time}, expected_sha256=registered['sourceSha256'])
                self.assertEqual(counts(), (1, 2, 2))  # no re-read for location validation.
                with db.session() as s:
                    accesses = s.scalars(select(CustodyEventRow).where(CustodyEventRow.kind == 'Access')).all()
                    self.assertEqual(len(accesses), 1)
                    self.assertEqual(accesses[0].sha256, RAW_SHA)
                    self.assertEqual(accesses[0].evidence_id, receipt['evidenceId'])
                    self.assertEqual(s.query(AuditEventRow).filter_by(action='custody.access').count(), 1)
                    self.assertTrue(verify_chain(all_lines(s, cid))['valid'])
                    custody = s.scalars(select(CustodyEventRow).where(CustodyEventRow.case_id == cid).order_by(CustodyEventRow.seq)).all()
                    self.assertTrue(verify_chain([r.line for r in custody])['valid'])
                    tables = set(s.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).scalars())
                    self.assertEqual(tables, {m.__tablename__ for m in models})
                print(json.dumps({'syntheticOnly':True, 'receiptPin':pin,
                    'cursorUtc':'2026-02-01T12:01:40.000Z', 'sourceRecordedUtc':quote,
                    'location':location, 'timeReview':'not_provided', 'eventOrderEstablished':False,
                    'auditChainValid':True, 'committedAccess':1, 'wrongCaseStatus':404,
                    'deniedStatus':403, 'pinMismatchesRolledBack':2, 'saved':False,
                    'ecfcBindingVerified':False}, ensure_ascii=False, sort_keys=True))

    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    for name, loaded in tuple(sys.modules.items()):
        if name == 'mcis_service' or name.startswith('mcis_service.'):
            path = Path(loaded.__file__).resolve()
            if not path.is_relative_to(source) or str(path.relative_to(source)) not in allowed:
                raise RuntimeError('Unexpected production import')
    return result.wasSuccessful()


if __name__ == '__main__':
    if not sys.flags.isolated or not __debug__: raise SystemExit('Use existing Python -I -B without -O')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, type=Path)
    ROOT = parser.parse_args().repo.resolve()
    raw_input = FIXTURE.read_bytes()
    if hashlib.sha256(raw_input).hexdigest() != RAW_SHA: raise SystemExit('Fixed fixture differs')
    with tempfile.TemporaryDirectory(prefix='w11-t109-source-') as folder:
        source = Path(folder)
        harness = module('pinned_business', copy_fixed(HARNESS,
            'tests_acceptance/registered-trajectory-pair/business.py', source))
        allowed = tuple(p for p in harness.PATHS if not p.startswith('tests_acceptance/'))
        for path in allowed: copy_fixed(PRODUCT, path, source)
        locator = module('pinned_locator', copy_fixed(DRAFT,
            'tests_acceptance/synthetic-utf8-locator/check.py', source))
        for side in ('a','b'):
            path = 'tests_acceptance/shared-trajectory-cross-repo-expanded/vessel-' + side + '.json'
            document = json.loads(copy_fixed(TRACKS, path, source).read_bytes())
            assert document['caseId'] == 'SYN-XREPO-001'
            if side == 'a':
                assert document['points'][7]['pointId'] == 'A-t100'
                assert document['points'][7]['time']['alignedUtc'] == '2026-02-01T12:01:40.000Z'
                assert document['points'][7]['headingDeg']['value'] is None
                assert not any(p['time']['alignedUtc'] == '2026-02-01T12:01:49.000Z' for p in document['points'])
        ok = run(source, allowed, locator, raw_input)
    raise SystemExit(0 if ok else 1)
