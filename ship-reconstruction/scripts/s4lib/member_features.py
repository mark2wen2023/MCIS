"""图示T形截面与有标注的圆角舱口。保存原边、圆弧和投影范围。"""
from collections import defaultdict
import re
import numpy as np
from shapely.geometry import LineString, Point
from .notes import normalized
from .panels import METRE


def tee_sections(row, curves):
    result=[]
    for spec in row["profiles"]:
        if spec["family"]!="T" or "/" not in spec["raw"] or len(spec["values"])!=4:continue
        tf,width,tw,depth=spec["values"]
        if any(v is None or v<=0 for v in (tf,width,tw,depth)) or tw>=width:continue
        for lead in row["leaders"]:
            if len(lead["target_instances"])!=1:continue
            target=curves.get(lead["target_instances"][0])
            if not target or target["type"]!="LINE":continue
            w=np.asarray(target["samples"])[:,:2]
            vec=w[1]-w[0]; span=np.linalg.norm(vec)
            if span<=0:continue
            ratio=depth/span
            hits=[];tol=max(span*1e-5,1e-9)
            for c in curves.values():
                if c["layout"]!=row["layout"] or c["type"]!="LINE" or c["instance"].rpartition("/")[0]!=target["instance"].rpartition("/")[0]:continue
                pts=np.asarray(c["samples"])[:,:2];u=pts[1]-pts[0];length=np.linalg.norm(u)
                if abs(length*ratio-width)>tol*ratio or abs(u@vec)>tol*length:continue
                if min(np.linalg.norm(pts.mean(axis=0)-p) for p in w)>tol:continue
                hits.append(c["instance"])
            if len(hits)!=1:continue
            result.append(dict(kind="nominal_tee_section",note=row["instance"],source_sha256=row["source_sha256"],
                 evidence=[row["instance"],*lead["handles"],target["instance"],hits[0]],web_centerline_wcs=w.tolist(),
                 flange_centerline_wcs=curves[hits[0]]["samples"],specification=spec,
                 section_in_printed_units=[[-tw/2,0],[tw/2,0],[tw/2,depth],[width/2,depth],
                   [width/2,depth+tf],[-width/2,depth+tf],[-width/2,depth],[-tw/2,depth]],
                 physical_unit=spec["unit"],unit_per_drawing_unit=ratio,installed_member=None,
                 unknowns=["member_identity","member_length","root_radius","weld","installed_xyz"]))
    return result


OPENING=re.compile(r"(?:货舱(?:口)?|舱口|hatch(?:way)?|cargo hold)\s*[:：=]?\s*(\d+(?:\.\d+)?)\s*[x×*]\s*(\d+(?:\.\d+)?)\s*(mm|cm|m|in)\b",re.I)


def straight_sides(centers,radius,mat,anchor,lines,tol):
    segments=[]
    for axis in (0,1):
        for sign in (-1,1):
            side=[p for pair,p in centers.items() if pair[axis]==sign]
            delta=np.eye(2)[axis]*radius*sign
            a,b=((q+delta)@mat.T+anchor for q in side)
            ends=[(h,l) for h,l in lines if l.distance(Point(a))<=tol and l.distance(Point(b))<=tol]
            if len(ends)!=1:return []
            h,l=ends[0]
            segments.append(dict(handle=h,trimmed_wcs=[a.tolist(),b.tolist()],source_wcs=list(map(list,l.coords))))
    return segments


