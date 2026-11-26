"""区分 CAD 原始几何、文字指认、曲线族候选与已验证船轴坐标。"""
from collections import defaultdict
import re
import numpy as np
from .tables import WL,NUM


def family(s):
    rules=[("deck_edge",r"甲板边|deckedge|deckline"),("chine",r"折角线?|chine|knuckle"),("keel",r"龙骨|船底线|keel"),
        ("bow",r"艏轮廓|首轮廓|艏柱|stemprofile|bow(?:profile|contour)"),
        ("stern",r"艉轮廓|尾轮廓|艉柱|stern(?:profile|contour)"),
        ("center_profile",r"中纵剖|中心纵剖|centerlineprofile|centrelineprofile|sheerprofile"),
        ("buttock",r"纵剖|buttock|\d剖"),("waterline",r"水线|waterline|(?:\d|^)wl"),
        ("section",r"横剖|stationsection|section|bodyline")]
    return next((k for k,p in rules if re.search(p,s)),None)


def distance(p,poly):
    if len(poly)<2:return np.inf
    a=poly[:-1];v=np.diff(poly,axis=0);den=(v*v).sum(axis=1)
    t=np.clip(((p-a)*v).sum(axis=1)/np.maximum(den,1e-30),0,1)
    return float(np.min(np.linalg.norm(p-a-t[:,None]*v,axis=1)))


def hits(x,pp):
    a,b=pp[:-1],pp[1:]
    ok=(np.minimum(a[:,0],b[:,0])<=x)&(np.maximum(a[:,0],b[:,0])>=x)&(np.abs(b[:,0]-a[:,0])>1e-12)
    return a[ok,1]+(x-a[ok,0])/(b[ok,0]-a[ok,0])*(b[ok,1]-a[ok,1])


def offset_match(frame,points,cells):
    view=frame["view"]
    axes={k:points@np.array(v[:2])+v[2] for k,v in frame["axes"].items()}
    if view=="YZ":
        p=np.column_stack((axes["Z"],abs(axes["Y"])));kind="section";key="station_m";coord="level_m"
        if np.ptp(axes["Z"])<.2*np.ptp(axes["Y"]):return []
    elif view=="XY":
        p=np.column_stack((axes["X"],abs(axes["Y"])));kind="waterline";key="level_m";coord="station_m"
    else:return []
    errors=defaultdict(list)
    for c in cells:
        if c["value_m"] is None or c[key] is None or c[coord] is None or c["level_m"] is None:continue
        v=hits(c[coord],p)
        if len(v):errors[c[key]].append((min(abs(v-c["value_m"])),c["instances"]))
    scored=[]
    for level,err in errors.items():
        if len(err)>=2:
            rms=float(np.sqrt(np.mean([v*v for v,_ in err])))
            scored.append(dict(kind=kind,fixed_m=level,rms_m=rms,n=len(err),value_instances=[s for _,items in err for s in items]))
    return sorted(scored,key=lambda r:r["rms_m"])[:3]


def extract(data,inv,tables,frames):
    cells=[c for t in tables for c in t["cells"]];excluded={h for c in cells for h in [*c["instances"],c["row_header"]["instance"],c["field_header"]["instance"]]}
    guide_labels=[(t,family(t["n"])) for t in data["texts"] if t["instance"] not in excluded and family(t["n"])]
    lines_doc=bool({"lines","section"}&set(inv["classes"]))
    selected=[]
    for c in data["curves"]:
        if not lines_doc and not guide_labels:continue
        # Structure sheets can contain thousands of bolt circles and ruling
        # lines; only typed source curves or directly labelled features enter.
        if not lines_doc and c["type"]=="LINE":continue
        points=np.asarray(c["samples"],dtype=float)
        if len(points)<2:continue
        pp=points[:,:2];lo=pp.min(0);hi=pp.max(0)
        candidates=[];geometry_matches=[];physical=[]
        for f in frames:
            if f["layout"]!=c["layout"] or "paper_bounds" not in f:continue
            low,high=np.array(f["paper_bounds"])
            if f["method"]=="explicit_controls" and f["status"]=="verified":
                if np.all(lo>=low-1e-8) and np.all(hi<=high+1e-8):
                    physical.append(dict(method="explicit_controls",controls=f["controls"],points_m=(np.column_stack((pp,np.ones(len(pp))))@np.array(f["paper_to_ship_m"]).T).tolist()))
                continue
            if f["method"]!="measured_grid":continue
            extent=high-low;pad=.36*extent
            if np.all(hi>=low-pad) and np.all(lo<=high+pad) and np.all((pp.mean(0)>=low-pad)&(pp.mean(0)<=high+pad)):
                tag={"YZ":"section","XY":"waterline","XZ":"buttock"}[f["view"]]
                candidates.append(dict(kind=tag,basis="view_family",view=f["view"]))
                if c["type"]=="SPLINE":
                    geometry_matches.extend(offset_match(f,pp,cells))
        labels=[]
        for t,kind in guide_labels:
            if t["layout"]!=c["layout"]:continue
            anchor=np.array(t["p"][:2]);h=max(t["height"],1e-6)
            if np.any(anchor<lo-3*h) or np.any(anchor>hi+3*h):continue
            d=distance(anchor,pp)/h
            if d<=2.5:labels.append((d,t,kind))
        labels.sort(key=lambda q:q[0])
        for d,t,kind in labels[:3]:candidates.append(dict(kind=kind,basis="near_text",label=t["instance"],text=t["text"],distance_text_heights=d))
        by_key={}
        for g in geometry_matches:
            key=(g["kind"],g["fixed_m"])
            if key not in by_key or by_key[key]["rms_m"]>g["rms_m"]:by_key[key]=g
        matches=sorted(by_key.values(),key=lambda g:g["rms_m"])
        kind="unknown";confidence="unknown"
        if matches and matches[0]["rms_m"]<.025 and (len(matches)==1 or matches[1]["rms_m"]>matches[0]["rms_m"]+.005):
            kind=matches[0]["kind"];confidence="cross_checked_candidate"
        elif labels and labels[0][0]<1.25 and len({k for d,t,k in labels if d<labels[0][0]+.5})==1:
            kind=labels[0][2];confidence="text_candidate"
        if c["type"]=="LINE" and not labels:continue
        if not lines_doc and not labels:continue
        selected.append({**c,"kind":kind,"confidence":confidence,"candidates":candidates,"offset_matches":matches[:3],
                         "ship_coordinates":physical if len(physical)==1 else [],"alignment_candidates":len(physical)})
    return selected
