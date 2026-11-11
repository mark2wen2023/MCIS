"""Contract-safe public report seeding, provenance, fail-closed hashes and idempotence."""
import hashlib
import json
import shutil

import pytest
from sqlalchemy import select

from mcis_service.cases.models import CaseRow, VesselRow, TrackPointRow
from mcis_service.common import contracts
from mcis_service.config import PROJECT_ROOT
from mcis_service.db import get_doc, list_docs, put_doc
from mcis_service.evidence.models import EvidenceRow
from mcis_service.seed import yangze22 as seed


def test_seed_contract_provenance_no_tracks_and_restart_preserves_edits(app):
    with app.state.db.session() as s:
        case = get_doc(s, CaseRow, seed.CASE_ID, seed.CASE_ID)
        assert case and not contracts.errors('case', case)
        assert case['accidentGrade'] == '较大' and case['caseEpochUtc'] == case['incidentTimeUtc']
        assert case['isFictionalDemo'] is False
        vessels = list_docs(s, VesselRow, seed.CASE_ID)
        assert len(vessels) == 2
        assert sorted(v['loaM'] for v in vessels) == [225.29, 283.3]
        assert all(not contracts.errors('vessel', v) for v in vessels)
        assert all('draftForeM' not in v and 'grossTonnage' not in v for v in vessels)
        assert not list(s.scalars(select(TrackPointRow).where(TrackPointRow.case_id == seed.CASE_ID)))
        evidence = list_docs(s, EvidenceRow, seed.CASE_ID)
        assert len(evidence) == 3
        for item in evidence:
            assert not contracts.errors('evidence-item', item)
            data = (app.state.settings.blob_dir / seed.CASE_ID / item['relativePath']).read_bytes()
            assert hashlib.sha256(data).hexdigest() == item['sha256']
        case['title'] = '调查员编辑保留'
        put_doc(s, CaseRow, seed.CASE_ID, seed.CASE_ID, case)
        vessels[0]['name'] = '人工编辑船名'
        put_doc(s, VesselRow, seed.CASE_ID, vessels[0]['vesselId'], vessels[0])
    with app.state.db.session() as s:
        assert seed.seed(s, app.state.settings.blob_dir) is False
        assert get_doc(s, CaseRow, seed.CASE_ID, seed.CASE_ID)['title'] == '调查员编辑保留'
        assert get_doc(s, VesselRow, seed.CASE_ID, vessels[0]['vesselId'])['name'] == '人工编辑船名'
        assert list_docs(s, EvidenceRow, seed.CASE_ID) == evidence


def test_source_tamper_rejected_before_import(tmp_path):
    root = tmp_path / 'source'
    root.mkdir()
    for filename in seed.SOURCE_HASHES:
        shutil.copy(PROJECT_ROOT / 'reports/yangze22' / filename, root / filename)
    with (root / 'report.txt').open('ab') as f:
        f.write(b'tampered')
    with pytest.raises(ValueError, match='checksum mismatch'):
        seed.load_source(root)


@pytest.mark.parametrize('template', ['imo-cic', 'maib', 'cn-msa'])
def test_yangze_report_available_with_all_five_seed_scenarios(client, template):
    from .conftest import H
    prefix = '/api/v1/cases/' + seed.CASE_ID
    assert client.get(prefix, headers=H()).status_code == 200
    assert 'blockedReason' not in client.get(prefix + '/reports', headers=H()).json()
    created = client.post(prefix + '/reports', headers=H(), json={'templateId': template, 'lang': 'bilingual'})
    assert created.status_code == 201, created.text
    report = created.json()
    assert report['caseId'] == seed.CASE_ID and report['isFictionalDemo'] is False
    assert report['realDataStatus'] == 'authorized-public' and report['status'] == 'Draft'
    sentences = [t for section in report['sections'] for t in section['sentences']]
    scenarios = [t for t in sentences if 'W14 推演情景' in t['textZh']]
    assert len(scenarios) >= 5
    assert all(t['status'] == 'Draft' and t['sourceStatus'] == 'Derived' for t in scenarios)
    rid = report['reportId']
    sid = report['sections'][0]['sectionId']
    review = client.patch(prefix + f'/reports/{rid}/sections/{sid}', headers=H(),
                          json={'action': 'confirm'})
    assert review.status_code == 200, review.text
    events = client.get(prefix + f'/reports/{rid}/audit', headers=H()).json()
    snapshot_id = events[-1]['snapshotRef'].split(':', 1)[1]
    assert client.get(prefix + '/report-snapshots/' + snapshot_id, headers=H()).status_code == 200
    regenerated = client.post(prefix + f'/reports/{rid}:generate', headers=H())
    assert regenerated.status_code == 201 and regenerated.json()['version'] == 2
    for fmt in ('pdf', 'docx'):
        response = client.get(prefix + f'/reports/{rid}/export?format={fmt}', headers=H())
        assert response.status_code == 200, response.text[:500]
        assert response.content.startswith(b'%PDF' if fmt == 'pdf' else b'PK')
    assert client.get(prefix + '/gisis', headers=H()).json()['realDataStatus'] == 'authorized-public'


def test_failed_seed_transaction_can_retry_identical_blobs(tmp_path):
    from .conftest import make_settings
    from mcis_service.main import create_app
    app = create_app(make_settings(tmp_path, seed=False))
    with pytest.raises(RuntimeError):
        with app.state.db.session() as s:
            assert seed.seed(s, app.state.settings.blob_dir)
            raise RuntimeError('simulate transaction rollback')
    with app.state.db.session() as s:
        assert get_doc(s, CaseRow, seed.CASE_ID, seed.CASE_ID) is None
        assert seed.seed(s, app.state.settings.blob_dir)
    with app.state.db.session() as s:
        assert len(list_docs(s, EvidenceRow, seed.CASE_ID)) == 3


def test_conflicting_existing_blob_not_overwritten_or_partially_imported(tmp_path):
    from .conftest import make_settings
    from mcis_service.main import create_app
    app = create_app(make_settings(tmp_path, seed=False))
    path = app.state.settings.blob_dir / seed.CASE_ID / 'raw/public/report.txt'
    path.parent.mkdir(parents=True)
    path.write_bytes(b'user-owned content')
    with pytest.raises(ValueError, match='existing source blob differs'):
        with app.state.db.session() as s:
            seed.seed(s, app.state.settings.blob_dir)
    assert path.read_bytes() == b'user-owned content'
    with app.state.db.session() as s:
        assert get_doc(s, CaseRow, seed.CASE_ID, seed.CASE_ID) is None
        assert not list_docs(s, EvidenceRow, seed.CASE_ID)
