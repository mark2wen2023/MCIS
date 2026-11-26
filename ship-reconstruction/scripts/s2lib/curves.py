"""区分 CAD 原始几何、文字指认、曲线族候选与已验证船轴坐标。"""

from collections import defaultdict
import re
import numpy as np
from .tables import WL, NUM


def family(s):
    rules = [
        ("deck_edge", r"甲板边|deckedge|deckline"),
        ("chine", r"折角线?|chine|knuckle"),
        ("keel", r"龙骨|船底线|keel"),
        ("bow", r"艏轮廓|首轮廓|艏柱|stemprofile|bow(?:profile|contour)"),
        ("stern", r"艉轮廓|尾轮廓|艉柱|stern(?:profile|contour)"),
        ("center_profile", r"中纵剖|中心纵剖|centerlineprofile|centrelineprofile|sheerprofile"),
        ("buttock", r"纵剖|buttock|\d剖"),
        ("waterline", r"水线|waterline|(?:\d|^)wl"),
        ("section", r"横剖|stationsection|section|bodyline"),
    ]
    return next((k for k, p in rules if re.search(p, s)), None)


def distance(p, poly):
    if len(poly) < 2:
        return np.inf
    a = poly[:-1]
    v = np.diff(poly, axis=0)
    den = (v * v).sum(axis=1)
    t = np.clip(((p - a) * v).sum(axis=1) / np.maximum(den, 1e-30), 0, 1)
    return float(np.min(np.linalg.norm(p - a - t[:, None] * v, axis=1)))


def hits(x, pp):
    a, b = pp[:-1], pp[1:]
    ok = (
        (np.minimum(a[:, 0], b[:, 0]) <= x)
        & (np.maximum(a[:, 0], b[:, 0]) >= x)
        & (np.abs(b[:, 0] - a[:, 0]) > 1e-12)
    )
    return a[ok, 1] + (x - a[ok, 0]) / (b[ok, 0] - a[ok, 0]) * (b[ok, 1] - a[ok, 1])


def offset_match(frame, points, cells):
    view = frame["view"]
    axes = {k: points @ np.array(v[:2]) + v[2] for k, v in frame["axes"].items()}
    if view == "YZ":
        p = np.column_stack((axes["Z"], abs(axes["Y"])))
        kind = "section"
        key = "station_m"
        coord = "level_m"
        if np.ptp(axes["Z"]) < 0.2 * np.ptp(axes["Y"]):
            return []
    elif view == "XY":
        p = np.column_stack((axes["X"], abs(axes["Y"])))
        kind = "waterline"
        key = "level_m"
        coord = "station_m"
    else:
        return []
    errors = defaultdict(list)
    for c in cells:
        if c["value_m"] is None or c[key] is None or c[coord] is None or c["level_m"] is None:
            continue
        v = hits(c[coord], p)
        if len(v):
            errors[c[key]].append((min(abs(v - c["value_m"])), c["instances"]))
    scored = []
    for level, err in errors.items():
        if len(err) >= 2:
            rms = float(np.sqrt(np.mean([v * v for v, _ in err])))
            scored.append(
                dict(
                    kind=kind,
                    fixed_m=level,
                    rms_m=rms,
                    n=len(err),
                    value_instances=[s for _, items in err for s in items],
                )
            )
    return sorted(scored, key=lambda r: r["rms_m"])[:3]


