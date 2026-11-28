"""从图上控制点或注记对应的栅线建立可复核的视图变换。"""

from collections import defaultdict, Counter
from fractions import Fraction
import itertools
import math
import re

import numpy as np
from scipy.spatial import ConvexHull

from .tables import NUM, WL, STA, metre

CONTROL = re.compile(
    rf"\bCONTROL\s+(\S+)\s+X\s*=\s*({NUM})\s+Y\s*=\s*({NUM})\s+Z\s*=\s*({NUM})\s*(mm|m)\s*$", re.I
)


def dimensions(texts):
    out = []
    for note in texts:
        for key, pat in (
            ("station_spacing", r"站距|stationspacing"),
            ("beam", r"^(?:船宽|型宽|mouldedbeam|beam)"),
            ("length", r"^(?:船长|垂线间长|lengthbetweenperpendiculars|lbp)"),
        ):
            if not re.search(pat, note["n"]):
                continue
            items = []
            for t in texts:
                if t["layout"] != note["layout"]:
                    continue
                m = re.fullmatch(rf"({NUM})(mm|m|毫米|米)", t["n"])
                if not m:
                    continue
                dx, dy = np.subtract(t["p"][:2], note["p"][:2])
                if abs(dy) < note["height"] * 0.65 and abs(dx) < note["height"] * 36:
                    items.append((abs(dx), t, metre(float(m[1]), m[2])))
            inline = re.search(
                rf"(?:站距|stationspacing|型宽|船宽|beam|lbp|船长)[:=：]?({NUM})(mm|m|毫米|米)$",
                note["n"],
            )
            if inline:
                items = [(0, note, metre(float(inline[1]), inline[2]))]
            if items:
                _, v, value = min(items, key=lambda o: o[0])
                out.append(dict(kind=key, value_m=value, handles=[note["instance"], v["instance"]]))
    return out


_IMPERIAL_ATOM = r"(?:\d+\s+\d+\s*/\s*\d+|\d+\s*/\s*\d+|\d+\s*[½¼¾⅛⅜⅝⅞]|[½¼¾⅛⅜⅝⅞]|\d+(?:\.\d*)?|\.\d+)"
_UNIT_FACTOR = {"in": 0.0254, "inch": 0.0254, "inches": 0.0254, "ft": 0.3048,
                "foot": 0.3048, "feet": 0.3048, "mm": 0.001, "cm": 0.01, "m": 1.0,
                "毫米": 0.001, "厘米": 0.01, "米": 1.0}


def _fractional_number(value):
    value = re.sub(r"\s+", " ", value.strip())
    unicode_fractions={"½":.5,"¼":.25,"¾":.75,"⅛":.125,"⅜":.375,"⅝":.625,"⅞":.875}
    if value[-1:] in unicode_fractions:
        whole=value[:-1].strip()
        return (float(whole) if whole else 0.0)+unicode_fractions[value[-1]]
    if " " in value:
        whole, fraction = value.split(" ", 1)
        return float(Fraction(int(whole), 1) + Fraction(fraction.replace(" ", "")))
    if "/" in value:
        return float(Fraction(value.replace(" ", "")))
    return float(value)


