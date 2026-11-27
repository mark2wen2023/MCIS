"""S2.1 的建模范围由原始观测重算。所有准入仅限研究。"""
import re

from cad_input import declarations


def drawing_notes(texts):
    pattern = r"origin|原点|symmetric|symmetry|对称|asymmetr|half.breadth|左右舷|左舷|右舷|[左右][^\s]{0,12}(?:油柜|水柜)|\bport\b|starboard|完整型值范围|offset domain|x\s+forward|y\s+port|z\s+up"
    return [{k:t[k] for k in ("instance","handle","layout","text","p")} for t in texts if re.search(pattern,t["text"],re.I)]


def evidence(src, instances):
    return [{"source_sha256":src,"instance":h} for h in dict.fromkeys(instances) if h]


def fields(g):
    sources, ambiguities, conflicts, blocked, allowed, features = [], [], [], [], [], []
    for inv in g["inventory"]:
        notes = inv.get("registration_notes", [])
        sources.extend(evidence(inv["source_sha256"],[n["instance"] for n in notes if re.search(r"origin|原点",n["text"],re.I)]))
        side = [n["instance"] for n in notes if re.search(r"左舷|右舷|左.*(?:油柜|水柜)|右.*(?:油柜|水柜)|port|starboard",n["text"],re.I)]
        if side:
            ambiguities.append(dict(kind="sheet_local_side_annotation",scope="same_view_only",evidence=evidence(inv["source_sha256"],side)))
    for curve in g["curves"]:
        if curve["kind"] in ("chine","keel","deck_edge","bow","stern"):
            features.append(dict(kind=curve["kind"],confidence=curve["confidence"],evidence=evidence(curve["source_sha256"],[curve["instance"]])))
    seen_signs = {}
    for c in g["curves"]:
        if len({v["y_sign"] for v in c["ship_coordinate_candidates"]}) > 1:
            seen_signs.setdefault(c["source_sha256"],[]).append(c["instance"])
    for src,handles in seen_signs.items():
        ambiguities.append(dict(kind="transverse_sign",scope="signed_geometry_and_asymmetric_components",evidence=evidence(src,handles)))
    for t in g["tables"]:
        src = t["source_sha256"]
        for c in t["cells"]:
            if c["status"] == "conflict":
                conflicts.append(dict(kind="contradictory_printed_values",station_m=c["station_m"],level_m=c["level_m"],raw_values=c["raw_texts"],evidence=evidence(src,c["instances"])))
        cells = {tuple(c["instances"]):c for c in t["cells"] if c["instances"]}
        for obs in t.get("height_unit_check",{}).get("observations",[]):
            c=cells.get(tuple(obs["value_instances"]))
            if c is None or c["value_m"] is None or not re.search("甲板|deck",c["field_label"],re.I):
                continue
            residual=obs["geometry_height_m"]-c["value_m"]
            if abs(residual)>0.025:
                conflicts.append(dict(kind="deck_note_vs_section_endpoint",station_m=c["station_m"],level_m=None,printed_m=c["value_m"],section_endpoint_m=obs["geometry_height_m"],residual_m=residual,comparison_limit_m=0.025,side_profile_candidates=obs.get("side_profile_candidates",[]),evidence=evidence(src,[*c["instances"],obs["curve"],*(h for p in obs.get("side_profile_candidates",[]) for h in [p["curve"],p["label"],*p["grid_handles"]])])))
    for item in conflicts:
        blocked.append(dict(scope="deck_to_section_join" if item["kind"].startswith("deck_") else "offset_cell",station_m=item["station_m"],level_m=item["level_m"],evidence=item["evidence"]))
    # Acceptance uses a complete, explicitly bounded half-breadth dataset. A general
    # collection of measured points cannot by itself establish coverage or closure.
    state="blocked"
    if len(g["tables"]) == 1 and not conflicts and not g["issues"]:
        t = g["tables"][0]
        src=t["source_sha256"]
        inv=next(i for i in g["inventory"] if i["source_sha256"]==src)
        notes=[n for n in inv["registration_notes"] if n["layout"]==t["layout"]]
        decl=declarations([dict(handle=n["instance"],text=n["text"],type="TEXT") for n in notes])
        domain=[]
        num=r"([-+]?(?:\d+(?:\.\d*)?|\.\d+))"
        for n in notes:
            m=re.fullmatch(r"OFFSET DOMAIN X "+num+" TO "+num+" Z "+num+" TO "+num+" M; FULL MOULDED HULL; FLAT CLOSURES",n["text"].upper().strip())
            if m: domain.append((n,[float(a) for a in m.groups()]))
        cs=t["cells"]
        xs={c["station_m"] for c in cs}
        zs={c["level_m"] for c in cs}
        complete=(None not in xs|zs and len(xs)>=2 and len(zs)>=2 and len({(c["station_m"],c["level_m"]) for c in cs})==len(cs)==len(xs)*len(zs) and
                  all(c["status"] in ("numeric","zero","duplicate") and c["value_m"] is not None and c["value_m"]>=0 for c in cs))
        if len(domain)==1 and complete and domain[0][1]==[min(xs),max(xs),min(zs),max(zs)] and decl["symmetric"]:
            handles=[domain[0][0]["instance"],*decl["notes"],*(h for c in cs for h in c["instances"])]
            if decl["frame"] and not seen_signs and len(g["inventory"])==1:
                state="full_research"
            else:
                state="local_symmetric"
            allowed.append(dict(scope="bounded_symmetric_hull",bounds_xz_m=domain[0][1],evidence=evidence(src,handles)))
            if state=="local_symmetric":
                ambiguities.append(dict(kind="transverse_sign",scope="table_half_breadth_sign",candidate_y_multipliers=[1,-1],evidence=evidence(src,decl["notes"])))
                blocked.append(dict(scope="absolute_frame_and_signed_components",evidence=evidence(src,handles[:1])))
    if not allowed:
        blocked.append(dict(scope="whole_hull",evidence=[]))
    return dict(coordinate_system=dict(axes=["x_forward","y_port","z_up"],length_unit="m",origin_evidence=sources),
                topology_features=features,uncertainties=ambiguities,conflicts=conflicts,
                modeling_admission=dict(state=state,engineering_approved=False,allowed_regions=allowed,blocked_regions=blocked))
