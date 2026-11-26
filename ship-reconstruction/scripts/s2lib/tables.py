"""从直线支撑、文字及原生 CAD 表恢复拓扑，不接受个船模板。"""

from collections import defaultdict
from bisect import bisect_right
import math
import re

import numpy as np

from .cad import norm

NUM = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
WL = rf"(?:wl|水线)[:=]?({NUM})(mm|cm|m|毫米|厘米|米)?|({NUM})(mm|cm|m|毫米|厘米|米)?(?:wl|水线)"
STA = rf"(?:sta(?:tion)?|st|站位|站号|站|fr(?:ame)?)[:=#]?({NUM})(mm|m|米|毫米)?"
GROUP = r"半宽值?|高度值?|half.?breadths?|heights?"
UNIT = r"(mm|cm|毫米|厘米|m|米)"


def station(s):
    s = norm(s)
    return bool(
        re.fullmatch(STA, s)
        or re.fullmatch(NUM, s)
        or re.fullmatch(r"(?:ap|fp|艏垂线|艉垂线|首垂线|尾垂线)(?:[+-]\d+(?:\.\d+)?)?", s)
        or re.fullmatch(r"(?:\d+\+?)?\d+[/⁄]\d+", s)
        or re.fullmatch(r"(?:st|sta|station|站)(?:\d+\+?)?\d+[/⁄]\d+", s)
    )


def field(s):
    n = norm(s)
    return bool(
        re.fullmatch(WL, n)
        or n in ("bl", "baseline", "基线", "船底", "keel", "甲板", "deck")
        or re.search(r"甲板边|deckedge|折角|chine|\d剖|buttock", n)
    )


def units(texts):
    hits = []
    for t in texts:
        if re.search(
            r"型值|半宽|纵距|坐标|尺寸|单位|offset|ordinate|breadth|units?|dimensions?", t["n"]
        ):
            m = re.search(
                r"(?:units?|单位|尺寸|半宽|型值|offsets?|breadths?|ordinates?|dimensions?)(?:units?|数值|单位|均为|为|in|arein|以|采用|[:=：()（）\[\]])*"
                + UNIT
                + r"(?![a-z])",
                t["n"],
            )
            if m:
                hits.append(
                    ({"毫米": "mm", "厘米": "cm", "米": "m"}.get(m[1], m[1]), t["instance"])
                )
    return hits


def metre(v, unit):
    return (
        v * ({"mm": 0.001, "毫米": 0.001, "cm": 0.01, "厘米": 0.01, "m": 1.0, "米": 1.0}[unit])
        if v is not None and unit
        else None
    )


def axis_value(label, axis, unit, spacing):
    s = norm(label)
    if axis == "field":
        if s in ("bl", "baseline", "基线"):
            return 0.0
        m = re.fullmatch(WL, s)
        if m:
            return metre(float(m[1] or m[3]), m[2] or m[4] or unit)
    else:
        m = re.fullmatch(STA, s)
        if m and m[2]:
            return metre(float(m[1]), m[2])
        n = m[1] if m else s
        if spacing is not None and re.fullmatch(NUM, n):
            return float(n) * spacing
    return None


def first(grid, r, c):
    items = grid.get((r, c), [])
    return items[0]["text"].strip() if len(items) == 1 else ""


def interpret(grid, nr, nc, *, merged=None, parents=None):
    options = []
    for transpose in (False, True):
        g = {(c, r): items for (r, c), items in grid.items()} if transpose else grid
        rows, cols = (nc, nr) if transpose else (nr, nc)
        for header in range(rows):
            fs = [c for c in range(cols) if field(first(g, header, c))]
            if len(fs) < 2:
                continue
            for sc in range(cols):
                if min(fs) <= sc <= max(fs):
                    continue
                for direction in (-1, 1):
                    rs = []
                    for r in range(header + direction, rows if direction == 1 else -1, direction):
                        if not station(first(g, r, sc)):
                            break
                        rs.append(r)
                    if len(rs) < 2:
                        continue
                    options.append((len(rs) * len(fs), transpose, header, sc, fs, rs))
    if not options:
        return []
    best = max(o[0] for o in options)
    opts = [o for o in options if o[0] == best]
    if len(opts) != 1:
        return []
    _, tr, head, sc, fields, rows = opts[0]

    def rc(r, c):
        return (c, r) if tr else (r, c)

    out = []
    for r in rows:
        sr = grid[rc(r, sc)][0]
        for c in fields:
            orig = rc(r, c)
            hdr = grid[rc(head, c)][0]
            vs = grid.get(orig, [])
            raw = [t["text"] for t in vs]
            nums = [float(norm(t)) for t in raw if re.fullmatch(NUM, norm(t))]
            value = None
            if merged and orig in merged:
                status = "merged_unknown"
            elif not raw:
                status = "blank_unknown"
            elif len(nums) != len(raw):
                status = "non_numeric"
            elif len(set(nums)) > 1:
                status = "conflict"
            else:
                value = nums[0]
                status = "duplicate" if len(raw) > 1 else "zero" if value == 0 else "numeric"
            parent = parents(rc(head, c), tr, 1 if rows[0] > head else -1) if parents else None
            out.append(
                dict(
                    station_label=sr["text"].strip(),
                    field_label=hdr["text"].strip(),
                    group=parent["text"].strip() if parent else None,
                    raw_texts=raw,
                    handles=[v["handle"] for v in vs],
                    instances=[v["instance"] for v in vs],
                    source_wcs=[v["p"] for v in vs],
                    status=status,
                    value=value,
                    row_header=sr,
                    field_header=hdr,
                    group_header=parent,
                    grid_index=list(orig),
                )
            )
    return out


