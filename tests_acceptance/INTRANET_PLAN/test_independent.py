"""Independent offline acceptance. All identifiers/endpoints are synthetic fixtures."""
import copy
import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest

SERVICE = Path(__file__).resolve().parents[2] / 'service'
sys.path.insert(0, str(SERVICE))
from mcis_service.intranet_plan import build_plan


def request():
    return {'sources': [{'id': 'fixture', 'category': 'ais', 'transport': 'api',
                        'endpointRef': 'endpoint:fixture', 'credentialRef': 'credential:fixture',
                        'maxWindowDays': 1}],
            'case': {'caseId': 'FICTIONAL-ACCEPTANCE', 'vessels': [{'kind': 'imo', 'value': '9074729'}],
                     'startUtc': '2026-01-01T08:00:00+08:00', 'endUtc': '2026-01-02T00:00:00Z'}}


def test_no_network_no_mutation(monkeypatch):
    def denied(*a, **kw):
        pytest.fail('network access attempted')
    monkeypatch.setattr(socket, 'socket', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)
    data = request()
    before = copy.deepcopy(data)
    result = build_plan(data)
    assert data == before
    assert result['scope']['startUtc'] == '2026-01-01T00:00:00Z'
    assert result['scope']['vessels'] == data['case']['vessels']
    assert result['scope']['caseId'] == data['case']['caseId']
    assert result['plans'][0]['status'] == 'planned_unverified'
    assert not result['plans'][0]['executable']
    assert not result['networkAttempted'] and not result['executed']


@pytest.mark.parametrize('key', ['apiKey', 'password', 'token', 'headers', 'url', 'nested'])
def test_secret_field_fails_without_echo(key):
    data = request()
    data['sources'][0][key] = {'secret': 'SYNTHETIC-DO-NOT-ECHO'}
    result = build_plan(data)
    assert result['status'] == 'validation_failed'
    assert 'SYNTHETIC' not in json.dumps(result)
    assert 'sources' not in result


@pytest.mark.parametrize('ref', ['https://user:pass@fixture.invalid/', 'endpoint:foo?token=synthetic', 'credential:foo/bar', 'endpoint:$(echo unsafe)', 4, {}, []])
def test_references_reject_values(ref):
    data = request()
    data['sources'][0]['endpointRef'] = ref
    assert build_plan(data)['status'] == 'validation_failed'


@pytest.mark.parametrize('field,value', [('startUtc', '2026-01-01'), ('startUtc', '2026-01-03T00:00:00Z'), ('endUtc', '2026-01-01T00:00:00Z'), ('vessels', [{'kind': 'imo', 'value': '9074728'}]), ('vessels', [{'kind': 'mmsi', 'value': '000000000'}]), ('caseId', {'name': 'unknown'})])
def test_bad_scope(field, value):
    data = request()
    data['case'][field] = value
    assert build_plan(data)['status'] == 'validation_failed'


def test_boundary_and_pending():
    data = request()
    assert build_plan(data)['plans'][0]['status'] == 'planned_unverified'
    data['case']['endUtc'] = '2026-01-02T00:00:00.000001Z'
    assert build_plan(data)['plans'][0]['status'] == 'range_exceeded'
    data['case'] = {}
    result = build_plan(data)
    assert set(result['pendingFields']) == {'caseId', 'vessels', 'startUtc', 'endUtc'}
    assert result['plans'][0]['status'] == 'pending_input'
    assert result['scope']['vessels'] == []


def test_states_and_all_categories():
    data = request()
    data['sources'] = [dict(id='s'+str(i), category=category, transport='api' if i%2 else 'mcp')
                       for i, category in enumerate(['ship_parameters', 'ais', 'company', 'regulatory'])]
    result = build_plan(data)
    assert result['unconfiguredCategories'] == []
    assert all(s['status'] == 'unconfigured' for s in result['sources'])
    assert all(p['status'] == 'blocked_unconfigured' and not p['executable'] for p in result['plans'])


@pytest.mark.parametrize('days', [True, 0, -1, 367, 1.0, '1'])
def test_range_config(days):
    data = request()
    data['sources'][0]['maxWindowDays'] = days
    assert build_plan(data)['status'] == 'validation_failed'


def test_duplicates_and_capacity():
    data = request()
    data['sources'] *= 2
    assert build_plan(data)['status'] == 'validation_failed'
    data = request()
    data['case']['vessels'] *= 2
    assert build_plan(data)['status'] == 'validation_failed'
    data = request()
    data['sources'] = [dict(data['sources'][0], id='s'+str(i)) for i in range(33)]
    assert build_plan(data)['status'] == 'validation_failed'


@pytest.mark.parametrize('raw', [b'{"sources":[],"sources":[],"case":{}}', b'{', b'NaN', b'\xff', b'['*2000, b' '*65537])
def test_cli_safe_failure(raw):
    done = subprocess.run([sys.executable, '-m', 'mcis_service.intranet_plan'], input=raw,
                          capture_output=True, cwd=SERVICE, timeout=10)
    assert done.returncode == 4
    assert done.stderr == b''
    assert json.loads(done.stdout)['status'] == 'validation_failed'
