"""Bounded, offline, synthetic tests for MCIS research GLB assets."""
import hashlib
import json
import os
import struct
import sys
from pathlib import Path

import pytest

if "MCIS_SOURCE_TREE" in os.environ:
    repo = Path(os.environ["MCIS_SOURCE_TREE"])
else:
    repo = next(p for p in Path(__file__).resolve().parents if (p / "service/mcis_service").is_dir())
sys.path.insert(0, str(repo.resolve() / "service"))

from mcis_service.agents.skills.ship_reconstruction.asset_integrity import bind_asset, verify_asset
from mcis_service.agents.skills.ship_reconstruction.glb_export import export_glb
from mcis_service.agents.skills.ship_reconstruction.reconstruction_pipeline import reconstruct_sparse


def rectangle_args(origin=0., gap=1.):
    stations, heights = [origin, origin + gap], [0., 1.]
    samples = [[dict(height_m=z, half_breadth_m=1., basis="direct_sample",
                     sources=[dict(document_id="SYNTHETIC-QA", locator=f"横剖-{i}-{j}")])
                for j, z in enumerate(heights)] for i in range(2)]
    reviews = {(0, 0): dict(review="accepted", document_id="SYNTHETIC-QA", locator="单元-0")}
    return stations, heights, samples, reviews


def geometry(vertices, triangles):
    """An exporter-level triangle input; the sparse-grid pipeline is tested separately."""
    entries = [dict(face_id=i, sources=[dict(document_id="SYNTHETIC-QA", locator=f"face-{i}")])
               for i in range(len(triangles))]
    return dict(mesh=dict(vertices_m=vertices, triangles=triangles), provenance=dict(faces=entries),
                research_only=True, lofting_authorized=False)


def asset():
    result = reconstruct_sparse(*rectangle_args())
    glb, evidence = export_glb(result)
    return glb, evidence, bind_asset(glb, evidence, algorithm_version="synthetic-v1")


def read_chunks(glb):
    magic, version, total = struct.unpack_from("<4sII", glb)
    if (magic, version, total) != (b"glTF", 2, len(glb)):
        raise ValueError("invalid container")
    n, kind = struct.unpack_from("<I4s", glb, 12)
    size, bin_type = struct.unpack_from("<I4s", glb, 20 + n)
    if kind != b"JSON" or bin_type != b"BIN\0" or size != len(glb) - 28 - n:
        raise ValueError("invalid chunks")
    return json.loads(glb[20:20+n]), glb[28+n:]


def positions(glb):
    doc, binary = read_chunks(glb)
    primitive = doc["meshes"][0]["primitives"][0]
    accessor = doc["accessors"][primitive["attributes"]["POSITION"]]
    view = doc["bufferViews"][accessor["bufferView"]]
    assert accessor["componentType"] == 5126 and accessor["type"] == "VEC3"
    start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    stride = view.get("byteStride", 12)
    return [struct.unpack_from("<fff", binary, start + i*stride) for i in range(accessor["count"])]


def container(json_chunk, binary=b"\0" * 4, version=2, json_tag=b"JSON", binary_tag=b"BIN\0"):
    """Assemble a small local, two-chunk test fixture."""
    body = struct.pack("<I4s", len(json_chunk), json_tag) + json_chunk
    body += struct.pack("<I4s", len(binary), binary_tag) + binary
    return struct.pack("<4sII", b"glTF", version, 12 + len(body)) + body


