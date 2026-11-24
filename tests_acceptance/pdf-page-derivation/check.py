"""Real registration/read + Poppler; only synthetic context/request transport."""
import asyncio
import base64
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PARENT = '900a8e58585693a408706129ba9562d159ed5eb9'
HELPER = 'tests_acceptance/image-reopen-source/check.py'
HELPER_SHA = '76de411135b4754ec99ca2c6e8c9740609b13205a7915397e2d2ac15023a9b60'
os.environ['GIT_NO_LAZY_FETCH'] = '1'
os.environ['GIT_TERMINAL_PROMPT'] = '0'
sys.dont_write_bytecode = True


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def synthetic_pdf():
    # Two 72pt square physical pages: red then blue; no fonts/OCR/external objects.
    streams = [b'1 0 0 rg 0 0 72 72 re f\n', b'0 0 1 rg 0 0 72 72 re f\n']
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
               b'<< /Type /Pages /Kids [3 0 R 5 0 R] /Count 2 >>']
    for content_id, stream in zip((4, 6), streams):
        objects += [f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 72 72] /Resources << >> /Contents {content_id} 0 R >>'.encode(),
                    b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'endstream']
    raw = b'%PDF-1.4\n'; offsets = [0]
    for n, obj in enumerate(objects, 1):
        offsets.append(len(raw)); raw += str(n).encode() + b' 0 obj\n' + obj + b'\nendobj\n'
    xref = len(raw)
    raw += b'xref\n0 7\n0000000000 65535 f \n'
    raw += b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets[1:])
    return raw + b'trailer\n<< /Size 7 /Root 1 0 R >>\nstartxref\n' + str(xref).encode() + b'\n%%EOF\n'


