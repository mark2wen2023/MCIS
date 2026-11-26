"""Synthetic DXF files only. No proprietary drawing, handle or dimensions."""

import json
import math
import pytest

from mcis_service.agents.skills.ship_reconstruction.drawing_parser import parse_drawing
from mcis_service.agents.skills.ship_reconstruction.oriented_table import (
    TableFrame,
    extract_oriented_table,
    main,
)

ROWS = ["R0", "R1", "R2"]
COLS = ["Depth A", "Depth B", "Depth C"]
VALUES = [["0", None, "12.60"], [None, None, None], ["-2.5", "+3", "4e-1"]]
U = [0.0, 6.0, 13.0, 22.0]
V = [0.0, 2.3, 7.0, 13.0]
Z = 7.5
ORIGIN = (82031.25, -4172.60, Z)


def draw(layout, angle, parity, origin=ORIGIN, variant=None):
    th = math.radians(angle)
    u = (math.cos(th), math.sin(th))
    v = (-parity * math.sin(th), parity * math.cos(th))

    def point(x, y):
        return (origin[0] + u[0] * x + v[0] * y, origin[1] + u[1] * x + v[1] * y, Z)

    def text(x, y, value):
        e = layout.add_text(
            value,
            dxfattribs={
                "insert": point(x, y),
                "height": 0.6,
                "rotation": angle + 17,
                "text_generation_flag": 2 if parity < 0 else 0,
            },
        )
        return e.dxf.handle

    def line(x, y, k, l):
        return layout.add_line(point(x, y), point(k, l)).dxf.handle

    edges = []
    for j, x in enumerate([-6.0, *U]):
        if x == 13:
            entity = layout.add_lwpolyline(
                [point(x, -4)[:2], point(x, V[-1])[:2]], dxfattribs={"elevation": Z}
            )
            edges.append(entity.dxf.handle)
        else:
            edges.append(line(x, -4, x, V[-1]))
    horizontal = {}
    for y in [-4.0, *V]:
        if y == V[1]:
            horizontal[y] = [
                line(-6, y, 9.8 if variant == "gap" else 10, y),
                line(10, y, U[-1], y),
            ]
        else:
            horizontal[y] = [line(-6, y, U[-1], y)]
    labels = {}
    row_headers = {}
    col_headers = {}
    for j, c in enumerate(COLS):
        col_headers[c] = text(U[j] + 0.83, -1.6 + (j % 2) * 0.7, c)
    for i, r in enumerate(ROWS):
        if variant == "missing_label" and i == 1:
            continue
        row_headers[r] = text(-3.2, V[i] + 0.75, r)
    for i, r in enumerate(ROWS):
        for j, c in enumerate(COLS):
            value = VALUES[i][j]
            if value is not None:
                labels[r, c] = text(U[j] + 1.07, V[i] + 0.82, value)
    if variant == "duplicate":
        text(1.67, 0.95, "9")
    if variant == "boundary":
        text(U[1], 1.01, "8")
    if variant == "invalid_text":
        text(U[1] + 1, V[1] + 0.8, "?")
    # Stray non-table text and non-orthogonal line do not define cells.
    text(-12, 24, "28")
    line(-15, -4, 25, 24)
    return labels, row_headers, col_headers, point, edges, horizontal


def actual(tmp_path, angle=0, parity=1, variant=None, twice=False):
    import ezdxf

    doc = ezdxf.new("R2013")
    model = doc.modelspace()
    record = draw(model, angle, parity, variant=variant)
    if twice:
        draw(model, angle, parity, origin=(ORIGIN[0] + 105, ORIGIN[1] - 79, Z))
    doc.layouts.new("Other").add_text(
        "5.10", dxfattribs={"insert": record[3](1, 1), "height": 0.6}
    )
    doc.saveas(tmp_path / "synthetic.dxf")
    return parse_drawing(tmp_path / "synthetic.dxf"), record


def extract(parsed, rows=ROWS, cols=COLS):
    return extract_oriented_table(
        parsed, row_labels=rows, column_labels=cols, plane_z=Z, tolerance=0.001
    )