def extract(data, inv, tables, frames):
    cells = [c for t in tables for c in t["cells"]]
    excluded = {
        h
        for c in cells
        for h in [*c["instances"], c["row_header"]["instance"], c["field_header"]["instance"]]
    }
    guide_labels = [
        (t, family(t["n"]))
        for t in data["texts"]
        if t["instance"] not in excluded and family(t["n"])
    ]
    lines_doc = bool({"lines", "section"} & set(inv["classes"]))
    selected = []
    for c in data["curves"]:
        if not lines_doc and not guide_labels:
            continue
        # Structure sheets can contain thousands of bolt circles and ruling
        # lines; only typed source curves or directly labelled features enter.

        points = np.asarray(c["samples"], dtype=float)
        if len(points) < 2:
            continue
        pp = points[:, :2]
        lo = pp.min(0)
        hi = pp.max(0)
        candidates = []
        geometry_matches = []
        physical = []
        for f in frames:
            if f["layout"] != c["layout"] or "paper_bounds" not in f:
                continue
            low, high = np.array(f["paper_bounds"])
            if f["method"] == "explicit_controls" and f["status"] == "verified":
                if (
                    np.all(lo >= low - 1e-8)
                    and np.all(hi <= high + 1e-8)
                    and np.all(
                        pp @ np.asarray(f["hull_halfspaces"])[:, :2].T
                        + np.asarray(f["hull_halfspaces"])[:, 2]
                        <= 1e-8
                    )
                ):
                    physical.append(
                        dict(
                            method="explicit_controls",
                            controls=f["controls"],
                            points_m=(
                                np.column_stack((pp, np.ones(len(pp))))
                                @ np.array(f["paper_to_ship_m"]).T
                            ).tolist(),
                        )
                    )
                continue
            if f["method"] != "measured_grid":
                continue
            extent = high - low
            pad = 0.36 * extent
            if (
                np.all(hi >= low - pad)
                and np.all(lo <= high + pad)
                and np.all((pp.mean(0) >= low - pad) & (pp.mean(0) <= high + pad))
            ):
                tag = {"YZ": "section", "XY": "waterline", "XZ": "buttock"}[f["view"]]
                candidates.append(dict(kind=tag, basis="view_family", view=f["view"]))
                if c["type"] == "SPLINE":
                    geometry_matches.extend(offset_match(f, pp, cells))
        labels = []
        for t, kind in guide_labels:
            if t["layout"] != c["layout"]:
                continue
            anchor = np.array(t["p"][:2])
            h = max(t["height"], 1e-6)
            if np.any(anchor < lo - 3 * h) or np.any(anchor > hi + 3 * h):
                continue
            d = distance(anchor, pp) / h
            if d <= 2.5:
                labels.append((d, t, kind))
        labels.sort(key=lambda q: q[0])
        for d, t, kind in labels[:3]:
            candidates.append(
                dict(
                    kind=kind,
                    basis="near_text",
                    label=t["instance"],
                    text=t["text"],
                    distance_text_heights=d,
                )
            )
        by_key = {}
        for g in geometry_matches:
            key = (g["kind"], g["fixed_m"])
            if key not in by_key or by_key[key]["rms_m"] > g["rms_m"]:
                by_key[key] = g
        matches = sorted(by_key.values(), key=lambda g: g["rms_m"])
        kind = "unknown"
        confidence = "unknown"
        if (
            matches
            and matches[0]["rms_m"] < 0.025
            and (len(matches) == 1 or matches[1]["rms_m"] > matches[0]["rms_m"] + 0.005)
        ):
            kind = matches[0]["kind"]
            confidence = "cross_checked_candidate"
        elif (
            labels
            and labels[0][0] < 1.25
            and len({k for d, t, k in labels if d < labels[0][0] + 0.5}) == 1
        ):
            kind = labels[0][2]
            confidence = "text_candidate"
        # An explicit view title may be placed above a single drawn feature.
        if not candidates and len(data["curves"]) == 1 and len({k for _, k in guide_labels}) == 1:
            label, tag = guide_labels[0]
            kind = tag
            confidence = "single_feature_view_candidate"
            candidates.append(dict(kind=tag, basis="single_feature_view", label=label["instance"]))
        # A full transverse trace runs from the centre plane to the side and
        # traverses depth. This identifies the family without assigning a station.
        if (
            kind == "unknown"
            and c["type"] == "SPLINE"
            and any(g.get("view") == "YZ" for g in candidates)
        ):
            for f in frames:
                if f.get("view") != "YZ" or f["layout"] != c["layout"]:
                    continue
                m = f["axes"]["Y"]
                y = pp @ np.array(m[:2]) + m[2]
                zc = f["axes"]["Z"]
                z = pp @ np.array(zc[:2]) + zc[2]
                if (
                    np.ptp(y) > 0
                    and np.ptp(z) > 0.25 * np.ptp(y)
                    and min(abs(y[0]), abs(y[-1])) < 1e-4
                    and max(abs(y[0]), abs(y[-1])) > 0.8 * np.ptp(y)
                ):
                    kind = "section"
                    confidence = "body_plan_shape_candidate"
                    break
        if (
            kind == "unknown"
            and c["type"] in ("SPLINE", "LWPOLYLINE", "POLYLINE")
            and "section" in inv["classes"]
        ):
            from shapely.geometry import Polygon, Point

            for region in inv["regions"]:
                if (
                    region["kind"] != "section"
                    or region["layout"] != c["layout"]
                    or not region.get("bounds_wcs")
                ):
                    continue
                border = Polygon(region["bounds_wcs"])
                if not all(border.covers(Point(v)) for v in (pp[0], pp[-1], pp.mean(0))):
                    continue
                u = np.asarray(region["anchor"]["baseline"][:2])
                u /= np.linalg.norm(u)
                hor = pp @ u
                vertical = pp @ np.array([-u[1], u[0]])
                span = np.ptp(hor)
                rise = np.ptp(vertical)
                if (
                    span <= 0
                    or rise / span < 0.25
                    or rise / span > 1.8
                    or abs(hor[-1] - hor[0]) < 0.9 * span
                ):
                    continue
                for dim in inv["dimensions"]:
                    if dim["kind"] != "beam":
                        continue
                    evidence = next(
                        (t for t in data["texts"] if t["instance"] == dim["handles"][0]), None
                    )
                    if not evidence or not border.covers(Point(evidence["p"][:2])):
                        continue
                    scale = [
                        q
                        for q in (1.0, 0.01, 0.001)
                        if 0.82 <= 2 * span * q / dim["value_m"] <= 1.02
                    ]
                    if scale:
                        kind = "section"
                        confidence = "framed_section_candidate"
                        candidates.append(
                            dict(
                                kind=kind,
                                basis="transverse_region_half_beam_span",
                                beam=dim,
                                proposed_m_per_drawing_unit=scale,
                                region_label=region["anchor"]["instance"],
                                fixed_station=None,
                            )
                        )
                        break
        if c["type"] == "LINE" and not labels and not candidates:
            continue
        if not lines_doc and not labels and not candidates:
            continue
        selected.append(
            {
                **c,
                "kind": kind,
                "confidence": confidence,
                "candidates": candidates,
                "offset_matches": matches[:3],
                "ship_coordinates": physical if len(physical) == 1 else [],
                "alignment_candidates": len(physical),
            }
        )
    return selected


