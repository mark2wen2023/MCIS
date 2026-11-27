"""从原文生成角钢和扁钢的名义截面。截面线不带未经证实的构件长度。"""
from collections import defaultdict
import re


def section_templates(observations):
    result=[]
    for row in observations:
        if row["type"] in ("unknown","compartment","tank"):continue
        for spec in row["profiles"]:
            a=spec["values"];family=spec["family"]
            if any(v is None or v<=0 for v in a) or "/" in spec["raw"] or "+" in spec["raw"]:continue
            if family in ("L","ANGLE","角钢","∠") and len(a) in (2,3):
                h,b,t=(a[0],a[0],a[1]) if len(a)==2 else a
                if min(h,b)<=t:continue
                pts=[[0,0],[b,0],[b,t],[t,t],[t,h],[0,h]]
                method="nominal_sharp_corner_angle"
            elif family in ("FB","扁钢","FLAT BAR") and len(a)==2:
                pts=[[0,0],[a[0],0],[a[0],a[1]],[0,a[1]]]
                method="nominal_flat_bar"
            else:continue
            result.append(dict(type=row["type"],source_sha256=row["source_sha256"],instance=row["instance"],spec=spec,method=method,
                               outer_loop_in_printed_units=pts,length_m=None,ship_position_m=None,unknowns=["installed_length","fillets","signed_orientation"]))
    return result


def profile_matches(rows):
    groups=defaultdict(list)
    for row in rows:
        if row["type"]=="unknown" or len(row["mentioned_types"])>2:continue
        for p in row["profiles"]:
            if any(v is None for v in p["values"]):continue
            groups[row["type"],p["family"],tuple(p["values"]),p["unit"],re.sub(r"[^/+×x*]","",p["raw"].lower()).replace("×","x").replace("*","x")].append(row)
    result=[]
    for (role,family,values,unit,_),group in groups.items():
        if len({r["source_sha256"] for r in group})<2:continue
        result.append(dict(type=role,family=family,values=list(values),unit=unit,status="same_specification_only",identity_confirmed=False,
                           evidence=[dict(source_sha256=r["source_sha256"],instance=r["instance"],frame_ranges=r["frame_ranges"]) for r in group]))
    return result