def padded_document(doc):
    raw = json.dumps(doc, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return raw + b" " * (-len(raw) % 4)


@pytest.mark.parametrize("gap,stored", [
    (0.0625 - 2**-29, None), (0.0625, None), (0.0625 + 2**-29, .125), (.125, .125),
    (.25,.25)], ids=["below-half-ulp","tie-to-even","above-half-ulp","one-ulp","two-ulp"])
def test_float32_spacing_threshold(gap, stored):
    # ULP of binary32 above 2**20 is 0.125 m.
    result = reconstruct_sparse(*rectangle_args(2.**20,gap))
    assert not result["quality"]["degenerate_faces"]
    if stored is None:
        with pytest.raises(ValueError, match="float32"):
            export_glb(result)
    else:
        decoded = positions(export_glb(result)[0])
        xs = [point[0] for point in decoded]
        assert max(xs) - min(xs) == stored and len(set(decoded)) == 4


def test_distinct_vertices_became_collinear():
    origin = 2.**20
    result = geometry([[0., origin, 0.], [1., origin+.01, 0.], [2., origin, 0.]], [[0,1,2]])
    with pytest.raises(ValueError, match="float32 serialization introduced invalid geometry"):
        export_glb(result)


def test_distinct_unconnected_vertices_merge():
    origin = 2.**20
    vertices = [[origin,0,0], [origin+1,0,0], [origin,1,0],
                [origin+.01,0,0], [origin+2,1,0], [origin+1,2,0]]
    with pytest.raises(ValueError, match="merged distinct vertices"):
        export_glb(geometry(vertices, [[0,1,2],[3,4,5]]))


@pytest.mark.parametrize("value,representable", [(float.fromhex("0x1.fffffep+127"),True),(1.e39,False)])
def test_float32_numeric_limit(value, representable):
    result = geometry([[value,0,0],[value,1,0],[value,0,1]], [[0,1,2]])
    if representable:
        assert all(p[0] == value for p in positions(export_glb(result)[0]))
    else:
        with pytest.raises(ValueError, match="not representable as float32"):
            export_glb(result)


@pytest.mark.parametrize("field", ["document_id","locator"])
@pytest.mark.parametrize("value", [None, 7, True, " \t", "\u3000"])
@pytest.mark.parametrize("source", ["sample","cell","export"])
def test_invalid_references(field,value,source):
    args = rectangle_args()
    if source == "export":
        result = reconstruct_sparse(*args)
        result["provenance"]["faces"][1]["sources"][0][field] = value
        with pytest.raises(ValueError, match="evidence"):
            export_glb(result)
    else:
        ref = args[2][1][1]["sources"][0] if source == "sample" else args[3][(0,0)]
        ref[field] = value
        with pytest.raises(ValueError, match="evidence"):
            reconstruct_sparse(*args)


def test_second_reference_is_checked():
    result = reconstruct_sparse(*rectangle_args())
    result["provenance"]["faces"][0]["sources"].append({"document_id":"SYNTHETIC-QA","locator":" "})
    with pytest.raises(ValueError,match="evidence"):
        export_glb(result)


def test_unicode_valid_source_retained():
    glb, evidence, _ = asset()
    assert all(any(s["locator"]=="横剖-0-0" for s in e["sources"]) for e in evidence["faces"])
    assert b"SYNTHETIC-QA" not in glb
    gltf, _ = read_chunks(glb)
    assert gltf["asset"]["extras"] == {"research_only":True,"lofting_authorized":False}


@pytest.mark.parametrize("field", ["glb_sha256","evidence_sha256"])
@pytest.mark.parametrize("bad", [None,0,False,[], "", "0"*63, "0"*65, "K"*64, "F"*64, "无效", "0"*64+"\n"],
                         ids=["null","number","boolean","array","empty","short","long","nonhex","uppercase","unicode","newline"])
def test_malformed_digests_have_field_level_rejection(field,bad):
    glb, evidence, manifest = asset()
    checked = verify_asset(glb,evidence,{**manifest,field:bad},expected_algorithm_version="synthetic-v1")
    assert checked == dict(matches=False,mismatches=[field],authenticity_checked=False,lofting_authorized=False)


@pytest.mark.parametrize("manifest", [None, [], "text"])
def test_manifest_type(manifest):
    glb, evidence, _ = asset()
    checked = verify_asset(glb,evidence,manifest,expected_algorithm_version="synthetic-v1")
    assert checked["mismatches"] == ["manifest"] and not checked["matches"] and not checked["lofting_authorized"]


def test_external_algorithm_and_hashes():
    glb, evidence, manifest = asset()
    canon = json.dumps(evidence,ensure_ascii=False,sort_keys=True,separators=(",", ":"),allow_nan=False).encode()
    assert manifest["glb_sha256"] == hashlib.sha256(glb).hexdigest()
    assert manifest["evidence_sha256"] == hashlib.sha256(canon).hexdigest()
    assert verify_asset(glb,evidence,manifest,expected_algorithm_version="synthetic-v1")["matches"]
    different = verify_asset(glb,evidence,manifest,expected_algorithm_version="different-expectation")
    assert different["mismatches"] == ["algorithm_version"]


def malformed_container(case):
    encoded = padded_document({"asset":{"version":"2.0"}})
    glb = container(encoded)
    if case == "short":
        return glb[:4]
    if case == "version":
        return container(encoded,version=1)
    if case == "total":
        return glb[:8]+struct.pack("<I",len(glb)+4)+glb[12:]
    if case == "short-json":
        return container(b"{")
    if case == "json-syntax":
        return container(b"oops")
    if case == "json-root":
        return container(b"[]  ")
    if case == "asset-type":
        return container(padded_document({"asset":"2.0"}))
    if case == "asset-ver":
        return container(padded_document({"asset":{"version":"1.0"}}))
    if case == "order":
        return container(encoded,json_tag=b"BIN\0",binary_tag=b"JSON")
    if case == "empty-bin":
        return container(encoded,binary=b"")
    if case == "unaligned-bin":
        return container(encoded,binary=b"\0\0")
    if case == "unknown-chunk":
        return container(encoded,binary_tag=b"NONE")
    if case == "trailing":
        return glb[:8]+struct.pack("<I",len(glb)+4)+glb[12:]+b"    "
    if case == "cut-bin":
        return glb[:-1]
    raise AssertionError(case)


@pytest.mark.parametrize("case", ["short","version","total","short-json","json-syntax","json-root",
             "asset-type","asset-ver","order","empty-bin","unaligned-bin","unknown-chunk","trailing","cut-bin"])
def test_bad_glb_framing_rejected(case):
    _, evidence, _ = asset()
    with pytest.raises(ValueError):
        bind_asset(malformed_container(case),evidence,algorithm_version="synthetic-v1")