def locate_in_space(curve_rows, frames):
    """生成带固定轴及符号候选的纸面到三维矩阵，保持逐实体身份。"""
    for curve in curve_rows:
        curve["ship_coordinate_candidates"] = []
        matches = curve["offset_matches"]
        if not matches or curve["confidence"] != "cross_checked_candidate":
            continue
        match = matches[0]
        view = {"section": "YZ", "waterline": "XY", "buttock": "XZ"}[match["kind"]]
        coords = np.array(curve["samples"])[:, :2]
        evidence = {
            h for g in curve["candidates"] if g["basis"] == "view_family" for h in [g["view"]]
        }
        if view not in evidence:
            continue
        seen = set()
        for frame in frames:
            if frame.get("view") != view or frame["layout"] != curve["layout"]:
                continue
            low, high = np.asarray(frame["paper_bounds"])
            pad = 0.36 * (high - low)
            if np.any(coords.mean(0) < low - pad) or np.any(coords.mean(0) > high + pad):
                continue
            for sign in (1, -1):
                matrix = np.array([frame["axes"].get(k, [0, 0, match["fixed_m"]]) for k in "XYZ"])
                matrix[1] *= sign
                key = tuple(np.round(matrix, 8).flatten())
                if key in seen:
                    continue
                seen.add(key)
                curve["ship_coordinate_candidates"].append(
                    dict(
                        status="candidate",
                        paper_to_ship_m=matrix.tolist(),
                        view=view,
                        fixed_axis={"YZ": "X", "XY": "Z", "XZ": "Y"}[view],
                        fixed_m=match["fixed_m"],
                        y_sign=sign,
                        fixed_axis_value_instances=match["value_instances"],
                        rms_at_offsets_m=match["rms_m"],
                        grid_evidence=frame["ticks"],
                        scope="纸面WCS乘齐次矩阵；左右舷解释待证",
                    )
                )


