"""在有跨图引用的同名非中线控制特征上判别镜像，保留所有原候选。"""
import re
import numpy as np
from cad_input import declarations

PATTERN=re.compile(r"(?:LANDMARK|同名控制特征)\s+([\w.-]+)$",re.I)
TOLERANCE_M=1e-4


def collect(texts):
    return [dict(id=m[1].casefold(),instance=t["instance"],p=t["p"],layout=t["layout"])
            for t in texts if (m:=PATTERN.fullmatch(t["text"].strip()))]


def decide(g):
    docs={i["source_sha256"]:i for i in g["inventory"]}
    frames={d["source_sha256"]:d["frames"] for d in g["alignment"]}
    for curve in g["curves"]:
        src=curve["source_sha256"]
        candidates=curve["ship_coordinate_candidates"]
        if len(candidates)!=2 or {v["y_sign"] for v in candidates}!={-1,1}:
            continue
        support=[]
        for rel in g["relationships"]:
            if not rel["explicit_refs"] or src not in rel["sources"]:
                continue
            other=next(h for h in rel["sources"] if h!=src)
            anchors=docs[other].get("landmarks",[])
            for a in docs[src].get("landmarks",[]):
                if a["layout"]!=curve["layout"]:continue
                matches=[k for k in anchors if k["id"]==a["id"]]
                if len(matches)!=1 or sum(k["id"]==a["id"] for k in docs[src]["landmarks"])!=1:continue
                b=matches[0]
                notes=[dict(handle=n["instance"],type="TEXT",text=n["text"]) for n in docs[other]["registration_notes"] if n["layout"]==b["layout"]]
                decl=declarations(notes)
                if not decl["frame"]:continue
                p=np.r_[a["p"][:2],1.]
                q=np.r_[b["p"][:2],1.]
                # Use only landmarks within the subject curve trace. Mere
                # presence inside the same drawing or bounding box is insufficient.
                from .curves import distance
                poly=np.asarray(curve["samples"])[:,:2]
                M=np.asarray(candidates[0]["paper_to_ship_m"])
                if distance(p[:2],poly)*np.linalg.norm(M[:,:2],ord=2)>TOLERANCE_M:continue
                valid=[f for f in frames[other] if f["layout"]==b["layout"] and f["status"]=="verified" and
                       np.all(np.asarray(f["hull_halfspaces"])@q<=1e-8)]
                if len(valid)!=1:continue
                ref=np.asarray(valid[0]["paper_to_ship_m"])@q
                if abs(ref[1])<=TOLERANCE_M:continue
                signs=[v["y_sign"] for v in candidates if np.linalg.norm(np.asarray(v["paper_to_ship_m"])@p-ref)<=TOLERANCE_M]
                support.append(dict(id=a["id"],other_source=other,instances=[a["instance"],b["instance"]],target=ref.tolist(),
                                    signed_candidates=signs,controls=valid[0]["controls"],axis_notes=decl["notes"]))
        if support:
            signs={r["signed_candidates"][0] for r in support if len(r["signed_candidates"])==1}
            distinct_positions={tuple(np.round(r["target"],4)) for r in support}
            unique=(len(distinct_positions)>=2 and len(signs)==1 and all(len(r["signed_candidates"])==1 for r in support))
            curve["registration_decision"]=dict(status="cross_checked_sign" if unique else "unresolved",
                y_sign=next(iter(signs)) if unique else None,tolerance_m=TOLERANCE_M,witnesses=support)
