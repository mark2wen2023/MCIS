"""Synthetic direct-handler reopen check; no application, seed, model or HTTP."""
import asyncio
import base64
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
import zlib

REF = '91962113bd98778d3538f0e8e9879a014023c21f'
ROOT = Path(__file__).resolve().parents[2]
CASE = 'SYN-XREPO-001'
MODULES = '''__init__ config db common/__init__ common/contracts common/context common/timeutil common/csjson
cases/__init__ cases/models cases/service audit/__init__ audit/models audit/service
redaction/__init__ redaction/models redaction/policy redaction/gateway
evidence/__init__ evidence/models evidence/service evidence_intake/__init__ evidence_intake/parser evidence_intake/router
reports/__init__ reports/models reports/access interviews/__init__ interviews/models interviews/access
manual_interviews/__init__ manual_interviews/models working_records_archive/__init__ working_records_archive/models
working_records_archive/validation working_records_archive/service report_output/__init__ report_output/attachment_access
track_history/__init__ track_history/models track_history/service
image_review/__init__ image_review/app image_review/contract'''.split()
PATHS = tuple('service/mcis_service/' + p + '.py' for p in MODULES) + tuple(
    'contracts/schemas/' + p + '.schema.json' for p in ('case', 'common', 'evidence-item'))
os.environ['GIT_NO_LAZY_FETCH'] = '1'
os.environ['GIT_TERMINAL_PROMPT'] = '0'
sys.dont_write_bytecode = True


def materialize(folder):
    for path in PATHS:
        entry = subprocess.check_output(['git', '--no-replace-objects', 'ls-tree', REF, '--', path], cwd=ROOT).decode().split()
        if len(entry) != 4 or entry[:2] != ['100644', 'blob'] or entry[3] != path:
            raise RuntimeError('fixed source missing: ' + path)
        raw = subprocess.check_output(['git', '--no-replace-objects', 'show', REF + ':' + path], cwd=ROOT)
        if hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() != entry[2]:
            raise RuntimeError('fixed blob mismatch')
        target = folder / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)


def sha(raw): return hashlib.sha256(raw).hexdigest()


class Body:
    # Transport fixture only; production body_bounded still validates this body.
    headers = {'content-type': 'application/json'}
    def __init__(self, value): self.raw = json.dumps(value).encode()
    async def stream(self): yield self.raw


def png():
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 2, 1, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\0\xff\0\0\0\0\xff')) + chunk(b'IEND', b'')


def candidate(image, pdf, raw):
    return dict(schema='mcis.offline-ocr-candidate/v0.1', production_import_supported=False,
        page_index_inferred=False, limitations=['synthetic supplied OCR; image/PDF mapping not verified'],
        confirmed=False, needs_review=True, status='pending_human_review',
        source=dict(pdf_sha256=sha(pdf), image_sha256=sha(image), raw_sha256=sha(raw),
                    pdf_page_1based=1, printed_page='', mapping_basis='synthetic declaration only', width=2, height=1),
        recognizer=dict(paddlepaddle='synthetic', paddleocr='synthetic', paddlex='synthetic', pipeline='synthetic', models=['fixture'], device='none'),
        raw_page_index=None, coordinate_space='rendered_page_pixels_xy_top_left', tables=[],
        text_lines=[dict(line_index=0, text='SYNTHETIC LINE', is_blank=False, confirmed=False,
                        needs_review=True, model_score=0.5, bbox=[0, 0, 2, 1], polygon=[[0, 0], [2, 0], [2, 1], [0, 1]])])