def coalesce(vals, tol):
    result = []
    for v in sorted(vals):
        if not result or v - result[-1] > tol:
            result.append(v)
    return result


def grids(data, layout):
    texts = [x for x in data["texts"] if x["layout"] == layout]
    if sum(field(t["text"]) for t in texts) < 2:
        return
    segments = [
        s for s in data["segments"] if s["layout"] == layout and abs(s["a"][2] - s["b"][2]) < 1e-6
    ]
    by = defaultdict(list)
    for s in segments:
        a, b = np.array(s["a"][:2]), np.array(s["b"][:2])
        d = b - a
        if np.linalg.norm(d) > 1e-8:
            by[round(math.atan2(d[1], d[0]) % math.pi, 6) % round(math.pi, 6)].append((a, b, s))
    seen = set()
    for ang, array in by.items():
        if len(array) < 3:
            continue
        perp = next((k for k in by if abs(math.cos(ang - k)) < 2e-6), None)
        if perp is None:
            continue
        axis = array[0][1] - array[0][0]
        axis /= np.linalg.norm(axis)
        if axis[0] < 0:
            axis = -axis
        mat = np.array([axis, [-axis[1], axis[0]]])
        # Use coordinates relative to a real source vertex to handle large drawing offsets.
        origin = array[0][0]
        tol = max(1e-6, 1e-9 * np.median([np.linalg.norm(b - a) for a, b, _ in array]))

        def runs(items, dim):
            groups = defaultdict(list)
            for a, b, s in items:
                p = mat @ (a - origin)
                q = mat @ (b - origin)
                fixed = (p[1 - dim] + q[1 - dim]) / 2
                key = round(fixed / tol)
                groups[key].append((min(p[dim], q[dim]), max(p[dim], q[dim]), s["instance"], fixed))
            out = []
            for group in groups.values():
                left = None
                for lo, hi, h, fixed in sorted(group):
                    if left is None or lo > right + tol:
                        if left is not None:
                            out.append((v, left, right, ids))
                        v, left, right, ids = fixed, lo, hi, [h]
                    else:
                        right = max(right, hi)
                        ids.append(h)
                if left is not None:
                    out.append((v, left, right, ids))
            return out

        horizontal = runs(array, 0)
        vertical = runs(by[perp], 1)
        blocks = defaultdict(list)
        for y, l, r, ids in horizontal:
            blocks[round(l / tol), round(r / tol)].append(y)
        for (kl, kr), levels in blocks.items():
            if len(levels) < 3:
                continue
            l, r = kl * tol, kr * tol
            # Split identical-width grids separated by substantial empty paper.
            yy = coalesce(levels, tol)
            diffs = np.diff(yy)
            chunks = np.split(yy, np.where(diffs > 4 * np.median(diffs))[0] + 1)
            for chunk in chunks:
                if len(chunk) < 3:
                    continue
                b, t = chunk[0], chunk[-1]
                vr = [
                    e
                    for e in vertical
                    if l - tol <= e[0] <= r + tol and min(t, e[2]) - max(b, e[1]) > tol
                ]
                xs = coalesce([v[0] for v in vr], tol)
                hr = [
                    e
                    for e in horizontal
                    if b - tol <= e[0] <= t + tol and min(r, e[2]) - max(l, e[1]) > tol
                ]
                ys = coalesce([h[0] for h in hr], tol)
                if len(xs) < 3 or len(ys) < 3 or (len(xs) - 1) * (len(ys) - 1) > 100000:
                    continue
                z = next((s["a"][2] for _, _, s in array if s["instance"] == hr[0][3][0]), 0)
                grid = defaultdict(list)
                boundaries = defaultdict(list)
                for txt in texts:
                    p = mat @ (np.array(txt["p"][:2]) - origin)
                    i, j = bisect_right(ys, p[1]) - 1, bisect_right(xs, p[0]) - 1
                    if abs(txt["p"][2] - z) < tol and 0 <= i < len(ys) - 1 and 0 <= j < len(xs) - 1:
                        rr = [
                            k
                            for k in (i - 1, i, i + 1)
                            if 0 <= k < len(ys) - 1 and ys[k] - tol <= p[1] <= ys[k + 1] + tol
                        ]
                        cc = [
                            k
                            for k in (j - 1, j, j + 1)
                            if 0 <= k < len(xs) - 1 and xs[k] - tol <= p[0] <= xs[k + 1] + tol
                        ]
                        if len(rr) * len(cc) > 1:
                            for ri in rr:
                                for cj in cc:
                                    boundaries[ri, cj].append(txt)
                        else:
                            grid[i, j].append(txt)
                if sum(any(field(t["text"]) for t in v) for v in grid.values()) < 2:
                    continue

                def bounds(axis_lines, pos, lo, hi):
                    return [
                        h
                        for f, a, e, ids in axis_lines
                        if abs(f - pos) <= tol and a <= lo + tol and e >= hi - tol
                        for h in ids
                    ]

                def parent(pos, tr, sign):
                    i, j = pos
                    if tr:
                        j -= sign
                    else:
                        i -= sign
                    if not (0 <= i < len(ys) - 1 and 0 <= j < len(xs) - 1):
                        return None
                    if tr:
                        borders = [k for k, y in enumerate(ys) if bounds(hr, y, xs[j], xs[j + 1])]
                        coord = i
                    else:
                        borders = [k for k, x in enumerate(xs) if bounds(vr, x, ys[i], ys[i + 1])]
                        coord = j
                    low = max((k for k in borders if k <= coord), default=coord)
                    high = min((k for k in borders if k > coord), default=coord + 1)
                    candidates = [
                        v
                        for k in range(low, high)
                        for v in grid.get((k, j) if tr else (i, k), [])
                        if re.search(GROUP, v["n"])
                    ]
                    return candidates[0] if len(candidates) == 1 else None

                cells = interpret(grid, len(ys) - 1, len(xs) - 1, parents=parent)
                if not cells:
                    continue
                key = frozenset(
                    (c["row_header"]["instance"], c["field_header"]["instance"]) for c in cells
                )
                if key in seen:
                    continue
                seen.add(key)
                for c in cells:
                    i, j = c["grid_index"]
                    c["edge_instances"] = [
                        bounds(hr, y, xs[j], xs[j + 1]) for y in ys[i : i + 2]
                    ] + [bounds(vr, x, ys[i], ys[i + 1]) for x in xs[j : j + 2]]
                    if not all(c["edge_instances"]):
                        c.update(status="merged_unknown", value=None)
                    if boundaries[i, j]:
                        c.update(
                            status="boundary_ambiguous", value=None, boundary_texts=boundaries[i, j]
                        )
                    c["cell_wcs"] = [
                        [*((mat.T @ [x, y]) + origin), z]
                        for x, y in [(xs[j], ys[i]), (xs[j + 1], ys[i + 1])]
                    ]
                yield dict(
                    layout=layout,
                    representation="ruled",
                    cells=cells,
                    origin_wcs=origin.tolist(),
                    paper_basis=mat.tolist(),
                )