def run(source, helper, derive):
    sys.path.insert(0, str(source / 'service'))
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
    from mcis_service.evidence_intake import router as intake

    class Pdf(unittest.TestCase):
        def test_registered_pdf_two_pages_and_crop_binding(self):
            with tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp); blobs = folder / 'blobs'; blobs.mkdir()
                db = Database('sqlite:///' + str(folder / 'fresh.sqlite'))
                try:
                    Base.metadata.create_all(db.engine, tables=[m.__table__ for m in (CaseRow, EvidenceRow, CustodyEventRow, AuditEventRow, AccessPolicyRow, ArchiveImportHistoryRow, LocalReceipt)])
                    with db.engine.begin() as c:
                        for table in APPEND_ONLY_TABLES:
                            for op in ('UPDATE', 'DELETE'):
                                c.execute(text(f"CREATE TRIGGER IF NOT EXISTS {table}_no_{op.lower()} BEFORE {op} ON {table} BEGIN SELECT RAISE(ABORT, 'append-only'); END;"))
                    state = SimpleNamespace(db=db, settings=SimpleNamespace(blob_dir=blobs))
                    ctx = Ctx('Investigator', 'Synthetic PDF author', SimpleNamespace(app=SimpleNamespace(state=state)))
                    cid = 'SYN-XREPO-001'
                    case = dict(caseId=cid, schemaVersion='1.0.0', title='Synthetic PDF pages', accidentType='Synthetic', isFictionalDemo=True,
                        caseEpochUtc='2026-02-01T12:00:00Z', incidentTimeUtc='2026-02-01T12:00:00Z', incidentLocation=dict(lonDeg=-130, latDeg=-30), displayTimeZoneOffsetMinutes=0)
                    validate('case', case)
                    with db.session() as s:
                        put_doc(s, CaseRow, cid, cid, case)
                        put_doc(s, AccessPolicyRow, cid, 'policy', default_policy())
                    original = synthetic_pdf()
                    body = dict(profile='mcis-evidence-intake-v1', fileName='synthetic.pdf', title='Synthetic two-page PDF', source='fixture generator',
                        extractedBy='Synthetic author', extractedUtc='2026-02-01T00:00:00Z', category='Document', confidentiality='Restricted', note='synthetic only', contentBase64=base64.b64encode(original).decode())
                    preview = asyncio.run(intake.preview_input(cid, helper.Body(body), ctx))
                    pin = asyncio.run(intake.commit_input(cid, helper.Body({**body, 'requestDigest': preview['requestDigest'], 'confirmed': True}), ctx))
                    response = asyncio.run(intake.download(cid, pin['requestDigest'], helper.Body({'purpose': 'Synthetic physical-page comparison'}), ctx))
                    self.assertEqual(response.body, original)
                    self.assertEqual(response.headers['x-sha256'], pin['sourceSha256'])
                    def counts():
                        with db.session() as s: return (s.query(EvidenceRow).count(), s.query(CustodyEventRow).count(), s.query(AuditEventRow).count())
                    baseline = counts(); self.assertEqual(baseline, (1, 2, 2))
                    pages = [derive.render(response.body, expected_sha256=pin['sourceSha256'], physical_page=n) for n in (1, 2)]
                    self.assertNotEqual(pages[0][0]['pageSha256'], pages[1][0]['pageSha256'])
                    for n, ((record, image), color) in enumerate(zip(pages, ((255, 0, 0), (0, 0, 255))), 1):
                        self.assertEqual((record['width'], record['height']), (256, 256))
                        locator, crop = derive.crop(image, page_record=record, expected_source_sha256=pin['sourceSha256'], expected_physical_page=n, box=(64, 64, 128, 128))
                        self.assertEqual(locator['physicalPage'], n)
                        self.assertEqual(locator['pageSha256'], record['pageSha256'])
                        self.assertEqual(locator['cropSha256'], derive.sha(crop))
                        with Image.open(io.BytesIO(crop)) as decoded:
                            self.assertEqual(decoded.size, (64, 64)); self.assertEqual(decoded.convert('RGB').getpixel((32, 32)), color)
                    with self.assertRaisesRegex(ValueError, 'page binding mismatch'):
                        derive.crop(pages[1][1], page_record=pages[1][0], expected_source_sha256=pin['sourceSha256'], expected_physical_page=1, box=(64, 64, 128, 128))
                    with self.assertRaisesRegex(ValueError, 'source digest mismatch'):
                        derive.render(response.body + b'\n', expected_sha256=pin['sourceSha256'], physical_page=1)
                    with self.assertRaisesRegex(ValueError, 'page outside document'):
                        derive.render(response.body, expected_sha256=pin['sourceSha256'], physical_page=3)
                    self.assertEqual(counts(), baseline)
                    self.assertEqual(intake.file_path(ctx, cid, intake.rel_for(pin['requestDigest'])).read_bytes(), original)
                    with db.session() as s:
                        events = s.scalars(select(CustodyEventRow).order_by(CustodyEventRow.seq)).all()
                        self.assertEqual([e.kind for e in events], ['Register', 'Access'])
                        self.assertEqual(events[-1].evidence_id, pin['evidenceId'])
                        self.assertEqual(events[-1].sha256, pin['sourceSha256'])
                        self.assertTrue(audit.verify_chain([e.line for e in events])['valid'])
                        self.assertTrue(audit.verify_chain(audit.all_lines(s, cid))['valid'])
                finally: db.engine.dispose()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Pdf))
    for name, loaded in tuple(sys.modules.items()):
        if name == 'mcis_service' or name.startswith('mcis_service.'):
            if str(Path(loaded.__file__).relative_to(source)) not in helper.PATHS: raise RuntimeError('unexpected module')
    return result.wasSuccessful()


if __name__ == '__main__':
    if not sys.flags.isolated or sys.flags.optimize: raise SystemExit('Use Python -I -B without -O')
    raw = subprocess.check_output(['git', '--no-replace-objects', 'show', PARENT + ':' + HELPER], cwd=ROOT)
    if hashlib.sha256(raw).hexdigest() != HELPER_SHA or (ROOT / HELPER).read_bytes() != raw: raise SystemExit('fixed helper mismatch')
    helper = module('fixed_image_helper', ROOT / HELPER)
    derive = module('pdf_derivation', Path(__file__).with_name('derive.py'))
    with tempfile.TemporaryDirectory(prefix='registered-pdf-source-') as tmp:
        source = Path(tmp); helper.materialize(source)
        passed = run(source, helper, derive)
    print(json.dumps({'passed': passed, 'syntheticOnly': True, 'sourceCommit': helper.REF, 'access': 1 if passed else None,
                      'physicalPages': 2 if passed else None, 'ocr': False, 'http': False, 'productMapping': False}))
    raise SystemExit(0 if passed else 1)
