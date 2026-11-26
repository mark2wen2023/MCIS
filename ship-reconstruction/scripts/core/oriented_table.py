"""Locate a ruled text table in a parsed CAD drawing using ordered header labels.

All distances and tolerances are in the drawing's coordinate units. Row and
column order define the signs of the two axes, including reflected tables.
Only direct, coplanar text anchors and straight grid segments are evidence.
"""

from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass
import math
import re

_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")


def _finite(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _point(value):
    return (
        isinstance(value, (list, tuple))
        and len(value) == 3
        and all(_finite(x) for x in value)
    )


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


@dataclass(frozen=True)
class TableFrame:
    """An orthonormal frame with the origin at the first data cell's lower index corner."""

    origin: tuple
    column_axis: tuple
    row_axis: tuple

    def to_local(self, p):
        d = (p[0] - self.origin[0], p[1] - self.origin[1])
        return (_dot(d, self.column_axis), _dot(d, self.row_axis))

    def to_wcs(self, p):
        u, v = p
        return (
            self.origin[0] + u * self.column_axis[0] + v * self.row_axis[0],
            self.origin[1] + u * self.column_axis[1] + v * self.row_axis[1],
            self.origin[2],
        )

    def as_dict(self):
        u, v = self.column_axis, self.row_axis
        return {
            "origin_wcs": list(self.origin),
            "column_axis": list(u),
            "row_axis": list(v),
            "determinant": u[0] * v[1] - u[1] * v[0],
            "column_angle_deg": math.degrees(math.atan2(u[1], u[0])) % 360,
        }


def _sources(parsed, layout, z, tol):
    texts = []
    segments = []
    skipped = []
    for e in parsed["entities"]:
        if e.get("layout") != layout:
            continue
        h = e.get("handle")
        kind = e.get("type")
        if kind in ("TEXT", "MTEXT"):
            p = e.get("anchor_wcs")
            if not h or not _point(p) or not isinstance(e.get("text"), str):
                skipped.append({"code": "unlocated_text", "handle": h})
                continue
            if abs(p[2] - z) <= tol:
                texts.append((e["text"].strip(), h, tuple(p), e["text"]))
        if kind not in ("LINE", "LWPOLYLINE"):
            continue
        for seg in e.get("segments_wcs", []):
            a = seg.get("start")
            b = seg.get("end")
            if not h or not _point(a) or not _point(b):
                skipped.append({"code": "unlocated_grid_segment", "handle": h})
                continue
            if (
                max(abs(a[2] - z), abs(b[2] - z)) <= tol
                and math.dist(a[:2], b[:2]) > tol
            ):
                segments.append((tuple(a), tuple(b), h, seg.get("index", 0)))
    return texts, segments, skipped


class _Line:
    def __init__(self, position, spans, tol):
        self.position = position
        self.spans = sorted(spans)
        self.tol = tol

    def covers(self, lo, hi):
        """Cover the full requested interval, retaining each supporting source segment."""
        current = lo
        hits = []
        for a, b, h, index in self.spans:
            if b < lo - self.tol or a > hi + self.tol:
                continue
            if a > current + self.tol:
                break
            if b >= lo and a <= hi and (b - a) > self.tol:
                if min(b, hi) - max(a, lo) > self.tol:
                    hits.append({"handle": h, "segment_index": index})
                current = max(current, b)
        return hits if current >= hi - self.tol and hits else None


def _lines(projected, along, tol):
    normal = 1 - along
    parts = []
    for a, b, h, index in projected:
        if abs(a[normal] - b[normal]) <= tol and abs(a[along] - b[along]) > tol:
            parts.append(
                (
                    (a[normal] + b[normal]) / 2,
                    min(a[along], b[along]),
                    max(a[along], b[along]),
                    h,
                    index,
                )
            )
    groups = []
    for c, *span in sorted(parts):
        if not groups or c - groups[-1][0][0] > tol:
            groups.append([])
        groups[-1].append((c, span))
    return [
        _Line(sum(x[0] for x in group) / len(group), [x[1] for x in group], tol)
        for group in groups
    ]


def _interior(edges, value, tol):
    i = bisect_right(edges, value) - 1
    if (
        i < 0
        or i + 1 >= len(edges)
        or min(value - edges[i], edges[i + 1] - value) <= tol
    ):
        return None
    return i


def _frames(first, last, segments, plane_z, tol):
    dx = last[2][0] - first[2][0]
    dy = last[2][1] - first[2][1]
    d = math.hypot(dx, dy)
    if d <= tol:
        return
    proposals = {}
    for a, b, _, _ in segments:
        ex = b[0] - a[0]
        ey = b[1] - a[1]
        ln = math.hypot(ex, ey)
        u = (ex / ln, ey / ln)
        advance = dx * u[0] + dy * u[1]
        if advance < 0:
            u = (-u[0], -u[1])
            advance = -advance
        if advance <= tol:
            continue
        # The header texts need not sit at identical in-cell offsets. Only
        # grid edges, never their possibly skewed anchor-to-anchor line, set axes.
        key = (round(u[0], 9), round(u[1], 9))
        if key not in proposals or ln > proposals[key][0]:
            proposals[key] = (ln, u)
    for _, u in sorted(proposals.values(), reverse=True):
        for sign in (1, -1):
            yield TableFrame(
                (first[2][0], first[2][1], plane_z), u, (-sign * u[1], sign * u[0])
            )


def _find(frame, first, last, texts, segments, rows, cols, tol):
    pts = [(*frame.to_local(t[2]), t) for t in texts]
    a = frame.to_local(first[2])
    b = frame.to_local(last[2])
    segs = [(frame.to_local(p), frame.to_local(q), h, i) for p, q, h, i in segments]
    horizontal = [g for g in _lines(segs, 0, tol) if g.covers(a[0], b[0])]
    hh = [g.position for g in horizontal]
    top = _interior(hh, a[1], tol)
    if top is None or top != _interior(hh, b[1], tol) or top + 1 + len(rows) >= len(hh):
        return
    hl = horizontal[top : top + len(rows) + 2]
    vv = [g.position for g in hl]
    vertical = [g for g in _lines(segs, 1, tol) if g.covers(vv[0], vv[-1])]
    uu = [g.position for g in vertical]
    left = _interior(uu, a[0], tol)
    if left is None or left < 1 or _interior(uu, b[0], tol) != left + len(cols) - 1:
        return
    right = left + len(cols)
    header = defaultdict(list)
    label = defaultdict(list)
    for x, y, t in pts:
        j = _interior(uu, x, tol)
        i = _interior(vv, y, tol)
        if j is None or i is None:
            continue
        if i == 0 and left <= j < right:
            header[j - left].append(t)
        if i > 0 and j < left:
            label[i - 1, j].append(t)

    def observed(groups, requested):
        if any(len(group) != 1 for group in groups):
            return None
        actual = [group[0][0] for group in groups]
        if any(not value for value in actual) or len(set(actual)) != len(actual):
            return None
        if any(
            want is not None and value != want for value, want in zip(actual, requested)
        ):
            return None
        return actual

    actual_cols = observed([header[j] for j in range(len(cols))], cols)
    if actual_cols is None:
        return
    for label_col in range(left):
        actual_rows = observed([label[i, label_col] for i in range(len(rows))], rows)
        if actual_rows is None:
            continue
        if any(not g.covers(uu[label_col], uu[right]) for g in hl[1:]):
            continue
        local = TableFrame(
            frame.to_wcs((uu[left], vv[1])), frame.column_axis, frame.row_axis
        )
        us = [x - uu[left] for x in uu[left : right + 1]]
        vs = [y - vv[1] for y in vv[1:]]
        box_hits = defaultdict(list)
        boundary = []
        disputed = defaultdict(list)
        for x, y, t in pts:
            if (
                not uu[left] - tol <= x <= uu[right] + tol
                or not vv[1] - tol <= y <= vv[-1] + tol
            ):
                continue
            j = _interior(us, x - uu[left], tol)
            i = _interior(vs, y - vv[1], tol)
            if i is None or j is None:
                boundary.append(t[1])
                for row_index in range(len(vs) - 1):
                    if not vs[row_index] - tol <= y - vv[1] <= vs[row_index + 1] + tol:
                        continue
                    for col_index in range(len(us) - 1):
                        if (
                            us[col_index] - tol
                            <= x - uu[left]
                            <= us[col_index + 1] + tol
                        ):
                            disputed[row_index, col_index].append(t)
            else:
                box_hits[i, j].append(t)
        cells = []
        issues = []
        if boundary:
            issues.append(
                {"code": "text_on_grid_boundary", "handles": sorted(boundary)}
            )
        for i, r in enumerate(actual_rows):
            for j, c in enumerate(actual_cols):
                bounds = [us[j], vs[i], us[j + 1], vs[i + 1]]
                values = box_hits[i, j]
                status = (
                    "blank_unknown"
                    if not values
                    else "conflict"
                    if len(values) > 1
                    else "numeric_text"
                    if _NUMBER.fullmatch(values[0][0])
                    else "non_numeric_text"
                )
                if disputed[i, j]:
                    status = "boundary_ambiguous"
                if status in ("conflict", "non_numeric_text"):
                    issues.append({"code": status, "row": r, "column": c})
                edge = {
                    "row_start": hl[i + 1].covers(uu[left + j], uu[left + j + 1]),
                    "row_end": hl[i + 2].covers(uu[left + j], uu[left + j + 1]),
                    "column_start": vertical[left + j].covers(vv[i + 1], vv[i + 2]),
                    "column_end": vertical[left + j + 1].covers(vv[i + 1], vv[i + 2]),
                }
                if not all(edge.values()):
                    return

                def anchor(t):
                    return {
                        "handle": t[1],
                        "raw_text": t[3],
                        "wcs": list(t[2]),
                        "local": list(local.to_local(t[2])),
                    }

                cells.append(
                    {
                        "row": r,
                        "column": c,
                        "status": status,
                        "numeric_lexeme": values[0][0]
                        if status == "numeric_text"
                        else None,
                        "texts": [anchor(t) for t in values],
                        "boundary_texts": [anchor(t) for t in disputed[i, j]],
                        "row_header": anchor(label[i, label_col][0]),
                        "column_header": anchor(header[j][0]),
                        "local_bounds": bounds,
                        "boundary_segments": edge,
                    }
                )
        yield {"frame": local.as_dict(), "cells": cells, "issues": issues}


def extract_oriented_table(
    parsed, *, row_labels, column_labels, layout="Model", plane_z=0.0, tolerance
):
    """Find one rectangular table by its ordered, contiguous row/column headers.

    At least two distinct labels per axis are required. Row labels are in a
    column preceding the data; column labels are in the adjacent header row.
    Interior labels may be None to transcribe unique intervening headers from
    the source. The axis length and the two endpoint labels remain required.
    The caller supplies no target handles, cell values, crop, origin or angle.
    All returns are candidates pending review; a blank never supplies a zero.
    """
    if not (
        _finite(tolerance)
        and tolerance > 0
        and _finite(plane_z)
        and isinstance(layout, str)
        and layout
    ):
        raise ValueError("invalid layout, plane or tolerance")

    def labels(values):
        if not isinstance(values, (list, tuple)) or not all(
            x is None or (isinstance(x, str) and x.strip()) for x in values
        ):
            raise ValueError("ordered text labels required")
        seq = [v.strip() if v is not None else None for v in values]
        explicit = [v for v in seq if v is not None]
        if (
            len(seq) < 2
            or seq[0] is None
            or seq[-1] is None
            or len(explicit) != len(set(explicit))
        ):
            raise ValueError(
                "distinct endpoint labels and unique explicit labels required"
            )
        return seq

    rows, cols = labels(row_labels), labels(column_labels)
    result = {
        "document": dict(parsed["document"]),
        "layout": layout,
        "drawing_insertion_units": parsed.get("units"),
        "engineering_unit": None,
        "plane_z": plane_z,
        "tolerance": tolerance,
        "frame": None,
        "cells": [],
        "issues": [],
        "source_issues": list(parsed.get("issues", [])),
        "source_scope": "direct planar TEXT/MTEXT and straight LINE/LWPOLYLINE segments",
        "unexpanded_insert_handles": [
            e.get("handle")
            for e in parsed.get("entities", [])
            if e.get("layout") == layout and e.get("type") == "INSERT"
        ],
        "review": "pending",
        "lofting_authorized": False,
    }
    if parsed["document"].get("status") not in ("parsed", "partial"):
        result["issues"] = [{"code": "drawing_not_parsed"}]
        return result
    texts, segments, skipped = _sources(parsed, layout, plane_z, tolerance)
    found = {}
    by_text = defaultdict(list)
    for t in texts:
        by_text[t[0]].append(t)
    for first in by_text[cols[0]]:
        for last in by_text[cols[-1]]:
            for frame in _frames(first, last, segments, plane_z, tolerance):
                for matched in _find(
                    frame, first, last, texts, segments, rows, cols, tolerance
                ):
                    cells = matched["cells"]
                    key = tuple(
                        (
                            c["row_header"]["handle"],
                            c["column_header"]["handle"],
                            tuple(
                                (t["handle"], t["segment_index"])
                                for v in c["boundary_segments"].values()
                                for t in v
                            ),
                        )
                        for c in cells
                    )
                    found.setdefault(key, matched)
                    if len(found) > 1:
                        result["issues"] = [{"code": "ambiguous_tables"}]
                        return result
    if found:
        result.update(next(iter(found.values())))
    else:
        result["issues"] = [{"code": "table_not_found_or_incomplete_grid"}]
    result["issues"].extend(skipped)
    return result


def main(argv=None):
    """Read DXF and a JSON header profile without writing the CAD document."""
    import argparse
    import json
    from pathlib import Path
    from .drawing_parser import parse_drawing

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("drawing", type=Path)
    ap.add_argument(
        "profile", type=Path, help="JSON options for extract_oriented_table"
    )
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args(argv)
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    result = extract_oriented_table(parse_drawing(args.drawing), **profile)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    return 0 if result["cells"] and not result["issues"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