def dimension_annotation(text):
    """Parse one printed length or a two-axis size, retaining its original text."""
    raw = str(text).strip().replace("′", "'").replace("’", "'").replace("″", '"').replace("”", '"').replace("–", "-").replace("−", "-")
    scale = re.fullmatch(r"\s*(?:(?:scale|比例)\s*[:=：]?\s*)?1\s*[:/]\s*(\d+(?:\.\d+)?)\s*", raw, re.I)
    if scale:
        return dict(kind="paper_scale", denominator=float(scale[1]), unit=None, values=[], values_m=[], source_text=raw)
    pair = re.search(rf"(?<![\w.])({_IMPERIAL_ATOM})\s*[x×]\s*({_IMPERIAL_ATOM})\s*(mm|cm|毫米|厘米|inches|inch|in|m|米)(?![a-z])", raw, re.I)
    if pair:
        unit = pair[3].lower()
        vals = [_fractional_number(pair[1]), _fractional_number(pair[2])]
        return dict(kind="dimension_pair", values=vals, unit=unit,
                    values_m=[v * _UNIT_FACTOR[unit] for v in vals], source_text=raw)
    feet = re.search(rf"(?<![\w.])({_IMPERIAL_ATOM})\s*(?:ft\.?|feet|foot|')\s*(?:-\s*)?({_IMPERIAL_ATOM})?\s*(?:inches|inch|in\.?|\x22)?", raw, re.I)
    if feet and re.search(r"(?:ft\.?|feet|foot|')", feet[0], re.I):
        ft = _fractional_number(feet[1])
        inch = _fractional_number(feet[2]) if feet[2] else 0.0
        suffix = feet[0][feet[0].find(feet[2]) + len(feet[2]):] if feet[2] else ""
        if feet[2] and not re.search(r"(?:inches|inch|in\.?|\x22)\s*$", suffix, re.I):
            feet = None
        else:
            return dict(kind="dimension", values=[ft, inch] if feet[2] else [ft], unit="ft_in",
                        values_m=[ft * .3048 + inch * .0254], source_text=raw)
    inch = re.search(rf"(?<![\w.])({_IMPERIAL_ATOM})\s*(?:inches|inch|in\.?|\x22)(?![A-Za-z])", raw, re.I)
    if inch:
        value = _fractional_number(inch[1])
        return dict(kind="dimension", values=[value], unit="in", values_m=[value * .0254], source_text=raw)
    metric = re.search(rf"(?<![\w.])({_IMPERIAL_ATOM})\s*(mm|cm|毫米|厘米|m|米)(?![a-z])", raw, re.I)
    if metric:
        unit = metric[2].lower()
        value = _fractional_number(metric[1])
        return dict(kind="dimension", values=[value], unit=unit,
                    values_m=[value * _UNIT_FACTOR[unit]], source_text=raw)
    return None

def dimension_annotations(texts):
    records=[]
    for note in texts:
        parsed=dimension_annotation(note.get("text", ""))
        if parsed:
            records.append(dict(**parsed, handle=note["instance"], layout=note["layout"],
                                position=note["p"][:2], source="printed_CAD_text"))
    return records


def unit_declarations(texts):
    records=[]
    aliases={"millimeters":"mm","millimeter":"mm","millimetres":"mm","millimetre":"mm",
             "millimeter":"mm","millimetre":"mm","inches":"in","inch":"in",
             "feet":"ft","foot":"ft","m":"m","mm":"mm","cm":"cm",
             "米":"m","毫米":"mm","厘米":"cm"}
    for note in texts:
        raw=str(note.get("text",""));normalized=raw.casefold().replace("′","'").replace("″",'"')
        if not re.search(r"(?:units?|dimensions?|units\s+are|单位|尺寸单位)",normalized):continue
        m=re.search(r"(?:units?|dimensions?|单位|尺寸单位)\s*(?:are\s*)?(?:in\s*)?[:=：为]?\s*(millimeters?|millimetres?|inches?|inch|in|feet|foot|ft|mm|cm|m|毫米|厘米|米)(?![a-z])",normalized,re.I)
        if m:
            unit=aliases.get(m[1].lower(),m[1].lower())
            records.append(dict(unit=unit,handle=note["instance"],layout=note["layout"],
                                source_text=raw,source="explicit_unit_declaration"))
    return records


def datum_controls(data):
    groups = defaultdict(list)
    for t in data["texts"]:
        m = CONTROL.search(t["text"])
        if m:
            groups[
                t["layout"], t["instance"].rsplit("/", 1)[0] if "/" in t["instance"] else ""
            ].append(
                (
                    t,
                    m[1],
                    np.array([float(m[i]) for i in (2, 3, 4)])
                    * (0.001 if m[5].lower() == "mm" else 1),
                )
            )
    out = []
    for (layout, path), group in groups.items():
        p = np.array([t["p"][:2] for t, _, _ in group])
        q = np.array([a for _, _, a in group])
        f = dict(
            layout=layout,
            block_instance=path,
            method="explicit_controls",
            status="candidate",
            controls=[t["instance"] for t, _, _ in group],
        )
        out.append(f)
        if len(set(i for _, i, _ in group)) != len(group):
            f["status"] = "conflict"
            continue
        if len(p) < 3:
            continue
        o = p.mean(axis=0)
        X = np.column_stack((p - o, np.ones(len(p))))
        singular = np.linalg.svd(X[:, :2], compute_uv=False)
        if singular[-1] <= 1e-9 * singular[0]:
            continue
        if len(p) < 4:
            continue
        held = []
        for i in range(len(p)):
            mask = np.arange(len(p)) != i
            fit, _, rank, _ = np.linalg.lstsq(X[mask], q[mask], rcond=None)
            if rank != 3:
                break
            held.append(float(np.linalg.norm(X[i] @ fit - q[i])))
        if len(held) != len(p):
            continue
        f["leave_one_out_errors_m"] = held
        f["max_holdout_residual_m"] = max(held)
        f["control_pairs"] = [
            dict(instance=t["instance"], paper_wcs=t["p"], ship_m=qv.tolist()) for t, _, qv in group
        ]
        if max(held) > 1e-5:
            f["status"] = "conflict"
            continue
        fit = np.linalg.lstsq(X, q, rcond=None)[0].T
        if np.linalg.matrix_rank(fit[:, :2]) != 2:
            continue
        fit[:, 2] -= fit[:, :2] @ o
        planes = ConvexHull(p - o).equations.copy()
        planes[:, 2] -= planes[:, :2] @ o
        f.update(
            status="verified",
            paper_to_ship_m=fit.tolist(),
            hull_halfspaces=planes.tolist(),
            paper_bounds=[p.min(0).tolist(), p.max(0).tolist()],
        )
    return out


