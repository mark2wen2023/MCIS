"""New ordinary synthetic preparation tests; no model/browser or refusal probes."""
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from mcis_service.config import Settings
from mcis_service.media_review_demo import create_media_review_demo
from tools.media_review_demo.prepare import prepare, checked_public, CID


def test_fresh_preparation_reopens_pending_image_and_audio(tmp_path):
    result=prepare(tmp_path);root=Path(result['dataDir'])
    assert result['status']=='prepared' and result['modelExecuted'] is False
    assert result['imageOrigin'].startswith('generated') and result['audioOrigin'].startswith('generated')
    settings=Settings(data_dir=root,db_url=f'sqlite:///{root / "demo.db"}',seed_demo=False)
    with TestClient(create_media_review_demo(settings)) as c:
        base='/api/v1/cases/'+CID
        im=c.get(base+'/image-reviews/'+result['imageRunId']);au=c.get(base+'/audio-reviews/'+result['audioRunId'])
        assert im.status_code==au.status_code==200
        assert im.json()['initial']['candidate']['recognizer']['pipeline']=='synthetic-not-executed'
        assert au.json()['initial']['machineDraft']['receipt']['origin']=='synthetic_contract_fixture'
        assert au.json()['initial']['machineDraft']['transcript']['segments']==[]
        for key,signature in [('image',b'\x89PNG'),('pdf',b'%PDF'),('audio',b'RIFF')]:
            r=c.post(base+'/evidence-intakes/'+result['receipts'][key]+':download',json={'purpose':'ordinary synthetic fixture readback'})
            assert r.status_code==200 and r.content.startswith(signature)
            assert r.headers['X-Sha256']==result['sha256'][key]
    assert json.loads((root/'demo-manifest.json').read_text())==result


def test_each_run_uses_new_directory_and_ignores_database_environment(tmp_path,monkeypatch):
    monkeypatch.setenv('MCIS_DB_URL','sqlite:////nonexistent-synthetic-location/do-not-use.db')
    monkeypatch.setenv('MCIS_DATA_DIR','/nonexistent-synthetic-location')
    monkeypatch.setenv('MCIS_SEED_DEMO','1')
    a=prepare(tmp_path);b=prepare(tmp_path)
    assert a['dataDir']!=b['dataDir']
    for r in (a,b):
        assert Path(r['dataDir']).parent==tmp_path and Path(r['dbFile']).is_file()
        settings=Settings(data_dir=Path(r['dataDir']),db_url=f"sqlite:///{r['dbFile']}",seed_demo=False)
        with TestClient(create_media_review_demo(settings)) as c:
            assert [x['caseId'] for x in c.get('/api/v1/cases').json()]==[CID]


def test_missing_public_inputs_stop_before_preparation(tmp_path):
    paths={k:tmp_path/(k+'.missing') for k in ('audio','license','result')}
    with pytest.raises(FileNotFoundError):prepare(tmp_path,paths)
    assert list(tmp_path.iterdir())==[]


def test_public_digest_mismatch_is_not_treated_as_verified(tmp_path):
    paths={k:tmp_path/(k+'.fixture') for k in ('audio','license','result')}
    for path in paths.values():path.write_bytes(b'explicit synthetic incorrect input')
    with pytest.raises(ValueError,match='digest mismatch'):checked_public(paths)