def openings(data,src):
    found=[]
    for t in data["texts"]:
        match=OPENING.search(normalized(t["text"]))
        if not match:continue
        dims=np.array([float(match[1]),float(match[2])])*METRE[match[3].lower()]
        if min(dims)<=0:continue
        u=np.asarray(t["baseline"][:2]);u=u/np.linalg.norm(u)
        mat=np.column_stack((u,[-u[1],u[0]]))
        anchor=np.array(t["p"][:2])
        curves=[c for c in data["curves"] if c["layout"]==t["layout"] and
                c["instance"].rpartition("/")[0]==t["instance"].rpartition("/")[0]]
        lines=[(c["instance"],LineString(np.array(c["samples"])[:,:2])) for c in curves if c["type"]=="LINE"]
        # Arcs with non-default extrusion or an inherited transform require a separate OCS check.
        arcs=[]
        for c in curves:
            g=c["geometry"]
            if c["type"]!="ARC" or "source_to_wcs_row_major_ezdxf" in c or not np.allclose(g.get("extrusion",[0,0,1]),[0,0,1]):continue
            if abs((g.get("end_angle",0)-g.get("start_angle",0))%360-90)>1e-5:continue
            center=np.array(g["center"][:2]);pts=np.array(c["samples"])[:,:2]
            if len(pts)<3:continue
            signs=np.sign((pts[len(pts)//2]-center)@mat).astype(int)
            endpoints=(pts[[0,-1]]-center)@mat/g["radius"]
            if max(min(np.linalg.norm(p-a) for a in ([signs[0],0],[0,signs[1]])) for p in endpoints)>1e-5:continue
            arcs.append((c["instance"],(center-anchor)@mat,g["radius"],tuple(signs)))
        hits=[]
        for factor in (.001,.01,1.,.0254):
            L,B=dims/factor
            near=[a for a in arcs if abs(a[1][0])<=L and abs(a[1][1])<=B]
            for first,p,r,signs in near:
                if signs!=(-1,-1) or 2*r>=min(L,B):continue
                tol=max(1e-9,min(L,B)*1e-6)
                mid=p+[(L-2*r)/2,(B-2*r)/2]
                if np.any(np.abs(mid)>=np.array([L,B])/2):continue
                others=[];side_centers={}
                for pair in [(-1,-1),(-1,1),(1,1),(1,-1)]:
                    target=mid+np.asarray(pair)*[(L-2*r)/2,(B-2*r)/2]
                    ok=[a for a in near if a[3]==pair and abs(a[2]-r)<tol and np.linalg.norm(a[1]-target)<tol]
                    if len(ok)!=1:break
                    others.append(ok[0][0]);side_centers[pair]=ok[0][1]
                if len(others)!=4:continue
                segments=straight_sides(side_centers,r,mat,anchor,lines,tol)
                if len(segments)!=4:continue
                # 同一组圆心的其他半径需要各自四弧、四切边。不能据此赋予材质或板厚。
                rings=[]
                alternatives=[a for a in near if a[3]==(-1,-1) and a[2]>r+tol and np.linalg.norm(a[1]-p)<tol]
                for _,_,radius,_ in alternatives:
                    rim=[]
                    for pair,center in side_centers.items():
                        candidates=[a for a in near if a[3]==pair and abs(a[2]-radius)<tol and np.linalg.norm(a[1]-center)<tol]
                        if len(candidates)!=1:break
                        rim.append(candidates[0][0])
                    if len(rim)!=4:continue
                    sides=straight_sides(side_centers,radius,mat,anchor,lines,tol)
                    if len(sides)!=4:continue
                    rings.append(dict(radius_m=radius*factor,extent_m=(dims+2*(radius-r)*factor).tolist(),
                        arc_handles=rim,straight_edges=sides,evidence=[*rim,*[item["handle"] for item in sides]],
                        material=None,thickness_m=None))
                hits.append(dict(kind="rounded_opening_projection",source_sha256=src,note=t["instance"],
                    nominal_size_m=dims.tolist(),radius_m=r*factor,m_per_drawing_unit=factor,
                    concentric_boundaries=rings,basis="printed_dimensions_and_eight_original_entities",arc_handles=others,straight_edges=segments,
                    evidence=[t["instance"],*others,*[s["handle"] for s in segments]],centroid_wcs=(mid@mat.T+anchor).tolist(),
                    material=None,cap_authorized=False,ship_position_m=None))
        if len(hits)==1:found+=hits
    return found


def spline_witness(curve, point, tolerance):
    """在非零结点区间上验证端点是否位于原生二维B样条。"""
    from scipy.interpolate import BSpline
    from scipy.optimize import minimize_scalar
    g=curve["geometry"]
    if curve["type"]!="SPLINE" or "source_to_wcs_row_major_ezdxf" in curve:return None
    poles=np.asarray(g.get("control_points",[])); knots=np.asarray(g.get("knots",[]))
    degree=g["degree"]
    if len(poles)<degree+1 or len(knots)!=len(poles)+degree+1 or np.any(np.diff(knots)<0):return None
    if np.any(point < poles[:,:2].min(axis=0)-tolerance) or np.any(point>poles[:,:2].max(axis=0)+tolerance):return None
    weights=np.asarray(g.get("weights") or [1.]*len(poles))
    if len(weights)!=len(poles) or min(weights)<=0:return None
    spline=BSpline(knots,np.column_stack(((poles[:,:2]-point)*weights[:,None],weights)),degree,extrapolate=False)
    def loss(param):
        v=spline(param)
        return float(np.dot(v[:2],v[:2])/v[2]**2)
    hits=[]
    for i in range(degree,len(poles)):
        a,b=knots[i:i+2]
        if b<=a:continue
        block=poles[i-degree:i+1,:2]
        if np.any(point<block.min(axis=0)-tolerance) or np.any(point>block.max(axis=0)+tolerance):continue
        # A positive witness suffices; an unlocated intersection stays unknown.
        res=minimize_scalar(loss,bounds=(a,b),method="bounded",options={"xatol":1e-15})
        val,param=min((loss(a),a),(loss(b),b),(res.fun,res.x))
        if val<=tolerance**2:hits.append((float(val**.5),float(param)))
    return min(hits) if hits else None


def support_contacts(structures,drawings):
    found=[];sources={d["sha256"]:d["data"] for d in drawings}
    for src,data in sources.items():
        lines={c["instance"]:c for c in data["curves"]}
        owners=defaultdict(list)
        for r in structures["observations"]:
            if r["source_sha256"]!=src:continue
            for l in r["leaders"]:
                if len(l["target_instances"])==1:
                    owners[l["target_instances"][0]].append((r,l))
        members=defaultdict(list)
        for m in structures["local_models"]:
            if m["source_sha256"]!=src or not m["frame_attachment"]:continue
            for edge in m["frame_attachment"]["boundary_handles"]:members[edge].append(m)
        for h,models in members.items():
            support=lines[h]; scale=models[0]["scale"]["m_per_drawing_unit"]
            for target,notes in owners.items():
                c=lines.get(target)
                if not c or c["type"]!="SPLINE" or c["layout"]!=support["layout"] or h.rpartition("/")[0]!=target.rpartition("/")[0]:continue
                for p in np.asarray(support["samples"])[:,:2]:
                    witness=spline_witness(c,p,1e-6/scale)
                    if witness is None:continue
                    for r,l in notes:
                        found.append(dict(kind="support_endpoint_on_section_curve",source_sha256=src,note=r["instance"],
                            evidence=[r["instance"],*l["handles"],target,h],support_edge=h,curve=target,
                            local_models=[m["id"] for m in models],point_wcs=p.tolist(),curve_parameter=witness[1],
                            residual_m=witness[0]*scale,tolerance_m=1e-6,physical_connection=None,ship_y_m=None))
    return found
