import math
import pytest
pytest.importorskip('scipy')
from mcis_service.agents.skills.ship_reconstruction.hull_benchmark import benchmark

def test_quadratic_benchmark():
    result=benchmark()
    assert result['research_only'] is True
    assert result['lofting_authorized'] is False
    metrics=result['metrics']
    assert set(metrics)=={'linear','pchip','bspline'}
    for m in metrics.values():
        assert m['count']==20
        assert all(math.isfinite(m[k]) for k in ('mae_m','rmse_m','max_abs_m'))
        assert 0<=m['mae_m']<=m['rmse_m']+1e-12<=m['max_abs_m']+2e-12
    assert metrics['linear']['max_abs_m']==pytest.approx(.0015625)
    assert metrics['pchip']['rmse_m']<metrics['linear']['rmse_m']
    assert metrics['bspline']['max_abs_m']<1e-12
