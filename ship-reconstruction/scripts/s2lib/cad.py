"""以原图实体、块实例路径和模型空间位置为证据的只读适配器。"""

from collections import Counter
import math
import re
import unicodedata

import numpy as np
from ezdxf.entities.acad_table import read_acad_table_content
from ezdxf.lldxf.encoding import decode_dxf_unicode, decode_mif_to_unicode
from ezdxf.math import Matrix44
from ezdxf.path import make_path


def norm(text):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text)).casefold()


def xyz(p):
    return [float(v) for v in p]


def read(doc):
    data = dict(texts=[], segments=[], native=[], curves=[], issues=[], counts=Counter())

    def walk(layout, name, parent, path, blocks):
        for e in layout:
            typ = e.dxftype()
            h = e.dxf.handle
            if not h:
                continue
            key = "/".join([*path, h])
            ref = dict(handle=h, instance=key, layout=name)
            data["counts"][typ] += 1

            def w(p):
                return xyz(parent.transform(p))

            if typ == "INSERT":
                block = e.block()
                if block is None or e.dxf.name in blocks or len(blocks) >= 32:
                    data["issues"].append(dict(**ref, code="unresolved_block"))
                    continue
                for i, insert in enumerate(e.multi_insert() if e.mcount > 1 else [e]):
                    token = f"{h}[{i}]" if e.mcount > 1 else h
                    walk(
                        block,
                        name,
                        insert.matrix44() @ parent,
                        [*path, token],
                        blocks | {e.dxf.name},
                    )
                continue
            if typ in ("TEXT", "MTEXT", "ATTRIB", "ATTDEF"):
                if typ == "MTEXT":
                    anchor = e.dxf.insert
                    height = e.dxf.char_height
                else:
                    _, anchor, _ = e.get_placement()
                    anchor = e.ocs().to_wcs(anchor)
                    height = e.dxf.height
                raw_text = e.plain_text()
                text = decode_mif_to_unicode(decode_dxf_unicode(raw_text))
                if text.strip():
                    angle = math.radians(
                        e.get_rotation() if typ == "MTEXT" else e.dxf.get("rotation", 0)
                    )
                    u = parent.transform_direction((math.cos(angle), math.sin(angle), 0))
                    data["texts"].append(
                        dict(
                            **ref,
                            baseline=xyz(u),
                            text=text,
                            raw_cad_text=raw_text,
                            n=norm(text),
                            p=w(anchor),
                            height=float(height) * parent.transform_direction((0, 1, 0)).magnitude,
                        )
                    )
                continue
            if typ == "ACAD_TABLE":
                try:
                    values = read_acad_table_content(e)
                    tags = e.xtags.get_subclass("AcDbTable")
                    flags = [int(tag.value) for tag in tags if tag.code == 173]
                    merged = [
                        list(divmod(i, len(values[0])))
                        for i, flag in enumerate(flags)
                        if flag and values and values[0]
                    ]
                    data["native"].append(
                        dict(
                            **ref,
                            rows=values,
                            merged=merged,
                            insertion_wcs=w(e.get_insert_location()),
                        )
                    )
                except (ValueError, AttributeError, IndexError, KeyError) as exc:
                    data["issues"].append(
                        dict(**ref, code="unreadable_native_table", detail=str(exc))
                    )
                continue
            if typ not in ("LINE", "SPLINE", "LWPOLYLINE", "POLYLINE", "ARC", "CIRCLE", "ELLIPSE"):
                continue
            raw = {}
            points = []
            if typ == "LINE":
                points = [e.dxf.start, e.dxf.end]
                raw = {"endpoints": list(map(xyz, points))}
                data["segments"].append(dict(**ref, a=w(points[0]), b=w(points[1])))
            elif typ in ("POLYLINE", "LWPOLYLINE"):
                points = list(e.points_in_wcs() if typ == "POLYLINE" else e.vertices_in_wcs())
                bulges = (
                    [float(v.dxf.get("bulge", 0)) for v in e.vertices]
                    if typ == "POLYLINE"
                    else [float(v[0]) for v in e.get_points("b")]
                )
                closed = e.is_closed if typ == "POLYLINE" else e.closed
                raw = dict(
                    vertices=list(map(xyz, points)),
                    bulges=bulges,
                    closed=bool(closed),
                    extrusion=xyz(e.dxf.get("extrusion", (0, 0, 1))),
                )
                for i in range(len(points) if closed else max(0, len(points) - 1)):
                    if not bulges[i]:
                        data["segments"].append(
                            dict(**ref, a=w(points[i]), b=w(points[(i + 1) % len(points)]))
                        )
            elif typ == "SPLINE":
                raw = dict(
                    degree=e.dxf.degree,
                    flags=e.dxf.flags,
                    knots=list(e.knots),
                    weights=list(e.weights),
                    control_points=[xyz(v) for v in e.control_points],
                    fit_points=[xyz(v) for v in e.fit_points],
                )
                for attr in ("start_tangent", "end_tangent", "extrusion"):
                    if e.dxf.hasattr(attr):
                        raw[attr] = xyz(e.dxf.get(attr))
            else:
                for attr in (
                    "center",
                    "major_axis",
                    "extrusion",
                    "radius",
                    "ratio",
                    "start_angle",
                    "end_angle",
                    "start_param",
                    "end_param",
                ):
                    if e.dxf.is_supported(attr) and e.dxf.hasattr(attr):
                        value = e.dxf.get(attr)
                        raw[attr] = xyz(value) if hasattr(value, "x") else float(value)
            # Keep native parameters untouched. Samples are only a location index.
            row = dict(**ref, type=typ, geometry=raw)
            if path:
                row["source_to_wcs_row_major_ezdxf"] = list(parent)
            if typ == "LINE":
                samples = [w(p) for p in points]
            else:
                try:
                    path_obj = make_path(e)
                    samples = [w(p) for p in path_obj.approximate(segments=12)]
                except (ValueError, TypeError, ZeroDivisionError, ArithmeticError) as exc:
                    samples = []
                    data["issues"].append(
                        dict(**ref, code="curve_sampling_failed", detail=str(exc))
                    )
            row["samples"] = samples
            data["curves"].append(row)

    for layout in doc.layouts:
        walk(layout, layout.name, Matrix44(), [], set())
    return data


