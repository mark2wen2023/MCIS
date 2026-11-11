"""Canonical upstream byte identity is independently hardcoded, not derived from production pins."""
import hashlib
import shutil
import pytest
from mcis_service.config import PROJECT_ROOT
from mcis_service.seed import yangze22 as seed
from mcis_service.reports import public_text
from mcis_service.reports.templates import get_template
from mcis_service.evidence.models import EvidenceRow
from mcis_service.db import Database, get_doc
from mcis_service.audit import service as audit
from mcis_service.evidence import service as evidence

CANONICAL_SHA = 'bca8f8b8ba04a5d0669a121bc6c9380c8cd6f8397f67be2d0b30b38871c22ef2'
CANONICAL_BLOB = 'd5a6b5fc79ad0371c8ccc372b40ca9110d5c30c4'
CANONICAL_SIZE = 62607
OLD_SHA = '7adad5bb499c28eb3985b79411c61dad593797e0d2a8aa64feb203077e43ee2b'
REPORT = PROJECT_ROOT / 'reports/yangze22/report.txt'
CASE = {'caseId': seed.CASE_ID, 'isFictionalDemo': False}


def test_upstream_canonical_byte_identity_and_three_pins():
    raw = REPORT.read_bytes()
    assert len(raw) == CANONICAL_SIZE
    assert hashlib.sha256(raw).hexdigest() == CANONICAL_SHA
    assert hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest() == CANONICAL_BLOB
    assert seed.SOURCE_HASHES['report.txt'] == public_text.SOURCE_SHA256 == CANONICAL_SHA
    ref = get_template('cn-msa', seed.CASE_ID)['standardRefs']
    assert CANONICAL_SHA in str(ref) and OLD_SHA not in str(ref)
    assert seed.load_source()[1]['report.txt'] == raw
    assert public_text.excerpts(CASE, get_template('cn-msa', seed.CASE_ID))


@pytest.mark.parametrize('suffix', [b'\n', b'\n\n', b'\r\n'])
def test_extra_final_linebreak_strictly_rejected(tmp_path, suffix):
    target = tmp_path / 'reports/yangze22'
    target.mkdir(parents=True)
    shutil.copy(REPORT.parent / 'case.json', target / 'case.json')
    raw = REPORT.read_bytes() + suffix
    (target / 'report.txt').write_bytes(raw)
    if suffix == b'\n':
        assert len(raw) == 62608 and hashlib.sha256(raw).hexdigest() == OLD_SHA
    with pytest.raises(ValueError, match='checksum mismatch: report.txt'):
        seed.load_source(target)
    assert public_text.excerpts(CASE, get_template('cn-msa', seed.CASE_ID), tmp_path) == {}


def test_fresh_database_evidence_and_custody_pin_canonical(app):
    with app.state.db.session() as session:
        item = get_doc(session, EvidenceRow, seed.CASE_ID, 'EV-201')
        assert item['sha256'] == CANONICAL_SHA
        raw = (app.state.settings.blob_dir / seed.CASE_ID / item['relativePath']).read_bytes()
        assert len(raw) == CANONICAL_SIZE and hashlib.sha256(raw).hexdigest() == CANONICAL_SHA
        events = evidence.custody_events(session, seed.CASE_ID, 'EV-201')
        assert events and all(e.sha256 == CANONICAL_SHA for e in events)


def test_legacy_bad_pin_database_is_not_silently_rewritten(tmp_path, monkeypatch):
    source = tmp_path / 'old-source'; source.mkdir()
    shutil.copy(REPORT.parent / 'case.json', source / 'case.json')
    (source / 'report.txt').write_bytes(REPORT.read_bytes() + b'\n')
    db = Database(f"sqlite:///{tmp_path / 'legacy.db'}"); db.create_all()
    blobs = tmp_path / 'blobs'
    # Deliberately construct a historical bad-pin DB in isolation; production source is never modified.
    with monkeypatch.context() as patch:
        patch.setitem(seed.SOURCE_HASHES, 'report.txt', OLD_SHA)
        with db.session() as session:
            assert seed.seed(session, blobs, source_root=source)
    def snapshot(session):
        return (get_doc(session, EvidenceRow, seed.CASE_ID, 'EV-201'),
                [e.line for e in evidence.custody_events(session, seed.CASE_ID, 'EV-201')],
                audit.list_events(session, seed.CASE_ID))
    with db.session() as session: before = snapshot(session)
    with db.session() as session:
        assert seed.seed(session, blobs) is False
        assert snapshot(session) == before
    assert before[0]['sha256'] == OLD_SHA
    assert hashlib.sha256((blobs / seed.CASE_ID / before[0]['relativePath']).read_bytes()).hexdigest() == OLD_SHA