def extract(data, inventory, spacing):
    tables = []
    for layout in sorted({t["layout"] for t in data["texts"]}):
        zs = {
            round(t["p"][2], 6) for t in data["texts"] if t["layout"] == layout and field(t["text"])
        }
        ruled = []
        for z in sorted(zs):
            planar = {
                "texts": [
                    t for t in data["texts"] if t["layout"] == layout and abs(t["p"][2] - z) < 1e-6
                ],
                "segments": [
                    s
                    for s in data["segments"]
                    if s["layout"] == layout and max(abs(s["a"][2] - z), abs(s["b"][2] - z)) < 1e-6
                ],
            }
            ruled.extend(grids(planar, layout))
        tables.extend(ruled)
        used = {
            h
            for t in ruled
            for c in t["cells"]
            for h in [*c["instances"], c["row_header"]["instance"], c["field_header"]["instance"]]
        }
        # Require printed table context before interpreting borderless gaps.
        if any(r["kind"] == "offset_table" and r["layout"] == layout for r in inventory["regions"]):
            tables.extend(text_tables(data, layout, used))
    for table in data["native"]:
        g = defaultdict(list)
        for i, row in enumerate(table["rows"]):
            for j, label in enumerate(row):
                if label.strip():
                    g[i, j].append(
                        dict(
                            handle=table["handle"],
                            instance=f"{table['instance']}:{i},{j}",
                            text=label,
                            n=norm(label),
                            p=None,
                            table_insertion_wcs=table["insertion_wcs"],
                            native_cell=[i, j],
                        )
                    )
        cells = interpret(
            g,
            len(table["rows"]),
            max(map(len, table["rows"]), default=0),
            merged={tuple(v) for v in table["merged"]},
        )
        if cells:
            tables.append(
                dict(
                    layout=table["layout"],
                    representation="ACAD_TABLE",
                    native_handle=table["handle"],
                    cells=cells,
                )
            )
    for table in tables:
        hits = units([t for t in data["texts"] if t["layout"] == table["layout"]])
        unique = {h[0] for h in hits}
        unit = next(iter(unique)) if len(unique) == 1 else None
        table.update(
            unit=unit,
            unit_evidence=hits,
            unit_status="printed" if unit else "conflict" if hits else "unknown",
        )
        for c in table["cells"]:
            c.update(
                unit=unit,
                value_m=metre(c["value"], unit),
                level_m=axis_value(c["field_label"], "field", unit, None),
                station_m=axis_value(c["station_label"], "station", None, spacing),
            )
    return tables