@pytest.mark.parametrize("parity", [1, -1])
@pytest.mark.parametrize("angle", [0, 30, 45, 90, 180, 271.37])
def test_disk_rotation_reflection_order_origin_and_inverse(tmp_path, angle, parity):
    parsed, (values, rows, columns, point, vertical, horizontal) = actual(
        tmp_path, angle, parity
    )
    result = extract(parsed)
    assert (
        not result["issues"]
        and len(result["cells"]) == 9
        and result["review"] == "pending"
    )
    assert not result["lofting_authorized"] and result["engineering_unit"] is None
    f = result["frame"]
    assert f["origin_wcs"] == pytest.approx(ORIGIN, abs=1e-8)
    assert f["determinant"] == pytest.approx(parity, abs=1e-9)
    model = TableFrame(f["origin_wcs"], f["column_axis"], f["row_axis"])
    for i, r in enumerate(ROWS):
        for j, c in enumerate(COLS):
            rec = result["cells"][i * 3 + j]
            assert (rec["row"], rec["column"]) == (r, c)
            assert (
                rec["row_header"]["handle"] == rows[r]
                and rec["column_header"]["handle"] == columns[c]
            )
            assert rec["numeric_lexeme"] == VALUES[i][j]
            assert rec["status"] == (
                "blank_unknown" if VALUES[i][j] is None else "numeric_text"
            )
            assert [t["handle"] for t in rec["texts"]] == (
                [values[r, c]] if (r, c) in values else []
            )
            for t in rec["texts"] + [rec["row_header"], rec["column_header"]]:
                assert model.to_wcs(t["local"]) == pytest.approx(t["wcs"], abs=1e-8)
                assert model.to_local(t["wcs"]) == pytest.approx(t["local"], abs=1e-8)
            assert model.to_wcs([U[j], V[i]]) == pytest.approx(
                point(U[j], V[i]), abs=1e-8
            )
            assert rec["local_bounds"] == pytest.approx(
                [U[j], V[i], U[j + 1], V[i + 1]], abs=1e-7
            )
            assert [t["handle"] for t in rec["boundary_segments"]["column_start"]] == [
                vertical[j + 1]
            ]
    assert [
        v["handle"] for v in result["cells"][1]["boundary_segments"]["row_end"]
    ] == horizontal[V[1]]
    assert result["document"]["sha256"] == parsed["document"]["sha256"]


def test_four_endpoint_names_and_counts_recognize_interior_headers(tmp_path):
    parsed, _ = actual(tmp_path, 37, -1)
    four = extract(parsed, ["R0", None, "R2"], ["Depth A", None, "Depth C"])
    assert four["cells"] == extract(parsed)["cells"]


def test_two_tables_are_ambiguous(tmp_path):
    parsed, _ = actual(tmp_path, 22, 1, twice=True)
    value = extract(parsed)
    assert (
        value["cells"] == []
        and value["frame"] is None
        and value["issues"][0]["code"] == "ambiguous_tables"
    )


@pytest.mark.parametrize(
    "kind,code",
    [
        ("gap", "table_not_found_or_incomplete_grid"),
        ("missing_label", "table_not_found_or_incomplete_grid"),
        ("duplicate", "conflict"),
        ("boundary", "text_on_grid_boundary"),
        ("invalid_text", "non_numeric_text"),
    ],
)
def test_disputed_or_incomplete_evidence_stays_unapproved(tmp_path, kind, code):
    parsed, _ = actual(tmp_path, 32, -1, kind)
    r = extract(parsed)
    assert code in {x["code"] for x in r["issues"]} and not r["lofting_authorized"]
    if kind == "duplicate":
        assert (
            r["cells"][0]["numeric_lexeme"] is None and len(r["cells"][0]["texts"]) == 2
        )


@pytest.mark.parametrize("bad", [["a", "a"], ["a"], [None, "r"], ["a", "b", None]])
def test_invalid_semantic_requests(bad):
    with pytest.raises(ValueError):
        extract({"document": {}}, rows=bad)


def test_cli_reads_original_without_modification(tmp_path):
    parsed, _ = actual(tmp_path, -17.25, -1)
    profile = tmp_path / "profile.json"
    profile.write_text(
        json.dumps(
            {
                "row_labels": ROWS,
                "column_labels": COLS,
                "tolerance": 0.001,
                "plane_z": Z,
            }
        )
    )
    dest = tmp_path / "candidate.json"
    src = tmp_path / "synthetic.dxf"
    before = src.read_bytes()
    assert (
        main([str(src), str(profile), "--output", str(dest)]) == 0
        and src.read_bytes() == before
    )
    assert json.loads(dest.read_text())["document"]["id"] == parsed["document"]["id"]


@pytest.fixture
def offset_case(tmp_path):
    parsed, _ = actual(tmp_path, 135, -1)
    # Test-only non-negative breadths in the synthetic drawing record.
    for entity in parsed["entities"]:
        if entity.get("text") == "-2.5":
            entity["text"] = "2.5"
        if entity.get("text") == "4e-1":
            entity["text"] = ".4"
    located = extract(parsed)
    mapping = dict(
        station_axis="row",
        stations_m_by_label={"R0": 0.0, "R1": 1.0, "R2": 2.0},
        heights_m_by_label={"Depth A": 0.0, "Depth B": 0.5, "Depth C": 1.0},
        unit="mm",
        mapping_source={
            "document_id": "synthetic-profile",
            "locator": "mock dimensions",
        },
    )
    return located, mapping


