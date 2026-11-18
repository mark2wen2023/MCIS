"""One normal synthetic 1.0 -> 1.2 evidence chain; no fault/denial probes."""
import hashlib
import io
import json
import zipfile
from sqlalchemy import select
from mcis_service.evidence.models import EvidenceRow, CustodyEventRow
from mcis_service.evidence.service import custody_line
from mcis_service.package.mcase import manifest_json
from .test_archive_artifact_destinations_normal import CID, initial_package, store, intake, export


def test_synthetic_evidence_bytes_registration_and_custody_across_three_stores(tmp_path):
    original = 'SYNTHETIC ONLY — no case material\n合成文本第二行。\n'.encode('utf-8')
    digest = hashlib.sha256(original).hexdigest()
    entry = dict(evidenceId='EV-900001', caseId=CID,
                 title='Synthetic text', source='Constructed in this test, not an actual source',
                 extractedBy='Synthetic operator', extractedUtc='2026-01-01T00:00:00Z',
                 sha256=digest, relativePath='raw/synthetic-text.txt',
                 confidentiality='Normal', category='Document', note='Not verified real evidence')
    line = custody_line(seq=1, utc='2026-01-01T00:00:00Z', operator='Synthetic operator',
                        kind='Register', evidence_id=entry['evidenceId'], sha256=digest,
                        previous_sha256='', detail='', matched=None, prev='0'*64, item=entry)
    with zipfile.ZipFile(io.BytesIO(initial_package())) as archive:
        files = {name: archive.read(name) for name in archive.namelist() if name != 'manifest.json'}
    files.update({'raw/synthetic-text.txt': original,
                  'evidence/index.json': json.dumps([entry], ensure_ascii=False).encode(),
                  'audit/custody.jsonl': (line+'\n').encode()})
    files['manifest.json'] = manifest_json(CID, files, '2026-01-01T00:00:00Z').encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, raw in files.items():
            archive.writestr(name, raw)
    package = output.getvalue()
    for generation in range(3):
        directory = tmp_path / f'generation-{generation}'
        with store(directory) as client:
            settings = client.app.state.settings
            assert settings.seed_demo is False
            assert settings.data_dir == directory
            assert settings.resolved_db_url == f'sqlite:///{directory / "test.db"}'
            intake(client, package)
            with client.app.state.db.session() as session:
                rows = list(session.scalars(select(EvidenceRow).where(EvidenceRow.case_id == CID)))
                assert len(rows) == 1 and rows[0].doc == entry
                custody = list(session.scalars(select(CustodyEventRow).where(
                    CustodyEventRow.case_id == CID).order_by(CustodyEventRow.seq)))
                assert len(custody) == 1
                assert (custody[0].seq, custody[0].kind, custody[0].evidence_id,
                        custody[0].sha256, custody[0].line) == (1, 'Register', entry['evidenceId'], digest, line)
            actual = (settings.blob_dir / CID / entry['relativePath']).read_bytes()
            assert actual == original and hashlib.sha256(actual).hexdigest() == digest
            package = export(client)
            with zipfile.ZipFile(io.BytesIO(package)) as archive:
                assert not any(name.startswith('hfacs/') for name in archive.namelist())
                assert json.loads(archive.read('evidence/index.json')) == [entry]
                assert archive.read(entry['relativePath']) == original
                assert hashlib.sha256(archive.read(entry['relativePath'])).hexdigest() == digest
                assert archive.read('audit/custody.jsonl') == (line+'\n').encode()
