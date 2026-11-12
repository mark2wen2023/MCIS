"""Non-finite core output must not escape the process-response boundary."""
import json
from types import SimpleNamespace

import pytest
from mcis_service.colreg import core_client


@pytest.mark.parametrize('literal', ['NaN', 'Infinity', '-Infinity', '1e309', '-1e309'])
@pytest.mark.parametrize('location', ['result', 'extension', 'error'])
def test_nonfinite_core_output_rejected(monkeypatch, literal, location):
    prefix = '{"ok":true,"coreVersion":"synthetic","result":{}'
    if location == 'result':
        raw = '{"ok":true,"result":{"items":[{"value":' + literal + '}]}}'
    elif location == 'error':
        raw = '{"ok":false,"error":{"code":"BAD_REQUEST","message":"x","detail":' + literal + '}}'
    else:
        raw = prefix + ',"extension":' + literal + '}'
    monkeypatch.setattr(core_client.subprocess, 'run', lambda *a, **k: SimpleNamespace(
        stdout=raw.encode(), stderr=b'', returncode=0))
    with pytest.raises(core_client.CoreError) as exc:
        core_client.run('/synthetic', 'cpa', {})
    assert (exc.value.code, exc.value.http_status) == ('CORE_BAD_OUTPUT', 502)


@pytest.mark.parametrize('literal', ['0.0', '-0.0', '1.7976931348623157e308', '-1.7976931348623157e308',
                                     '5e-324', '1e-999', '123456789012345678901234567890', '"NaN Infinity 1e309"'])
def test_finite_json_and_strings_preserved(monkeypatch, literal):
    raw = '{"ok":true,"coreVersion":"synthetic","result":{"value":' + literal + '},"extra":[true,null]}'
    monkeypatch.setattr(core_client.subprocess, 'run', lambda *a, **k: SimpleNamespace(
        stdout=b'build preamble\n' + raw.encode() + b'\n', stderr=b'', returncode=0))
    actual = core_client.run('/synthetic', 'cpa', {})
    assert actual == json.loads(raw)
    assert json.dumps(actual, allow_nan=False) == json.dumps(json.loads(raw), allow_nan=False)