def test_offsets_reuse_review_boundary_and_source_evidence(offset_case):
    from mcis_service.agents.skills.ship_reconstruction.oriented_offsets import (
        offsets_for_review,
    )
    from mcis_service.agents.skills.ship_reconstruction.offset_bridge import (
        prepare_offset_samples,
    )

    located, mapping = offset_case
    out = offsets_for_review(located, **mapping)
    assert len(out["rows"]) == 9 and out["diagnostics"]["unique_points"] == 5
    keys = dict(
        stations_m=out["stations_m"],
        heights_m=out["heights_m"],
        frame_id="synthetic-ship-frame",
    )
    with pytest.raises(ValueError, match="matching accepted research review"):
        prepare_offset_samples(out, reviews={}, **keys)
    reviews = {}
    for ob in out["rows"]:
        if ob["half_breadth_m"] is not None:
            reviews[ob["station_x_m"], ob["height_z_m"]] = {
                "source": ob["source"],
                "review": "accepted",
                "frame_id": keys["frame_id"],
                "value_m": ob["half_breadth_m"],
                "review_source": {
                    "document_id": "synthetic-test",
                    "locator": "fixture-only approval",
                },
            }
    bridge = prepare_offset_samples(out, reviews=reviews, **keys)
    assert bridge["observations"] == out["rows"] and not bridge["lofting_authorized"]
    assert (
        sum(t["source"]["table_cell"]["texts"] == [] for t in bridge["observations"])
        == 4
    )
    with pytest.raises(ValueError, match="exactly"):
        offsets_for_review(
            located, **{**mapping, "heights_m_by_label": {"Depth A": 0.0}}
        )
    with pytest.raises(ValueError):
        offsets_for_review(located, **{**mapping, "unit": "unverified"})
    assert out["rows"][0]["source"]["table_cell"]["texts"][0]["raw_text"] == "0"


def test_boundary_preserves_affected_cell_evidence(tmp_path):
    parsed, _ = actual(tmp_path, 90, -1, "boundary")
    r = extract(parsed)
    hits = [c for c in r["cells"] if c["status"] == "boundary_ambiguous"]
    assert len(hits) == 2 and all(c["numeric_lexeme"] is None for c in hits)
    assert {t["raw_text"] for c in hits for t in c["boundary_texts"]} == {"8"}


def test_unsupported_block_does_not_become_an_observed_zero(tmp_path):
    parsed, _ = actual(tmp_path)
    parsed["entities"].append(
        {"layout": "Model", "type": "INSERT", "handle": "TEST_BLOCK"}
    )
    r = extract(parsed)
    assert "TEST_BLOCK" in r["unexpanded_insert_handles"]
    assert r["cells"][4]["status"] == "blank_unknown" and not r["lofting_authorized"]


@pytest.mark.parametrize(
    "document",
    [
        None,
        [],
        {},
        {"sha256": None},
        {"sha256": True},
        {"sha256": 1},
        {"sha256": ["a" * 64]},
        {"sha256": ""},
        {"sha256": "a" * 63},
        {"sha256": "a" * 65},
        {"sha256": "0" * 63 + "g"},
        {"sha256": "a" * 63 + " "},
        {"sha256": "a" * 64 + "\n"},
        {"sha256": "０" * 64},
    ],
)
def test_rejects_invalid_serialized_drawing_fingerprint(offset_case, document):
    from mcis_service.agents.skills.ship_reconstruction.oriented_offsets import (
        offsets_for_review,
    )

    table, mapping = offset_case
    restored = json.loads(json.dumps({**table, "document": document}))
    with pytest.raises(ValueError, match="64 hexadecimal SHA-256"):
        offsets_for_review(restored, **mapping)


@pytest.mark.parametrize("doc_id", ["0123456789abcdef" * 4, "0123456789ABCDEF" * 4])
def test_accepts_ascii_sha256_and_preserves_evidence_fingerprint(offset_case, doc_id):
    from mcis_service.agents.skills.ship_reconstruction.oriented_offsets import (
        offsets_for_review,
    )

    table, mapping = offset_case
    table["document"] = {"sha256": doc_id}
    result = offsets_for_review(table, **mapping)
    assert all(row["source"]["document_id"] == doc_id for row in result["rows"])
