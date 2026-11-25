"""合成几何的读回、证据和授权专项验收。MCIS_SOURCE_TREE 指向待测源码。"""
import io
import json
import math
import os
from pathlib import Path
import struct
import sys

import numpy as np
import pytest
import trimesh

sys.path.insert(0, str(Path(os.environ["MCIS_SOURCE_TREE"]).resolve() / "service"))
from mcis_service.agents.skills.ship_reconstruction.asset_integrity import bind_asset, verify_asset
from mcis_service.agents.skills.ship_reconstruction.glb_export import export_glb


def triangle(points):
    return {
        "mesh": {"vertices_m": points, "triangles": [[0, 1, 2]]},
        "provenance": {"faces": [{"face_id": 0, "sources": [{"document_id": "SYNTH", "locator": "F0"}],
                                  "cell_review": {"document_id": "SYNTH", "locator": "C0", "review": "accepted"}}]},
        "research_only": True, "lofting_authorized": False,
    }


def narrow():
    return triangle([[16384., 0., 0.], [16384.001, 0., 0.], [16384., 1., 0.]])


def world_points(glb, origin):
    loaded = trimesh.load(io.BytesIO(glb), file_type="glb", force="mesh", process=False)
    assert loaded.faces.tolist() == [[0, 1, 2]]
    gltf = loaded.vertices
    return np.column_stack([gltf[:, 0], -gltf[:, 2], gltf[:, 1]]) + origin


def read_metrics(expected, actual):
    expected, actual = np.asarray(expected), np.asarray(actual)
    lengths = lambda p: np.linalg.norm(p - np.roll(p, 1, axis=0), axis=1)
    double_area = lambda p: np.linalg.norm(np.cross(p[1] - p[0], p[2] - p[0]))
    return {"max_vertex_error_m": float(np.linalg.norm(actual - expected, axis=1).max()),
            "max_edge_relative_error": float(np.abs(lengths(actual) / lengths(expected) - 1).max()),
            "max_area_relative_error": float(abs(double_area(actual) / double_area(expected) - 1))}


def with_extras(glb, mutate):
    size = struct.unpack_from("<I", glb, 12)[0]
    doc = json.loads(glb[20:20 + size])
    mutate(doc["asset"]["extras"])
    chunk = json.dumps(doc, separators=(",", ":"), allow_nan=False).encode()
    chunk += b" " * (-len(chunk) % 4)
    body = struct.pack("<I4s", len(chunk), b"JSON") + chunk + glb[20 + size:]
    return struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body


@pytest.mark.parametrize("field", ["max_vertex_error_m", "max_area_relative_error", "max_edge_relative_error"])
def test_tolerance_boundary_from_independent_readback(field):
    source = narrow()
    glb, _ = export_glb(source)
    real = read_metrics(source["mesh"]["vertices_m"], world_points(glb, [0, 0, 0]))
    threshold = real[field]
    assert threshold > 0
    for allowed in (threshold, math.nextafter(threshold, math.inf)):
        _, side = export_glb(source, **{field: allowed})
        assert side["precision"] == pytest.approx(real, rel=1e-12)
    with pytest.raises(ValueError, match="precision budget"):
        export_glb(source, **{field: math.nextafter(threshold, 0.)})


def test_vertex_error_without_shape_error():
    source = triangle([[16384.001, 0., 0.], [16384.001, 1., 0.], [16384.001, 0., 1.]])
    glb, side = export_glb(source, max_area_relative_error=0, max_edge_relative_error=0)
    measured = read_metrics(source["mesh"]["vertices_m"], world_points(glb, [0, 0, 0]))
    assert measured["max_area_relative_error"] == measured["max_edge_relative_error"] == 0
    assert measured["max_vertex_error_m"] > .0005
    assert side["precision"] == measured
    with pytest.raises(ValueError, match="precision budget"):
        export_glb(source, max_vertex_error_m=.0005)


@pytest.mark.parametrize("limit", [-.001, True, "0.5", math.nan, math.inf])
def test_invalid_budget(limit):
    with pytest.raises(ValueError, match="invalid precision budget"):
        export_glb(narrow(), max_edge_relative_error=limit)


@pytest.mark.parametrize("origin", [[0,0], [True,0,0], ["1",0,0], [0,math.inf,0]])
def test_invalid_origin(origin):
    with pytest.raises(ValueError, match="invalid local origin"):
        export_glb(narrow(), local_origin_m=origin)


def test_all_axes_world_readback_evidence_and_gate():
    origin = [32768., -523., 71.]
    pp = [[origin[0] + x, origin[1] + y, origin[2] + z] for x,y,z in [[0,0,0],[.001,0,.25],[0,-2,.5]]]
    glb, side = export_glb(triangle(pp), local_origin_m=origin, max_vertex_error_m=1e-8)
    restored = world_points(glb, origin)
    assert np.allclose(restored, pp, rtol=0, atol=1.e-8)
    assert side["mcis_origin_m"] == origin and side["faces"][0]["sources"][0]["locator"] == "F0"
    manifest = bind_asset(glb, side, algorithm_version="public-synthetic")
    checked = verify_asset(glb, side, manifest, expected_algorithm_version="public-synthetic")
    assert checked == {"matches":True, "mismatches":[], "authenticity_checked":False,"lofting_authorized":False}
    assert manifest["research_only"] is True and manifest["lofting_authorized"] is False


@pytest.mark.parametrize("location", ["glb_only","side_only","mismatch"])
def test_origin_disagreement(location):
    glb, side = export_glb(narrow())
    if location != "side_only":
        glb = with_extras(glb, lambda ex: ex.update(mcis_origin_m=[0,0,0]))
    if location != "glb_only":
        side["mcis_origin_m"] = [1,0,0]
    with pytest.raises(ValueError, match="origin"):
        bind_asset(glb, side, algorithm_version="synthetic")


@pytest.mark.parametrize("how", ["null","false","float","pending","bad_review_locator"])
def test_face_evidence_contract(how):
    item = narrow()
    rows = item["provenance"]["faces"]
    if how == "null":
        rows[0] = None
    elif how in ("false","float"):
        rows[0]["face_id"] = False if how == "false" else 0.
    elif how == "pending":
        rows[0]["cell_review"]["review"] = "pending"
    else:
        rows[0]["cell_review"]["locator"] = " "
    with pytest.raises(ValueError, match="evidence"):
        export_glb(item)


@pytest.mark.parametrize("field,value", [("lofting_authorized",True),("lofting_authorized",0),("research_only",1),("research_only",False)])
def test_ill_typed_or_open_glb_gate(field, value):
    glb, side = export_glb(narrow())
    changed = with_extras(glb, lambda ex: ex.update({field:value}))
    with pytest.raises(ValueError, match="authorization"):
        bind_asset(changed, side, algorithm_version="synthetic")


@pytest.mark.parametrize("axes", [(0,1),(1,2),(2,0)])
def test_normal_reversal_all_axes(axes):
    a, b = axes
    pts = []
    for dx,dy in [(0,0),(1.49,.49),(2.49,.51)]:
        p=[0.,0.,0.]
        p[a],p[b]=2**23+dx,2**23+dy
        pts.append(p)
    reference = np.asarray(pts)
    quantized = reference.astype(np.float32).astype(float)
    normal = lambda x: np.cross(x[1]-x[0],x[2]-x[0])
    assert np.dot(normal(reference), normal(quantized)) < 0
    with pytest.raises(ValueError, match="reversed face normal"):
        export_glb(triangle(pts))