def text_tables(data, layout, used):
    """表格无边线时，以双轴题头、平行文字带及单调行标恢复可观察的单元。"""
    texts = [t for t in data["texts"] if t["layout"] == layout and t["instance"] not in used]
    headers = [t for t in texts if field(t["text"])]
    seen = set()
    for head in headers:
        base = np.asarray(head["baseline"][:2])
        base /= np.linalg.norm(base)
        for u in (base, np.array([-base[1], base[0]])):
            v = np.array([-u[1], u[0]])
            o = np.asarray(head["p"][:2])
            h = max(head["height"], 1e-6)
            positions = [
                (
                    float((np.asarray(t["p"][:2]) - o) @ u),
                    float((np.asarray(t["p"][:2]) - o) @ v),
                    t,
                )
                for t in texts
            ]
            fieldrow = sorted(
                [(x, t) for x, y, t in positions if abs(y) < 0.7 * h and field(t["text"])],
                key=lambda q: q[0],
            )
            if len(fieldrow) < 2:
                continue
            steps = np.diff([x for x, _ in fieldrow])
            if min(steps) < 1.5 * h or max(steps) > 4 * np.median(steps):
                continue
            corner = [
                (x, t)
                for x, y, t in positions
                if abs(y) < 0.9 * h and re.search(r"station|站号|站位|^st[./]?$|^站$", t["n"])
            ]
            if not corner:
                # Explicit station prefixes furnish the second independent axis.
                corner = [(x, t) for x, y, t in positions if re.fullmatch(STA, t["n"])]
            for x0, _ in corner:
                if fieldrow[0][0] - h <= x0 <= fieldrow[-1][0] + h:
                    continue
                rows = sorted(
                    [
                        (y, t)
                        for x, y, t in positions
                        if abs(x - x0) < 0.95 * h and abs(y) > 1.1 * h and station(t["text"])
                    ],
                    key=lambda q: q[0],
                )
                if len(rows) < 2 or len({t["n"] for _, t in rows}) != len(rows):
                    continue
                if rows[0][0] * rows[-1][0] <= 0:
                    continue
                key = tuple(sorted(t["instance"] for _, t in fieldrow + rows))
                if key in seen:
                    continue
                gap = min(abs(np.diff([y for y, _ in rows])))
                if gap < 1.3 * h:
                    continue
                grid = defaultdict(list)
                for j, (_, t) in enumerate(fieldrow, 1):
                    grid[0, j] = [t]
                for i, (_, t) in enumerate(rows, 1):
                    grid[i, 0] = [t]
                field_ids = {t["instance"] for _, t in fieldrow + rows}
                for x, y, t in positions:
                    if t["instance"] in field_ids:
                        continue
                    i = min(range(len(rows)), key=lambda i: abs(rows[i][0] - y))
                    j = min(range(len(fieldrow)), key=lambda j: abs(fieldrow[j][0] - x))
                    if (
                        abs(rows[i][0] - y) < gap * 0.42
                        and abs(fieldrow[j][0] - x) < min(steps) * 0.42
                    ):
                        grid[i + 1, j + 1].append(t)
                cells = interpret(grid, len(rows) + 1, len(fieldrow) + 1)
                if cells and sum(c["value"] is not None for c in cells) >= 2:
                    seen.add(key)
                    yield dict(
                        layout=layout,
                        representation="text_alignment_candidate",
                        cells=cells,
                        origin_wcs=o.tolist(),
                        paper_basis=[u.tolist(), v.tolist()],
                    )