def axis_tag(t, spacing):
    s = t["n"]
    m = re.fullmatch(WL, s)
    if m:
        return "Z", float(m[1] or m[3]), m[2] or m[4]
    if s in ("bl", "baseline", "基线"):
        return "Z", 0.0, None
    if s in ("cl", "centerline", "centreline", "中心线"):
        return "Y", 0.0, None
    m = re.fullmatch(rf"({NUM})(mm|m)?剖|(?:buttock|纵剖线?)({NUM})(mm|m)?", s)
    if m:
        return "Y", float(m[1] or m[3]), m[2] or m[4]
    m = re.fullmatch(STA, s)
    if m and m[2]:
        return "X", metre(float(m[1]), m[2]), "m"
    if spacing and (m or re.fullmatch(NUM, s)):
        return "X", float(m[1] if m else s) * spacing, "m"


def measured_frames(data, spacing, table_handles):
    """通过标签附近的实际 CAD 直线求刻度。分开返回每种可行视图和横向符号。"""
    axes = []
    for layout in {t["layout"] for t in data["texts"]}:
        ss = [s for s in data["segments"] if s["layout"] == layout]
        if not ss:
            continue
        A = np.array([s["a"][:2] for s in ss])
        B = np.array([s["b"][:2] for s in ss])
        D = B - A
        ln = np.linalg.norm(D, axis=1)
        angles = np.arctan2(D[:, 1], D[:, 0]) % np.pi
        keys = Counter(np.round(angles[ln > 1e-6] % (np.pi / 2), 4))
        if not keys:
            continue
        theta = keys.most_common(1)[0][0]
        for phi in [theta, theta + np.pi / 2]:
            u = np.array([math.cos(phi), math.sin(phi)])
            v = np.array([-u[1], u[0]])
            mask = (ln > 1e-6) & (np.abs(D @ u) < 1e-5 * np.maximum(1, ln))
            ids = np.where(mask)[0]
            ca = (A[mask] @ u + B[mask] @ u) / 2
            low = np.minimum(A[mask] @ v, B[mask] @ v)
            high = np.maximum(A[mask] @ v, B[mask] @ v)
            clusters = []
            for t in data["texts"]:
                if t["layout"] != layout or t["instance"] in table_handles:
                    continue
                tag = axis_tag(t, spacing)
                if not tag:
                    continue
                label, val, unit = tag
                p = np.array(t["p"][:2])
                a, b = p @ u, p @ v
                h = max(t["height"], 1e-8)
                d = np.abs(ca - a)
                gap = np.maximum(0, np.maximum(low - b, b - high))
                sel = np.flatnonzero((d <= 2.5 * h) & (gap <= 7 * h) & (ln[ids] >= 1.5 * h))
                if not len(sel):
                    continue
                j = sel[np.argmin(d[sel] + 0.15 * gap[sel])]
                c = next(
                    (g for g in clusters if g["axis"] == label and abs(b - g["b"]) < 1.5 * h), None
                )
                if c is None:
                    c = dict(axis=label, b=b, records=[])
                    clusters.append(c)
                c["records"].append(
                    (val, unit, ca[j], ss[ids[j]]["instance"], t["instance"], low[j], high[j], h)
                )
            segment_index = {ss[i]["instance"]: i for i in ids}
            for g in clusters:
                rec = g["records"]
                if len({x[0] for x in rec}) < 3:
                    continue
                factor = 1.0 if g["axis"] == "X" else 0.001
                vals = np.array([metre(x[0], x[1]) if x[1] else x[0] * factor for x in rec])
                pos = np.array([x[2] for x in rec])
                best = None
                for i, j in itertools.combinations(range(len(rec)), 2):
                    if abs(pos[i] - pos[j]) < 1e-7 or vals[i] == vals[j]:
                        continue
                    scale = (vals[i] - vals[j]) / (pos[i] - pos[j])
                    intercept = vals[i] - scale * pos[i]
                    err = np.abs(pos * scale + intercept - vals)
                    good = err < 1e-4
                    if len(set(vals[good])) < 3:
                        continue
                    sig = (len(set(vals[good])), -float(np.max(err[good])))
                    if best is None or sig > best[0]:
                        best = (sig, scale, intercept, good, err)
                if best is None:
                    continue
                _, sc, ic, good, err = best
                rr = [r for r, k in zip(rec, good) if k]
                # The coarse angular bin is only a search index. Recover the
                # actual axis normal from the observed, labelled grid lines.
                indices = [segment_index[r[3]] for r in rr]
                normals = np.column_stack((-D[indices, 1], D[indices, 0])) / ln[indices, None]
                normals *= np.where(normals @ u < 0, -1., 1.)[:, None]
                precise_u = np.average(normals, axis=0, weights=ln[indices])
                precise_u /= np.linalg.norm(precise_u)
                precise_pos = (A[indices] + B[indices]) @ precise_u / 2
                origin = precise_pos.mean()
                sc, at_origin = np.polyfit(precise_pos-origin, vals[good], 1)
                ic = at_origin - sc*origin
                precise_err = np.abs(sc*precise_pos + ic - vals[good])
                if precise_err.max() > 1e-4:
                    continue
                corners = np.array(
                    [
                        u * x + v * y
                        for x in [min(r[2] for r in rr), max(r[2] for r in rr)]
                        for y in [min(r[5] for r in rr), max(r[6] for r in rr)]
                    ]
                )
                axes.append(
                    dict(
                        layout=layout,
                        axis=g["axis"],
                        coef=[*(precise_u * sc), ic],
                        scale=abs(sc),
                        scale_basis="station_or_explicit_unit"
                        if all(r[1] for r in rr)
                        else "millimetre_hypothesis",
                        bounds=[corners.min(0).tolist(), corners.max(0).tolist()],
                        ticks=[
                            dict(label=r[4], line=r[3], value_m=y, at=r[2])
                            for r, y in zip(rr, vals[good])
                        ],
                        max_grid_residual_m=float(np.max(precise_err)),
                    )
                )
    frames = []
    for a, b in itertools.combinations(axes, 2):
        if a["axis"] == b["axis"] or a["layout"] != b["layout"]:
            continue
        if abs(np.dot(a["coef"][:2], b["coef"][:2])) > 1e-6 * a["scale"] * b["scale"]:
            continue
        if abs(a["scale"] / b["scale"] - 1) > 1e-3:
            continue
        lo = np.maximum(a["bounds"][0], b["bounds"][0])
        hi = np.minimum(a["bounds"][1], b["bounds"][1])
        if np.any(hi - lo <= 0):
            continue
        f = dict(
            layout=a["layout"],
            method="measured_grid",
            status="candidate",
            paper_bounds=[lo.tolist(), hi.tolist()],
            view="".join(sorted([a["axis"], b["axis"]])),
            axes={a["axis"]: a["coef"], b["axis"]: b["coef"]},
            ticks=a["ticks"] + b["ticks"],
            max_grid_residual_m=max(a["max_grid_residual_m"], b["max_grid_residual_m"]),
            unresolved=["missing_out_of_plane_coordinate"]
            + (["port_starboard_sign"] if "Y" in (a["axis"], b["axis"]) else []),
        )
        if f["view"] == "YZ":
            # A split body plan uses both halves of the centreline. Only extend to
            # the outline of the other measured axis grid, never beyond its bounds.
            yaxis = next(axis for axis in (a, b) if axis["axis"] == "Y")
            zaxis = next(axis for axis in (a, b) if axis["axis"] == "Z")
            coef = np.array(yaxis["coef"][:2])
            zero = -yaxis["coef"][2] * coef / (coef @ coef)
            center = (lo + hi) / 2
            mirrored = center - 2 * coef * (coef @ (center - zero)) / (coef @ coef)
            shift = mirrored - center
            f["paper_bounds"] = [
                np.maximum(zaxis["bounds"][0], np.minimum(lo, lo + shift)).tolist(),
                np.minimum(zaxis["bounds"][1], np.maximum(hi, hi + shift)).tolist(),
            ]
            f["split_body_candidate"] = True
        frames.append(f)
    return frames, axes
