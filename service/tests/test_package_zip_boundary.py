"""Synthetic ZIP decoder boundaries; never read host files or extract a ZIP."""
import io
import struct
import warnings
import zipfile

import pytest
from fastapi import HTTPException

from mcis_service.package.mcase import read_zip


def archive(entries, compression=zipfile.ZIP_STORED):
    out = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        with zipfile.ZipFile(out, 'w', compression) as z:
            for name, body in entries:
                z.writestr(name, body)
    return out.getvalue()


def mutate_headers(data, offset, value, fmt='<H'):
    data = bytearray(data)
    for signature, position in [(b'PK\x03\x04', offset[0]), (b'PK\x01\x02', offset[1])]:
        at = data.index(signature)
        struct.pack_into(fmt, data, at + position, value)
    return bytes(data)


@pytest.mark.parametrize('entries', [
    [('case.json', b'a'), ('case.json', b'b')],
    [('raw/a', b'a'), ('raw\\a', b'b')],
    [('Case.json', b'a'), ('case.json', b'b')],
    [('raw/a', b'a'), ('RAW/A', b'a')],
    [('raw/', b''), ('raw', b'file')],
])
def test_duplicate_or_ambiguous_paths_are_bad_package(entries):
    with pytest.raises(HTTPException) as exc:
        read_zip(archive(entries))
    assert exc.value.status_code == 422
    assert exc.value.detail['code'] == 'BAD_PACKAGE'


@pytest.mark.parametrize('name', ['/absolute', '../up', 'raw/../up', 'C:/tmp/x', 'raw/a:stream', './case.json',
    'raw//a', 'raw/./a', '../bad/', '/bad/', 'C:\\bad\\', 'raw\\..\\x'])
def test_unsafe_paths_including_directories_are_rejected(name):
    with pytest.raises(HTTPException) as exc:
        read_zip(archive([(name, b'')]))
    assert exc.value.status_code == 422
    assert exc.value.detail['code'] == 'BAD_PACKAGE'


def malformed_archives():
    good = archive([('case.json', b'synthetic-test-payload')])
    corrupt = good.replace(b'synthetic-test-payload', b'corrupted-test-payloa!')
    encrypted = mutate_headers(good, (6, 8), 1)
    unsupported = mutate_headers(good, (8, 10), 99)
    nul = good.replace(b'case.json', b'case\x00json')
    return [b'not a zip', good[:-10], corrupt, encrypted, unsupported, nul]


@pytest.mark.parametrize('data', malformed_archives())
@pytest.mark.parametrize('endpoint', ['/api/v1/packages:verify', '/api/v1/cases:import'])
def test_malformed_zip_http_422_no_writes(empty_client, data, endpoint):
    response = empty_client.post(endpoint, content=data)
    assert response.status_code == 422, response.text
    assert response.json()['code'] == 'BAD_PACKAGE'
    assert empty_client.get('/api/v1/cases').json() == []
    assert 'Traceback' not in response.text


@pytest.mark.parametrize('compression', [zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED, zipfile.ZIP_BZIP2, zipfile.ZIP_LZMA])
def test_valid_zip_preserves_exact_bytes_and_backslash_compatibility(compression):
    data = archive([('raw/', b''), ('case.json', b'{}'), ('raw\\传感器.bin', bytes(range(256)))], compression)
    assert read_zip(data) == {'case.json': b'{}', 'raw/传感器.bin': bytes(range(256))}


def test_empty_zip_keeps_missing_manifest_integrity_behavior(empty_client):
    r = empty_client.post('/api/v1/packages:verify', content=archive([]))
    assert r.status_code == 200
    assert r.json()['missingFiles'] == ['manifest.json']
