"""Independent ZIP-boundary acceptance, synthetic archives and temporary database only."""
import hashlib
import io
import json
import random
import struct
import sys
import warnings
import zipfile
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'service'))
from mcis_service.config import Settings
from mcis_service.main import create_app
from mcis_service.package import mcase


def pack(entries, mode=zipfile.ZIP_DEFLATED):
    stream = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        with zipfile.ZipFile(stream, 'w', compression=mode) as z:
            for name, value in entries:
                z.writestr(name, value)
    return stream.getvalue()


def patched_archive(kind):
    b = bytearray(pack([('case.json', b'{"caseId":"CASE-SYNTHETIC"}')], zipfile.ZIP_STORED))
    cd = b.index(b'PK\x01\x02')
    if kind == 'encrypted':
        struct.pack_into('<H', b, 6, 1); struct.pack_into('<H', b, cd + 8, 1)
    elif kind == 'compression':
        struct.pack_into('<H', b, 8, 512); struct.pack_into('<H', b, cd + 10, 512)
    elif kind == 'crc':
        b[39] ^= 1
    elif kind == 'nul':
        b = b.replace(b'case.json', b'case\0json')
    elif kind == 'mismatched-name':
        b[30] = ord('X')
    elif kind == 'utf8-name':
        struct.pack_into('<H', b, 6, 2048); struct.pack_into('<H', b, cd + 8, 2048)
        b[30] = 255; b[cd + 46] = 255
    return bytes(b)


def invalid_payloads():
    yield 'not-zip', b'INVALID-SYNTHETIC-ARCHIVE'
    yield 'truncated', pack([('case.json', b'{}')])[:-16]
    for kind in ['encrypted', 'compression', 'crc', 'nul', 'mismatched-name', 'utf8-name']:
        yield kind, patched_archive(kind)
    for name in ['../raw/data', '/raw/x', 'C:/x', 'C:\\x', 'raw/a:stream', 'raw/./x', 'raw//x', '../empty/', './', '\\server\\share\\x']:
        yield name, pack([(name, b'data')])
    for names in [('raw/x', 'raw/x'), ('raw/x', 'raw\\x'), ('RAW/x', 'raw/X'), ('raw/x/', 'raw/x')]:
        yield repr(names), pack([(n, b'data') for n in names])


@pytest.fixture
def isolated(tmp_path):
    settings = Settings(data_dir=tmp_path / 'data', seed_demo=False)
    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        yield client, settings


@pytest.mark.parametrize('name,data', list(invalid_payloads()))
@pytest.mark.parametrize('endpoint', ['packages:verify', 'cases:import'])
def test_http_invalid_archive_rejects_without_case_or_blob(isolated, name, data, endpoint):
    client, settings = isolated
    response = client.post('/api/v1/' + endpoint, content=data)
    assert response.status_code == 422, (name, response.text)
    assert response.json()['code'] == 'BAD_PACKAGE'
    assert client.get('/api/v1/cases').json() == []
    assert not settings.blob_dir.exists() or not any(p.is_file() for p in settings.blob_dir.rglob('*'))
    assert 'Traceback' not in response.text and 'case.json' not in response.text


@pytest.mark.parametrize('mode', [zipfile.ZIP_DEFLATED, zipfile.ZIP_BZIP2, zipfile.ZIP_LZMA])
def test_corrupt_compression_stream_is_controlled(mode):
    b = bytearray(pack([('raw/data.bin', bytes(range(256)) * 4)], mode))
    fnlen, extra = struct.unpack_from('<HH', b, 26)
    start = 30 + fnlen + extra
    b[start:start+8] = b'\xff' * 8
    with pytest.raises(HTTPException) as err:
        mcase.read_zip(bytes(b))
    assert err.value.status_code == 422 and err.value.detail['code'] == 'BAD_PACKAGE'


