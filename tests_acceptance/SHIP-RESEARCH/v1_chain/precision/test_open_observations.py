"""研究边界的候选验收断言；当前红项应保留。使用合成三角形。"""
import math

import pytest

from test_precision_contracts import bind_asset, export_glb, narrow, triangle, with_extras, world_points


@pytest.mark.parametrize("source_x, origin_x", [(1e-13, 16384.), (1.,2.**54)], ids=["tiny_shift","extreme_offset"])
def test_zero_vertex_budget_after_world_restoration(source_x, origin_x):
    points = [[source_x,0,0],[source_x,1,0],[source_x,0,1]]
    origin = [origin_x,0,0]
    try:
        glb, side = export_glb(triangle(points), local_origin_m=origin, max_vertex_error_m=0)
    except ValueError as exc:
        assert any(word in str(exc).lower() for word in ('precision', 'origin', 'roundtrip'))
        return
    world = world_points(glb, origin)
    measured = max(math.dist(r,p) for r,p in zip(world,points))
    assert measured == 0, f"whole-frame zero budget exceeded: {measured} m"
    assert side["precision"]["max_vertex_error_m"] == measured


@pytest.mark.parametrize("stored,side_value", [(None,None), ("unknown","unknown"),([1,0,0],[True,0,0])],
                         ids=["both_null","both_string","bool_agrees_with_one"])
def test_origin_type_consistent_with_exporter(stored,side_value):
    glb, side = export_glb(narrow())
    glb = with_extras(glb,lambda ex: ex.update(mcis_origin_m=stored))
    side["mcis_origin_m"] = side_value
    with pytest.raises(ValueError,match="origin"):
        bind_asset(glb, side, algorithm_version="synthetic")
