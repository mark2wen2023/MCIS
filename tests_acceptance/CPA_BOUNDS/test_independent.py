"""Independent CPA sampler acceptance: bounded work and legacy-grid parity."""
from contextlib import nullcontext
import hashlib
import math
from pathlib import Path
import random
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'service'))
from mcis_service.colreg import router
from mcis_service.config import Settings
from mcis_service.main import create_app


@pytest.fixture
def direct(monkeypatch):
    case = {'durationSec': 720, 'incidentLocation': {'latDeg': 0, 'lonDeg': 0}}
    load = Mock(return_value=case)
    require = Mock()
    pairs = Mock(return_value=[])
    core = Mock(return_value={'coreVersion': 'synthetic', 'result': {'results': []}})
    monkeypatch.setattr(router.cases, 'load_case', load)
    monkeypatch.setattr(router, 'require', require)
    monkeypatch.setattr(router, '_pairs_at', pairs)
    monkeypatch.setattr(router, '_core', core)
    ctx = SimpleNamespace(db=SimpleNamespace(session=lambda: nullcontext(object())))
    return ctx, case, load, require, pairs, core


def invoke(direct, start=0., end=None, step=15.):
    return router.cpa_series('SYNTHETIC', direct[0], start, end, step)


@pytest.mark.parametrize('duration', [math.nan, math.inf, -math.inf])
def test_nonfinite_stored_duration_rejected(direct, duration):
    direct[1]['durationSec'] = duration
    with pytest.raises(HTTPException) as err:
        invoke(direct)
    assert (err.value.status_code, err.value.detail['code']) == (422, 'BAD_RANGE')
    direct[4].assert_not_called()
    direct[5].assert_not_called()


@pytest.mark.parametrize('start,end,step', [
    (0., 0., math.ulp(0.)),
    (2.**100, 2.**100, 1.),
    (-2.**100, -2.**100, 1.),
    (math.inf, math.inf, 1.),
    (0., 0., 1e-15),
])
def test_hard_budget_before_interpolation(direct, monkeypatch, start, end, step):
    native_round = round
    seen = []
    def count_round(t, n):
        seen.append(t)
        assert len(seen) <= 5001
        return native_round(t, n)
    monkeypatch.setattr(router, 'round', count_round, raising=False)
    with pytest.raises(HTTPException) as err:
        invoke(direct, start, end, step)
    assert err.value.status_code == 422 and err.value.detail['code'] == 'BAD_RANGE'
    direct[4].assert_not_called()
    direct[5].assert_not_called()


def test_random_finite_legacy_grids_match_exactly(direct):
    rng = random.Random(20261112)
    for _ in range(400):
        start = rng.uniform(-1000, 1000)
        step = rng.choice([.001, .03, .1, .25, 1., 15., 60.])
        end = start + rng.randint(-5, 300) * step + rng.choice([0., 1e-10, -1e-10])
        expected, t = [], start
        for _ in range(5002):
            if t > end + 1e-9:
                break
            expected.append(round(t, 3))
            t += step
        else:
            pytest.fail('invalid independent reference grid')
        assert invoke(direct, start, end, step)['coreVersion'] == 'synthetic'
        assert direct[4].call_args.args[2] == expected


@pytest.mark.parametrize('end,status,count', [(5000., 200, 5001), (5000.0000001, 422, None), (4999.999999999, 200, 5001)])
def test_interval_boundary(direct, end, status, count):
    if status == 422:
        with pytest.raises(HTTPException) as err:
            invoke(direct, 0., end, 1.)
        assert err.value.status_code == 422
        direct[4].assert_not_called()
    else:
        invoke(direct, 0., end, 1.)
        assert len(direct[4].call_args.args[2]) == count


@pytest.mark.parametrize('role', ['LeadInvestigator','Investigator','ExternalExpert','InterestedState','AgentService','Public'])
def test_http_invalid_requests_leave_database_unchanged(tmp_path, monkeypatch, role):
    settings = Settings(data_dir=tmp_path, db_url=f'sqlite:///{tmp_path / "test.db"}', seed_demo=True)
    core = Mock(side_effect=AssertionError('invalid request reached core'))
    pairs = Mock(side_effect=AssertionError('invalid request reached interpolation'))
    monkeypatch.setattr(router, '_core', core)
    monkeypatch.setattr(router, '_pairs_at', pairs)
    with TestClient(create_app(settings)) as client:
        db = tmp_path / 'test.db'
        before = hashlib.sha256(db.read_bytes()).digest()
        for query in ['fromSec=Infinity&toSec=Infinity', 'fromSec=NaN', 'stepSec=1e-320&toSec=0', 'fromSec=1e300&toSec=1e300&stepSec=1']:
            response = client.get('/api/v1/cases/CASE-2026-DEMO-LILY-MARY/cpa?' + query, headers={'X-MCIS-Role': role})
            assert response.status_code == 422, response.text
            assert response.json()['code'] == 'BAD_RANGE'
        assert hashlib.sha256(db.read_bytes()).digest() == before
        core.assert_not_called()
        pairs.assert_not_called()
