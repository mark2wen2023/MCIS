"""New ordinary synthetic launch preparation checks; no service/browser/model launch."""
import json
from pathlib import Path
import pytest
from tools.media_review_demo.prepare import prepare
from tools.media_review_demo.launch import check_manifest, checked_app, settings_for, summary, HOST, PORT


def test_prepared_manifest_metadata_and_disabled_app(tmp_path):
    doc=prepare(tmp_path);root=Path(doc['dataDir']);manifest=root/'demo-manifest.json'
    checked=check_manifest(manifest,root)
    assert checked==doc
    app,loaded=checked_app(manifest,root)  # app construction only, no server or TestClient startup
    assert loaded==doc
    assert app.state.image_ocr_runtime is None and app.state.audio_asr_runtime is None
    paths={getattr(r,'path',None) for r in app.routes}
    assert '/image-review-lab' in paths and '/audio-review-lab' in paths
    output=summary(doc)
    assert output['imageRunId']==doc['imageRunId'] and output['audioRunId']==doc['audioRunId']
    assert all(url.startswith('http://127.0.0.1:8766/') for url in output['pages'])
    assert output['sourceBytesVerified'] is False and output['browserVerified'] is False


def test_explicit_settings_ignore_default_database_and_seed(tmp_path,monkeypatch):
    doc=prepare(tmp_path)
    monkeypatch.setenv('MCIS_DB_URL','sqlite:////unused-demo-setting.db')
    monkeypatch.setenv('MCIS_DATA_DIR','/unused-demo-setting')
    monkeypatch.setenv('MCIS_SEED_DEMO','1')
    monkeypatch.setenv('MCIS_PORT','9999')
    settings=settings_for(doc)
    assert settings.resolved_db_url=='sqlite:///'+doc['dbFile']
    assert settings.data_dir==Path(doc['dataDir']) and settings.seed_demo is False
    assert settings.host==HOST=='127.0.0.1' and settings.port==PORT==8766


def test_incomplete_preparation_stops_before_app_creation(tmp_path):
    doc=prepare(tmp_path);root=Path(doc['dataDir']);manifest=root/'demo-manifest.json'
    # Ordinary incomplete-manifest fixture, not a file/DB write-refusal probe.
    doc['status']='incomplete-do-not-retry-in-place'
    manifest.write_text(json.dumps(doc))
    with pytest.raises(ValueError,match='preparation incomplete'):
        check_manifest(manifest,root)
    assert json.loads(manifest.read_text())['status']==doc['status']