CLASSES = {
    "lines": r"型线图|线型图|linesplan|bodylinesplan|linesdrawing|buttock(?:lines?|plan|view)|纵剖线(?:图)?|half.?breadthplan|sheerplan",
    "offset_table": r"型值表|型线坐标表|tableof(?:hull)?offsets|offsetstable|offsettable|tableofordinates",
    "arrangement": r"总布置图?|generalarrangement",
    "structure": r"基本结构图?|全船结构图|basicstructur|structuralplan|structuralprofile|framingplan|剖面结构图",
    "section": r"(?:典型|中横|横|船中|中部).*?剖面(?:结构)?图|主要典型剖面|midshipsection|typical(?:cross)?section|bodyplan|横剖线图",
    "capacity": r"舱容(?:量)?图|舱容表|tankcapacityplan|capacityplan|capacitytable",
}


def inventory(data):
    regions = []
    for t in data["texts"]:
        for kind, pattern in CLASSES.items():
            if re.search(pattern, t["n"]):
                regions.append(dict(kind=kind, anchor=t, layout=t["layout"], basis="printed_title"))
    facts = []
    for t in data["texts"]:
        n = t["n"]
        if re.fullmatch(r"(?:比例|scale)?[：:=]?1[:/]\d+(?:\.\d+)?", n):
            facts.append(dict(kind="paper_scale", text=t["text"], evidence=t))
        if re.search(r"基线|中心线|原点|baseline|centerline|centreline|origin|^(bl|cl)$", n):
            facts.append(dict(kind="datum_label", text=t["text"], evidence=t))
        if re.search(
            r"侧视|半宽水线|横剖线图|俯视|bodyplan|profileview|planview|half.?breadthplan", n
        ):
            facts.append(dict(kind="view_label", text=t["text"], evidence=t))
    return dict(
        classes=sorted({r["kind"] for r in regions}),
        regions=regions,
        facts=facts,
        entity_instances=dict(data["counts"]),
        issues=data["issues"],
    )
