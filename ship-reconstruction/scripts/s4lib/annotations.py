"""按实际布局中可达实体，将标注、托线、箭尖与原图目标分别登记。"""
from collections import defaultdict
import re
import numpy as np
from shapely import Point, LineString, STRtree, box
from .notes import parse, normalized


def _context(instance):
    return instance.rpartition("/")[0]


class LayoutIndex:
    def __init__(self,curves,leaders):
        self.curves=[]
        self.paths=[]
        self.lines=[]
        for c in curves:
            pts=np.asarray(c["samples"])
            if len(pts)<2: continue
            path=LineString(pts[:,:2])
            if path.length<1e-12:continue
            i=len(self.paths)
            self.paths.append(path)
            self.curves.append(c)
            if c["type"]=="LINE":self.lines.append(i)
        self.tree=STRtree(self.paths)
        self.is_line=set(self.lines)
        self.leaders=leaders
        self.ends=STRtree([Point(v["vertices"][-1][:2]) for v in leaders])

    def around(self,p,r):
        return self.tree.query(box(p[0]-r,p[1]-r,p[0]+r,p[1]+r))

    def trace(self,t):
        p=np.asarray(t["p"][:2]);height=max(t["height"],1e-8)
        u=np.asarray(t["baseline"][:2]);u=u/max(np.linalg.norm(u),1e-12)
        normal=np.array([-u[1],u[0]])
        eps=max(height*.004,1e-8)
        result=[]
        def add(method,handles,tip):
            target=[self.curves[i]["instance"] for i in self.around(tip,eps) if self.curves[i]["instance"] not in handles and
                    self.paths[i].distance(Point(tip))<=eps]
            result.append(dict(method=method,handles=handles,tip_wcs=[float(v) for v in tip],target_instances=sorted(set(target)),tolerance_wcs=eps))
        for i in self.ends.query(box(*(p-height*3),*(p+height*3))):
            lead=self.leaders[i]
            if lead.get("annotation") and lead["annotation"]!=t["instance"]:continue
            if _context(lead["instance"])!=_context(t["instance"]):continue
            add("native_leader",[lead["instance"]],lead["vertices"][0][:2])
        if result:return result
        # The shelf follows the text baseline, including rotated text. A nearby
        # curve is never accepted solely by distance to the text insertion point.
        for i in self.around(p,2*height):
            if i not in self.is_line:continue
            shelf=self.curves[i];ends=np.asarray(self.paths[i].coords)
            if _context(shelf["instance"])!=_context(t["instance"]):continue
            delta=ends-p
            span=delta@u;off=delta@normal;length=np.ptp(span)
            if not .55*height<=length<=max(15,len(t["text"])*1.6)*height:continue
            if np.ptp(off)>eps or abs(off.mean())>.54*height or min(span)>.4*height or max(span)<-.4*height:continue
            for end in ends:
                for j in self.around(end,eps):
                    if j==i:continue
                    branch=self.curves[j]
                    if _context(branch["instance"])!=_context(t["instance"]):continue
                    if branch["type"] not in ("LINE","LWPOLYLINE","POLYLINE") or branch["geometry"].get("closed"):continue
                    pts=np.asarray(self.paths[j].coords)
                    if self.paths[j].length>12*height:continue
                    gaps=[np.linalg.norm(pts[k]-end) for k in (0,-1)]
                    if min(gaps)>eps:continue
                    tip=pts[-1 if gaps[0]<=gaps[1] else 0]
                    if abs((tip-end)@normal)<.12*height:continue
                    add("shelf_and_branch",[shelf["instance"],branch["instance"]],tip)
        return result


def observations(data,src):
    ents=defaultdict(list);native=defaultdict(list)
    for c in data["curves"]:ents[c["layout"]].append(c)
    for v in data.get("leaders",[]):native[v["layout"]].append(v)
    indices={layout:LayoutIndex(curves,native[layout]) for layout,curves in ents.items()}
    rows=[]
    titles=[]
    for t in data["texts"]:
        raw=normalized(t["text"]).strip()
        match=re.fullmatch(r"(?:(?:典型|基本|上层建筑|船体|甲板|结构|中|横|纵|肋位|\s)*)(?:横剖面图?|中纵剖面图?|侧视图?|俯视图?|平面图|剖视图)|body plan|profile view|plan view|section view",raw,re.I)
        if match:titles.append(dict(text=raw,instance=t["instance"],layout=t["layout"],anchor_wcs=t["p"]))
        values=parse(t["text"])
        if not values:continue
        paths=indices[t["layout"]].trace(t) if t["layout"] in indices else []
        conflict=any(len({d["value"] for d in values["dimensions"] if d["kind"]==kind and d["unit"]==unit})>1 for kind,unit in {(d["kind"],d["unit"]) for d in values["dimensions"]})
        status="conflicting_dimensions" if conflict else "observed"
        rows.append(dict(source_sha256=src,handle=t["handle"],instance=t["instance"],layout=t["layout"],text=t["text"],anchor_wcs=t["p"],leaders=paths,
                         modeling_status=status,ship_position_m=None, **values))
    return rows,titles


def associations(rows):
    groups=defaultdict(list)
    for r in rows:
        if r["identity"]:
            groups[r["identity"]].append(r)
    candidates=[]
    for key,group in groups.items():
        if len(group)<2:continue
        # A drawing-specific ID may be reused on another ship or revision. Preserve
        # overlapping dimensions and discrepancies without equating their instances.
        attrs=defaultdict(set)
        for r in group:
            for d in r["dimensions"]:attrs[(d["kind"],d["unit"])].add(d["value"])
        conflict=any(len(v)>1 for v in attrs.values()) or len({r["type"] for r in group if r["type"]!="unknown"})>1
        candidates.append(dict(identity=key,status="conflict" if conflict else "shared_id_candidate",
                          evidence=[dict(source_sha256=r["source_sha256"],instance=r["instance"]) for r in group]))
    return candidates
