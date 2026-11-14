"""Synthetic offline unit fixtures; no intranet integration or model calls."""
import copy
import json
import socket
import subprocess
import sys
import pytest
from mcis_service.intranet_plan import build_plan


def sample():
    return {'sources': [{'id': 'demo', 'category': 'ais', 'transport': 'api',
                         'endpointRef': 'endpoint:demo', 'credentialRef': 'credential:demo'}],
            'case': {'caseId': 'SYNTHETIC', 'vessels': [{'kind': 'mmsi', 'value': '123456789'}],
                     'startUtc': '2026-01-01T00:00:00Z', 'endUtc': '2026-01-02T00:00:00Z'}}


def test_pure(monkeypatch):
    def forbidden(*a, **kw):
        pytest.fail('network forbidden')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)
    data = sample()
    before = copy.deepcopy(data)
    result = build_plan(data)
    assert data == before
    assert result['plans'][0]['status'] == 'planned_unverified'
    assert result['plans'][0]['executable'] is False
    assert result['executed'] is False
    assert result['scope'] == data['case']


@pytest.mark.parametrize('key', ['apiKey', 'password', 'token', 'headers', 'url', 'nested'])
def test_secrets(key):
    data = sample()
    data['sources'][0][key] = 'SYNTHETIC_SECRET_CANARY'
    result = build_plan(data)
    assert result['status'] == 'validation_failed'
    assert 'SYNTHETIC_SECRET_CANARY' not in json.dumps(result)


@pytest.mark.parametrize('value', ['https://user:pass@host', 'endpoint:a?token=x', 'Bearer secret', {}, 7])
def test_references(value):
    data = sample()
    data['sources'][0]['endpointRef'] = value
    assert build_plan(data)['status'] == 'validation_failed'


def test_states():
    data = sample()
    del data['sources'][0]['endpointRef']
    assert build_plan(data)['plans'][0]['status'] == 'blocked_unconfigured'
    data['case'] = {}
    assert build_plan(data)['pendingFields'] == ['caseId', 'vessels', 'startUtc', 'endUtc']
    assert build_plan(data)['plans'][0]['status'] == 'pending_input'
    data['sources'] = []
    assert 'sources' in build_plan(data)['pendingFields']


@pytest.mark.parametrize('days', [0, 367, True, '31', 1.5])
def test_limits(days):
    data = sample()
    data['sources'][0]['maxWindowDays'] = days
    assert build_plan(data)['status'] == 'validation_failed'


def test_boundary():
    data = sample()
    data['sources'][0]['maxWindowDays'] = 1
    assert build_plan(data)['plans'][0]['status'] == 'planned_unverified'
    data['case']['endUtc'] = '2026-01-02T00:00:00.000001Z'
    assert build_plan(data)['plans'][0]['status'] == 'range_exceeded'


@pytest.mark.parametrize('value', ['2026-01-02', '2026-01-02T00:00:00', 'garbage', {}, 12,
                                  '2025-01-01T00:00:00Z', '2026-01-01T00:00:00Z'])
def test_time(value):
    data = sample()
    data['case']['endUtc'] = value
    assert build_plan(data)['status'] == 'validation_failed'


@pytest.mark.parametrize('value', [None, [], '', 1, {'sources': [], 'case': []}])
def test_abnormal(value):
    assert build_plan(value)['status'] == 'validation_failed'


def test_cli():
    for raw in [b'{"sources":[],"sources":[],"case":{}}', b'{', b'['*2000, b'x'*65537, b'NaN']:
        run = subprocess.run([sys.executable, '-m', 'mcis_service.intranet_plan'], input=raw, capture_output=True)
        assert run.returncode == 4
        assert run.stderr == b''
        assert json.loads(run.stdout)['status'] == 'validation_failed'