def height_units(curve_rows, table_rows):
    for table in table_rows:
        if table["unit_status"] != "unknown" or not table.get("unit_candidate"):
            continue
        observations = []
        for curve in curve_rows:
            if curve["kind"] != "section" or not curve["ship_coordinate_candidates"]:
                continue
            cand = curve["ship_coordinate_candidates"][0]
            points = np.asarray(curve["samples"])
            pts = (
                np.column_stack((points[:, :2], np.ones(len(points))))
                @ np.asarray(cand["paper_to_ship_m"]).T
            )
            yz = np.column_stack((abs(pts[:, 1]), pts[:, 2]))
            for c in table["cells"]:
                if (
                    c["value"] is None
                    or c["station_m"] != cand["fixed_m"]
                    or not re.search("高度|height", re.sub(r"\s+", "", str(c["group"]).lower()))
                ):
                    continue
                f = re.sub(r"\s+", "", c["field_label"])
                if "船底" in f:
                    expected = float(pts[:, 2].min())
                elif "甲板" in f:
                    expected = float(pts[-1, 2] if pts[-1, 2] > pts[0, 2] else pts[0, 2])
                else:
                    m = re.fullmatch(r"(" + NUM + r")剖", f)
                    if not m:
                        continue
                    candidates = hits(
                        float(m[1]) * (0.001 if table["unit_candidate"]["unit"] == "mm" else 1), yz
                    )
                    if len(candidates) != 1:
                        continue
                    expected = float(candidates[0])
                if expected > 0.1 and c["value"] > 0:
                    observations.append((c, curve["instance"], expected))
        stations = {c["station_m"] for c, _, _ in observations}
        if len(stations) < 3:
            continue
        scores = {}
        for unit, factor in (("mm", 0.001), ("cm", 0.01), ("m", 1.0)):
            errors = np.asarray([abs(c["value"] * factor - z) for c, _, z in observations])
            scores[unit] = float(np.median(errors))
        accepted = [u for u, e in scores.items() if e <= 0.025]
        if len(accepted) != 1:
            continue
        unit = accepted[0]
        table["height_unit_check"] = dict(
            unit=unit,
            median_abs_error_m=scores,
            observations=[
                dict(value_instances=c["instances"], curve=inst, geometry_height_m=z)
                for c, inst, z in observations
            ],
        )
        for c in table["cells"]:
            if re.search("高度|height", re.sub(r"\s+", "", str(c["group"]).lower())):
                c.update(
                    unit=unit,
                    unit_basis="cross_checked_section_heights",
                    value_m=None
                    if c["value"] is None
                    else c["value"] * {"m": 1.0, "cm": 0.01, "mm": 0.001}[unit],
                )


def geometry_handoff(curve_rows, frames, table_rows):
    locate_in_space(curve_rows, frames)
    height_units(curve_rows, table_rows)
    # A profile buttock has a fixed breadth. Compare the recovered height
    # columns at station intersections after their independent unit evaluation.
    for curve in curve_rows:
        if curve["kind"] != "buttock" or curve["type"] != "SPLINE":
            continue
        pp = np.asarray(curve["samples"])[:, :2]
        matches = {}
        for f in frames:
            if f.get("view") != "XZ" or f["layout"] != curve["layout"]:
                continue
            lo, hi = np.array(f["paper_bounds"])
            pad = 0.36 * (hi - lo)
            if np.any(pp.mean(0) < lo - pad) or np.any(pp.mean(0) > hi + pad):
                continue
            vals = (
                np.column_stack((pp, np.ones(len(pp)))) @ np.array([f["axes"][k] for k in "XZ"]).T
            )
            errors = defaultdict(list)
            for table in table_rows:
                if table["layout"] != curve["layout"]:
                    continue
                for c in table["cells"]:
                    m = re.fullmatch(r"(" + NUM + r")剖", c["field_label"].strip())
                    if not m or c["value_m"] is None or c["station_m"] is None:
                        continue
                    unit = c.get("unit")
                    if not unit:
                        continue
                    widths = hits(c["station_m"], vals)
                    if len(widths) != 1:
                        continue
                    key = float(m[1]) * {"mm": 0.001, "cm": 0.01, "m": 1.0}[unit]
                    errors[key].append((abs(widths[0] - c["value_m"]), c["instances"]))
            for fixed, es in errors.items():
                if len(es) < 2:
                    continue
                rms = float(np.sqrt(np.mean([e * e for e, _ in es])))
                if fixed not in matches or rms < matches[fixed]["rms_m"]:
                    matches[fixed] = dict(
                        kind="buttock",
                        fixed_m=fixed,
                        rms_m=rms,
                        n=len(es),
                        value_instances=[h for _, ids in es for h in ids],
                    )
        rows = sorted(matches.values(), key=lambda r: r["rms_m"])
        if rows:
            curve["offset_matches"] = rows[:3]
            if rows[0]["rms_m"] < 0.025 and (
                len(rows) == 1 or rows[1]["rms_m"] > rows[0]["rms_m"] + 0.005
            ):
                curve["confidence"] = "cross_checked_candidate"
    locate_in_space(curve_rows, frames)
