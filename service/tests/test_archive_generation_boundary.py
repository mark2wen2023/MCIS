"""Existing history boundary across repeated import, not trusted generation support."""
import base64
import hashlib
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from .conftest import C,H,make_settings
from .test_registered_align_preview import register,request,URL
from mcis_service.main import create_app


def upload(target, raw):
    encoded=base64.b64encode(raw).decode()
    return target.post('/api/v1/packages/intakes:commit',headers=H('LeadInvestigator'),json={'contentBase64':encoded,'sourceSha256':hashlib.sha256(raw).hexdigest(),'confirmed':True})


def source(client,empty_client):
    assert empty_client.post('/api/v1/cases',headers=H(),json=client.get(C,headers=H()).json()).status_code==201
    receipt=register(empty_client)
    exported=empty_client.get(C+'/export',headers=H('LeadInvestigator'))
    assert exported.status_code==200,exported.text
    return receipt,exported.content


def test_reexport_does_not_revive_historical_request(client,empty_client,tmp_path):
    receipt,original=source(client,empty_client)
    with TestClient(create_app(make_settings(tmp_path/'first',seed=False))) as first:
        assert upload(first,original).status_code==200
        replay=upload(first,original)
        assert replay.status_code==200 and replay.json()['replayed'] is True
        exported=first.get(C+'/export',headers=H('LeadInvestigator'))
        assert exported.status_code==200,exported.text
    with TestClient(create_app(make_settings(tmp_path/'second',seed=False))) as second:
        assert upload(second,exported.content).status_code==200
        replay=upload(second,original)
        assert replay.status_code==409,replay.text
        assert replay.json()['code']=='ARCHIVE_HISTORY_ONLY'
        preview=second.post(URL,headers=H('LeadInvestigator'),json=request(receipt))
        assert preview.status_code==409,preview.text
        assert preview.json()['code']=='ARCHIVE_HISTORY_ONLY'


def test_commit_failure_rolls_back_published_directory_and_history(client,empty_client,tmp_path,monkeypatch):
    _,original=source(client,empty_client)
    settings=make_settings(tmp_path/'failed',seed=False)
    with TestClient(create_app(settings)) as target:
        with monkeypatch.context() as patch:
            original_commit=Session.commit
            def fail_commit(self):
                if (settings.blob_dir/C.split('/')[-1]).exists():
                    raise RuntimeError('injected commit failure')
                return original_commit(self)
            patch.setattr(Session,'commit',fail_commit)
            result=upload(target,original)
            assert result.status_code==500,result.text
        assert not (settings.blob_dir/C.split('/')[-1]).exists()
        assert not list(settings.blob_dir.glob('.package-intake-*'))
        # Retry must perform a fresh import, not return a phantom persisted receipt.
        imported=upload(target,original)
        assert imported.status_code==200,imported.text
        assert imported.json()['replayed'] is False