def run(source):
    sys.path.insert(0, str(source / 'service'))
    from fastapi import HTTPException
    from sqlalchemy import select, text
    from mcis_service.db import Database, Base, put_doc, APPEND_ONLY_TABLES
    from mcis_service.common.context import Ctx
    from mcis_service.common.contracts import validate
    from mcis_service.cases.models import CaseRow
    from mcis_service.evidence.models import EvidenceRow, CustodyEventRow
    from mcis_service.audit.models import AuditEventRow
    from mcis_service.audit import service as audit
    from mcis_service.redaction.models import AccessPolicyRow
    from mcis_service.redaction.policy import default_policy
    from mcis_service.working_records_archive.models import ArchiveImportHistoryRow
    from mcis_service.track_history.models import LocalReceipt
    from mcis_service.image_review import app as review
    from mcis_service.evidence_intake import router as intake

    class Reopen(unittest.TestCase):
        def test_saved_line_reopens_to_registered_bytes(self):
            with tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp); blobs = folder / 'blobs'; blobs.mkdir()
                url = 'sqlite:///' + str(folder / 'fresh.sqlite')
                db = Database(url)
                Base.metadata.create_all(db.engine, tables=[m.__table__ for m in (CaseRow, EvidenceRow, CustodyEventRow, AuditEventRow, AccessPolicyRow, ArchiveImportHistoryRow, LocalReceipt)])
                review.Storage.metadata.create_all(db.engine)
                with db.engine.begin() as c:
                    for table in (*APPEND_ONLY_TABLES, 'image_ocr_review_records'):
                        for op in ('UPDATE', 'DELETE'):
                            c.execute(text(f"CREATE TRIGGER IF NOT EXISTS {table}_no_{op.lower()} BEFORE {op} ON {table} BEGIN SELECT RAISE(ABORT, 'append-only'); END;"))
                state = SimpleNamespace(db=db, settings=SimpleNamespace(blob_dir=blobs))
                ctx = Ctx('Investigator', 'Synthetic fixture operator', SimpleNamespace(app=SimpleNamespace(state=state)))
                case = dict(caseId=CASE, schemaVersion='1.0.0', title='Synthetic image reopen', accidentType='Synthetic', isFictionalDemo=True,
                            caseEpochUtc='2026-02-01T12:00:00Z', incidentTimeUtc='2026-02-01T12:00:00Z',
                            incidentLocation=dict(lonDeg=-130, latDeg=-30), displayTimeZoneOffsetMinutes=0)
                validate('case', case)
                with db.session() as s:
                    put_doc(s, CaseRow, CASE, CASE, case)
                    put_doc(s, AccessPolicyRow, CASE, 'policy', default_policy())
                # PDF is opaque prerequisite bytes, NOT a rendered PDF or verified page.
                pdf = b'SYNTHETIC opaque PDF prerequisite; not a valid PDF'
                image = png(); raw = b'SYNTHETIC supplied recognizer bytes'
                value = candidate(image, pdf, raw)
                files = {'pdf': pdf, 'image': image, 'raw': raw, 'candidate': json.dumps(value).encode()}
                pins = {}
                for kind, data in files.items():
                    body = dict(profile='mcis-evidence-intake-v1', fileName=kind + '.bin', title='Synthetic ' + kind,
                        source='handmade synthetic fixture', extractedBy='Synthetic author', extractedUtc='2026-02-01T00:00:00Z',
                        category='Document', confidentiality='Restricted', note='not authenticated evidence', contentBase64=base64.b64encode(data).decode())
                    preview = asyncio.run(intake.preview_input(CASE, Body(body), ctx))
                    pins[kind] = asyncio.run(intake.commit_input(CASE, Body({**body, 'requestDigest': preview['requestDigest'], 'confirmed': True}), ctx))
                    self.assertEqual(pins[kind]['sourceSha256'], sha(data))
                bindings = {k: p['requestDigest'] for k, p in pins.items()}
                registered = asyncio.run(review.register(CASE, Body(dict(bindings=bindings, acknowledgeArchiveBlocked=True)), ctx))
                run_id = registered['runId']
                edited = asyncio.run(review.review(CASE, run_id, Body(dict(expectedRevision=0, lineIndex=0,
                    text='SYNTHETIC CORRECTION', decision='transcription-checked', reason='synthetic manual transcription declaration')), ctx))
                self.assertEqual(edited['revision'], 1)
                db.engine.dispose()
                # New Database/engine/session, same temporary on-disk files; not archive restore.
                db = Database(url); state.db = db
                try:
                    reopened = review.read(CASE, run_id, ctx)
                    self.assertEqual(reopened, edited)
                    self.assertFalse(reopened['factVerified']); self.assertFalse(reopened['archiveSupported'])
                    initial = reopened['initial']
                    self.assertFalse(initial['pageMappingVerified']); self.assertFalse(initial['originalAuthenticityVerified'])
                    self.assertEqual(initial['candidate']['text_lines'][0], value['text_lines'][0])
                    self.assertIsNone(initial['candidate']['raw_page_index'])
                    self.assertEqual(initial['bindings'], bindings)
                    for kind, p in pins.items():
                        self.assertEqual(initial['sourceVersions'][kind], {'evidenceId': p['evidenceId'], 'sha256': p['sourceSha256']})
                    with db.session() as s:
                        before = (s.query(CustodyEventRow).count(), s.query(AuditEventRow).count(), s.query(review.Record).count())
                        self.assertEqual(s.query(CustodyEventRow).filter_by(kind='Access').count(), 0)
                    # Ordinary unknown run: no source content returned and no Access.
                    with self.assertRaises(HTTPException) as denied: review.read(CASE, 'OCR-missing', ctx)
                    self.assertEqual(denied.exception.status_code, 404)
                    with db.session() as s:
                        self.assertEqual((s.query(CustodyEventRow).count(), s.query(AuditEventRow).count(), s.query(review.Record).count()), before)
                    response = asyncio.run(intake.download(CASE, bindings['image'], Body({'purpose': 'Synthetic reopened line comparison'}), ctx))
                    self.assertEqual(response.body, image); self.assertEqual(response.headers['x-sha256'], pins['image']['sourceSha256'])
                    self.assertEqual(response.headers['content-type'], 'application/octet-stream')
                    # Decode generated PNG scanline to validate shape/pixels, not OCR/visual meaning.
                    self.assertEqual(struct.unpack('>II', response.body[16:24]), (2, 1))
                    length = struct.unpack('>I', response.body[33:37])[0]
                    self.assertEqual(response.body[37:41], b'IDAT')
                    self.assertEqual(zlib.decompress(response.body[41:41+length]), b'\0\xff\0\0\0\0\xff')
                    with db.session() as s:
                        accesses = s.scalars(select(CustodyEventRow).where(CustodyEventRow.kind == 'Access')).all()
                        self.assertEqual(len(accesses), 1)
                        self.assertEqual((accesses[0].evidence_id, accesses[0].sha256), (pins['image']['evidenceId'], sha(image)))
                        self.assertEqual(s.query(review.Record).count(), 2)
                        self.assertEqual(s.query(AuditEventRow).count(), before[1] + 1)
                        self.assertTrue(audit.verify_chain(audit.all_lines(s, CASE))['valid'])
                        self.assertTrue(audit.verify_chain([r.line for r in s.scalars(select(CustodyEventRow).order_by(CustodyEventRow.seq))])['valid'])
                    self.assertEqual(review.read(CASE, run_id, ctx), reopened)
                finally: db.engine.dispose()
    outcome = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Reopen))
    for name, module in tuple(sys.modules.items()):
        if name == 'mcis_service' or name.startswith('mcis_service.'):
            if str(Path(module.__file__).relative_to(source)) not in PATHS:
                raise RuntimeError('unexpected module')
    return outcome.wasSuccessful()


if __name__ == '__main__':
    if not sys.flags.isolated or sys.flags.optimize: raise SystemExit('Use Python -I -B, without -O')
    with tempfile.TemporaryDirectory(prefix='image-reopen-source-') as tmp:
        source = Path(tmp)
        materialize(source)
        passed = run(source)
    print(json.dumps(dict(passed=passed, sourceCommit=REF, syntheticOnly=True, http=False,
        sourceAccess=1 if passed else None, browser=False, ocrExecuted=False, archiveRestored=False)))
    raise SystemExit(0 if passed else 1)