def test_full_inventory_is_checked_before_reading(monkeypatch):
    b = pack([('raw/valid.bin', b'payload'), ('raw/../invalid.bin', b'bad')])
    def forbidden(*args, **kwargs):
        pytest.fail('content was decoded before validating all member names')
    monkeypatch.setattr(zipfile.ZipFile, 'read', forbidden)
    with pytest.raises(HTTPException) as err:
        mcase.read_zip(b)
    assert err.value.detail['code'] == 'BAD_PACKAGE'


def test_zip_context_closes_on_success_and_error(monkeypatch):
    real = zipfile.ZipFile
    opened = []
    class ObservedZip(real):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            opened.append(self)
    good = pack([('raw/ok', b'ok')]); bad = pack([('../bad', b'bad')])
    monkeypatch.setattr(zipfile, 'ZipFile', ObservedZip)
    assert mcase.read_zip(good) == {'raw/ok': b'ok'}
    with pytest.raises(HTTPException):
        mcase.read_zip(bad)
    assert len(opened) == 2 and all(z.fp is None for z in opened)


@pytest.mark.parametrize('mode', [0, 8, 12, 14])
def test_supported_compression_preserves_random_bytes(mode):
    rng = random.Random(7913)
    for n in range(30):
        blobs = {'case.json': b'{}', 'raw/船.bin': rng.randbytes(n * 31), 'raw/empty': b''}
        entries = [('raw/', b''), ('case.json', blobs['case.json']), ('raw\\船.bin', blobs['raw/船.bin']), ('raw/empty', b'')]
        assert mcase.read_zip(pack(entries, mode)) == blobs


@pytest.mark.parametrize('mode', [0, 8, 12, 14])
def test_minimal_unity_import_and_export_roundtrip(isolated, mode):
    client, _ = isolated
    case = {'caseId': 'CASE-INDEPENDENT', 'title': 'Synthetic only', 'isFictionalDemo': True}
    content = json.dumps(case).encode()
    manifest = {'packageFormat': 'MCIS-MCASE', 'caseId': case['caseId'], 'files': [
        {'relativePath': 'case.json', 'sha256': hashlib.sha256(content).hexdigest(), 'sizeBytes': len(content)}]}
    blob = pack([('case.json', content), ('manifest.json', json.dumps(manifest).encode()), ('raw/', b'')], mode)
    verify = client.post('/api/v1/packages:verify', content=blob)
    assert verify.status_code == 200 and verify.json()['isValid']
    imported = client.post('/api/v1/cases:import', content=blob)
    assert imported.status_code == 201, imported.text
    exported = client.get('/api/v1/cases/CASE-INDEPENDENT/export')
    assert exported.status_code == 200
    assert json.loads(mcase.read_zip(exported.content)['case.json'])['caseId'] == case['caseId']
    assert client.post('/api/v1/packages:verify', content=exported.content).json()['isValid']


def test_missing_manifest_behavior_stays_integrity_report(isolated):
    client, _ = isolated
    r = client.post('/api/v1/packages:verify', content=pack([]))
    assert r.status_code == 200 and not r.json()['isValid']
    assert r.json()['missingFiles'] == ['manifest.json']


@pytest.mark.parametrize('paths', [('raw/a', 'raw/a/b'), ('raw/a/b', 'raw/a'), ('raw/A', 'raw/a/b')])
def test_file_ancestor_is_ambiguous_before_import(isolated, paths):
    client, settings = isolated
    files = {'case.json': json.dumps({'caseId': 'CASE-ANCESTOR', 'isFictionalDemo': True}).encode()}
    files.update({path: b'synthetic' for path in paths})
    manifest = {'caseId': 'CASE-ANCESTOR', 'packageFormat': 'MCIS-MCASE', 'files': [
        {'relativePath': path, 'sha256': hashlib.sha256(body).hexdigest(), 'sizeBytes': len(body)}
        for path, body in files.items()]}
    blob = pack([*files.items(), ('manifest.json', json.dumps(manifest).encode())])
    response = client.post('/api/v1/cases:import', content=blob)
    assert response.status_code == 422, response.text
    assert response.json()['code'] == 'BAD_PACKAGE'
    assert not settings.blob_dir.exists() or not any(p.is_file() for p in settings.blob_dir.rglob('*'))
