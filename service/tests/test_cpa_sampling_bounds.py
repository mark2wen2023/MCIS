"""CPA request sampling must terminate before track/core work on invalid grids."""
from unittest.mock import Mock

import pytest

from mcis_service.colreg import router
from .conftest import C, H


@pytest.fixture
def sampling_spies(monkeypatch):
    pairs = Mock(return_value=[])
    core = Mock(return_value={'coreVersion': 'test', 'result': {'results': []}})
    monkeypatch.setattr(router, '_pairs_at', pairs)
    monkeypatch.setattr(router, '_core', core)
    # Safe red-baseline tripwire: abort an old unbounded loop after 5002 steps,
    # rather than testing it by exhausting memory or waiting indefinitely.
    native_round = round
    calls = 0
    def bounded_round(value, digits):
        nonlocal calls
        calls += 1
        assert calls <= 5002, 'sampling exceeded the safety tripwire'
        return native_round(value, digits)
    monkeypatch.setattr(router, 'round', bounded_round, raising=False)
    return pairs, core


@pytest.mark.parametrize('field', ['fromSec', 'toSec', 'stepSec'])
@pytest.mark.parametrize('value', ['nan', 'inf', '-inf', '1e309'])
def test_nonfinite_rejected_before_work(client, sampling_spies, field, value):
    response = client.get(f'{C}/cpa', params={field: value}, headers=H())
    assert response.status_code == 422 and response.json()['code'] == 'BAD_RANGE'
    for spy in sampling_spies:
        spy.assert_not_called()


@pytest.mark.parametrize('params', [
    {'fromSec': 'inf', 'toSec': 'inf'},
    {'fromSec': 1e308, 'toSec': 1e308, 'stepSec': 1},
    {'fromSec': 0, 'toSec': 0, 'stepSec': 1e-20},
    {'fromSec': 0, 'toSec': 1, 'stepSec': 0},
    {'fromSec': 0, 'toSec': 1, 'stepSec': -1},
    {'fromSec': 0, 'toSec': 5001, 'stepSec': 1},
])
def test_invalid_or_unbounded_grid_rejected(client, sampling_spies, params):
    response = client.get(f'{C}/cpa', params=params, headers=H())
    assert response.status_code == 422 and response.json()['code'] == 'BAD_RANGE'
    for spy in sampling_spies:
        spy.assert_not_called()


@pytest.mark.parametrize('start,end,step', [
    (0, 600, 15), (0, 5000, 1), (0, 1, .1), (0, 0, 1),
    (1, 0, 1), (-1, 1, .3), (0, 1 - 1e-10, .1),
    (0, 0, 1e-9), (0, 0, 1e-8), (1e308, 1e308, 1e308),
])
def test_valid_grid_unchanged(client, sampling_spies, start, end, step):
    expected, t = [], start
    while t <= end + 1e-9:
        expected.append(round(t, 3))
        t += step
    response = client.get(f'{C}/cpa', params={'fromSec': start, 'toSec': end, 'stepSec': step}, headers=H())
    assert response.status_code == 200
    assert sampling_spies[0].call_args.args[2] == expected
    sampling_spies[1].assert_called_once()


def test_default_end_and_permission_order(client, sampling_spies):
    response = client.get(f'{C}/cpa', params={'stepSec': 60}, headers=H())
    assert response.status_code == 200
    times = sampling_spies[0].call_args.args[2]
    assert times[0] == 0 and times[-1] == 720 and len(times) == 13
    for spy in sampling_spies:
        spy.reset_mock()
    assert client.get('/api/v1/cases/missing/cpa', params={'stepSec': 'nan'}, headers=H()).status_code == 404
    policy = client.get(f'{C}/access-policy', headers=H()).json()
    policy['matrix']['Public']['ais_sim'] = 'Deny'
    assert client.put(f'{C}/access-policy', json=policy, headers=H('LeadInvestigator')).status_code == 200
    assert client.get(f'{C}/cpa', params={'stepSec': 'nan'}, headers=H('Public')).status_code == 403
    for spy in sampling_spies:
        spy.assert_not_called()
