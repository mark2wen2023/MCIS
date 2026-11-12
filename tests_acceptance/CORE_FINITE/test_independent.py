"""Independent finite-JSON boundary acceptance, synthetic child output only."""
import hashlib
import json
import math
import random
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from mcis_service.colreg import core_client
from mcis_service.config import Settings
from mcis_service.main import create_app

MARKER = 'synthetic-only-output-marker'


def child(raw):
    return SimpleNamespace(stdout=raw.encode(), stderr=MARKER.encode(), returncode=0)


@pytest.fixture
def http(tmp_path):
    settings = Settings(data_dir=tmp_path, db_url=f'sqlite:///{tmp_path / "acceptance.db"}', seed_demo=False)
    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        yield client, tmp_path / 'acceptance.db'


@pytest.mark.parametrize('token', ['NaN', 'Infinity', '-Infinity', '1e309', '-9.9e9999'])
@pytest.mark.parametrize('place', ['nested', 'extension', 'error'])
@pytest.mark.parametrize('endpoint', ['version', 'align'])
def test_http_bad_numbers_return_redacted_502_without_db_mutation(http, token, place, endpoint):
    client, db = http
    if place == 'nested':
        raw = '{"ok":true,"result":{"deep":[{"v":' + token + '}]},"note":"' + MARKER + '"}'
    elif place == 'extension':
        raw = '{"ok":true,"result":{},"unknown":[null,' + token + '],"note":"' + MARKER + '"}'
    else:
        raw = '{"ok":false,"error":{"code":"BAD_REQUEST","message":"' + MARKER + '","detail":' + token + '}}'
    before = hashlib.sha256(db.read_bytes()).digest()
    with patch.object(core_client.subprocess, 'run', return_value=child(raw)):
        response = client.get('/api/v1/core/version') if endpoint == 'version' else client.post('/api/v1/core/align', json={})
    assert response.status_code == 502, response.text
    assert response.json() == {'code':'CORE_BAD_OUTPUT', 'message':'计算核心返回无效结果。'}
    assert MARKER not in response.text
    assert hashlib.sha256(db.read_bytes()).digest() == before


@pytest.mark.parametrize('token', ['-0.0', '1.7976931348623157e308', '-1.7976931348623157e308', '4.9406564584124654e-324', '-1e-9999', '1234567890123456789012345678901234567890'])
def test_numeric_boundary_decoding_exactly_matches_standard_json(token):
    raw = '{"ok":true,"coreVersion":"test","result":{"n":' + token + '}}'
    with patch.object(core_client.subprocess, 'run', return_value=child(raw)):
        result = core_client.run('/synthetic-only', 'version', {})
    expected = json.loads(raw)
    assert result == expected
    a, b = result['result']['n'], expected['result']['n']
    assert type(a) is type(b)
    if isinstance(a, float):
        assert a.hex() == b.hex()
        assert math.isfinite(a)


def test_random_finite_json_roundtrip_and_protocol():
    rng = random.Random(20261112)
    for _ in range(400):
        number = math.ldexp(rng.uniform(-1, 1), rng.randrange(-1074, 1024))
        envelope = {'ok':True, 'coreVersion':'test', 'result':{'n':[number, rng.randrange(-10**50, 10**50), None, True]},
                    'extension':{'strings':['NaN', 'Infinity', '-Infinity', '1e309', '汉字']}}
        raw = 'preamble NaN Infinity 1e309\n' + json.dumps(envelope, allow_nan=False, ensure_ascii=False) + '\n'
        with patch.object(core_client.subprocess, 'run', return_value=child(raw)):
            actual = core_client.run('/synthetic-only', 'version', {})
        assert actual == envelope
        assert actual['result']['n'][0].hex() == number.hex()
        assert json.dumps(actual, allow_nan=False) == json.dumps(envelope, allow_nan=False)


@pytest.mark.parametrize('code,status', [('BAD_REQUEST',422),('BAD_JSON',422),('UNKNOWN_COMMAND',501),('NOT_IMPLEMENTED',501),('other',502)])
def test_valid_error_mapping_and_finite_extensions_preserved(code, status):
    raw = json.dumps({'ok':False, 'error':{'code':code, 'message':'domain', 'extra':-0.0}, 'extension':{'value':1e308}})
    with patch.object(core_client.subprocess, 'run', return_value=child(raw)):
        with pytest.raises(core_client.CoreError) as exc:
            core_client.run('/synthetic-only', 'align', {})
    assert (exc.value.code, exc.value.message, exc.value.http_status) == (code, 'domain', status)


def test_http_valid_strings_and_finite_envelope_unchanged(http):
    client, _ = http
    env = {'ok':True, 'coreVersion':'test', 'command':'version', 'result':{'n':1e308}, 'extension':['NaN','Infinity','1e309']}
    with patch.object(core_client.subprocess, 'run', return_value=child(json.dumps(env))):
        response = client.get('/api/v1/core/version')
    assert response.status_code == 200
    assert response.json() == env
