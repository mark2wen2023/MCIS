"""对同一原图中的横剖端点和有文字指认的侧视甲板边作独立交叉测量。"""
from collections import defaultdict
import numpy as np
from .curves import hits


def side_profile_observations(curves, frames, tables):
    profiles = []
    for c in curves:
        labels = [r for r in c["candidates"] if r.get("kind")=="deck_edge" and r["basis"]=="near_text" and r["distance_text_heights"]<=1.25]
        if c["type"]!="SPLINE" or c["kind"]!="deck_edge" or not labels:
            continue
        pp=np.asarray(c["samples"])[:,:2]
        for f in frames:
            if f.get("view")!="XZ" or f["layout"]!=c["layout"]:
                continue
            lo,hi=np.asarray(f["paper_bounds"])
            pad=0.36*(hi-lo)
            if np.any(pp.mean(0)<lo-pad) or np.any(pp.mean(0)>hi+pad):
                continue
            xz=np.column_stack((pp,np.ones(len(pp)))) @ np.asarray([f["axes"][k] for k in "XZ"]).T
            profiles.append((c,labels,f,xz))
    for t in tables:
        values=defaultdict(list)
        for c in t["cells"]:
            if c["station_m"] is None or c["value_m"] is None or not any(word in c["field_label"].lower() for word in ("甲板","deck")):
                continue
            for curve,labels,frame,pts in profiles:
                if curve["layout"]!=t["layout"]:
                    continue
                z=hits(c["station_m"],pts)
                if len(z)==1:
                    values[tuple(c["instances"])].append(dict(curve=curve["instance"],label=labels[0]["label"],height_m=float(z[0]),method="labelled_profile_polyline_intersection",grid_handles=sorted({k["line"] for k in frame["ticks"]})))
        for obs in t.get("height_unit_check",{}).get("observations",[]):
            obs["side_profile_candidates"]=values[tuple(obs["value_instances"])]
