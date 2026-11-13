"""Source clock syntax only; no calibration or uncertainty claims."""
import pytest
from .conftest import C, H
from .test_registered_align_preview import register, request, URL, RAW
from .test_align_preview_w41 import result
from mcis_service.timeline import align_preview


@pytest.mark.parametrize('offset', ['+00:60', '-00:60', '+01:99', '-01:99', '+14:01', '-14:01'])
def test_malformed_or_unsupported_offsets_stop_before_core(client, monkeypatch, offset):
    receipt = register(client, RAW.replace(b'00Z', ('00'+offset).encode()))
    def unexpected(*args):
        raise AssertionError('malformed timestamp must not reach core')
    monkeypatch.setattr(align_preview, 'core_run', unexpected)
    response = client.post(URL, headers=H(), json=request(receipt))
    assert response.status_code == 422
    assert response.json()['code'] == 'TIMELINE_SOURCE_CSV'


@pytest.mark.parametrize('offset', ['Z', '+00:00', '-00:00', '+00:59', '-00:59', '+14:00', '-14:00'])
def test_valid_offset_original_spelling_reaches_core_unchanged(client, monkeypatch, offset):
    raw = RAW.replace(b'00Z', ('00'+offset).encode())
    receipt = register(client, raw)
    captured = []
    def core(*args):
        captured.append(args[2]['sources'][0]['text'])
        return result(args[2])
    monkeypatch.setattr(align_preview, 'core_run', core)
    response = client.post(URL, headers=H(), json=request(receipt))
    assert response.status_code == 200, response.text
    assert captured == [raw.decode()]
    path = client.app.state.settings.blob_dir / receipt['caseId'] / receipt['evidence']['relativePath']
    assert path.read_bytes() == raw
