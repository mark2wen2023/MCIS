"""Ordinary synthetic preparation/readback; no role overrides or denial probes."""
import json
import sqlite3
from pathlib import Path
from fastapi.testclient import TestClient
from tools.media_review_demo.prepare import prepare, CID
from tools.media_review_demo.launch import check_manifest, settings_for
from mcis_service.media_review_demo import create_media_review_demo


def test_synthetic_prepare_and_readback_without_role_header(tmp_path, monkeypatch):
    original = TestClient.request
    seen = []
    def observe(self, method, url, **kwargs):
        headers = kwargs.get('headers') or {}
        assert all(k.lower() != 'x-mcis-role' for k in headers)
        seen.append((method, str(url)))
        return original(self, method, url, **kwargs)
    monkeypatch.setattr(TestClient, 'request', observe)
    result = prepare(tmp_path)
    root = Path(result['dataDir'])
    assert result['status'] == 'prepared'
    assert root.parent == tmp_path and result['modelExecuted'] is False
    assert result['archiveSupported'] is False
    assert check_manifest(root/'demo-manifest.json', root) == result
    with TestClient(create_media_review_demo(settings_for(result))) as client:
        assert client.app.state.image_ocr_runtime is None
        assert client.app.state.audio_asr_runtime is None
        base = '/api/v1/cases/'+CID
        for kind, run in [('image',result['imageRunId']),('audio',result['audioRunId'])]:
            response = client.get(base+'/'+kind+'-reviews/'+run)
            assert response.status_code == 200
            doc = response.json()
            assert doc['caseId'] == CID and doc['initial']['role'] == 'Investigator'
            assert doc['initial']['operator'] == 'Synthetic demo preparer'
        for key in ('image','audio'):
            response = client.post(base+'/evidence-intakes/'+result['receipts'][key]+':download',
                                   json={'purpose':'synthetic ordinary readback'})
            assert response.status_code == 200
            assert response.headers['X-Sha256'] == result['sha256'][key]
    # Inspect only this test's fresh database; no production DB, mutation or refusal probe.
    with sqlite3.connect(Path(result['dbFile']).as_uri()+'?mode=ro', uri=True) as db:
        roles = {json.loads(row[0])['role'] for row in db.execute('SELECT line FROM audit_events')}
    assert roles == {'Investigator'}
    assert len(seen) > 10
