"""由引线命中和真实图线围成的板件轮廓生成局部研究几何。"""
import hashlib
import math
import re
from collections import defaultdict
import numpy as np
import trimesh
from shapely import LineString, Point, Polygon, box, set_precision, union_all
from shapely.ops import polygonize
from geometry import quality
from .mesh_io import write_solid
from .annotations import LayoutIndex
from .notes import normalized
from .notes import NUM

METRE={"in":.0254,"m":1.,"cm":.01,"mm":.001}
UNITS={4:.001,5:.01,6:1.}


def ruler_scale(tip,layout,data,height):
    """寻找包围目标横坐标的同排连续肋号及独立印刷肋距，仅输出研究尺度。"""
    ticks=[];pitch=[]
    for t in data["texts"]:
        if t["layout"]!=layout:continue
        text=normalized(t["text"]).strip()
        if re.fullmatch(r"\d{1,4}",text):
            ticks.append((t,int(text)))
        m=re.search(r"(?:肋距|frame spacing)\s*(?:s\s*)?[:=：]?\s*("+NUM+r")\s*(mm|cm|m)\b",text,re.I)
        if m:pitch.append((t,float(m[1])*METRE[m[2].lower()]))
    nearby=sorted(ticks,key=lambda t:math.dist(t[0]["p"][:2],tip))[:70]
    candidates=[]
    for t,n in nearby:
        p=np.asarray(t["p"][:2]);u=np.array(t["baseline"][:2]);u/=np.linalg.norm(u);v=np.array([-u[1],u[0]])
        if abs((tip-p)@v)>16*height:continue
        group=sorted(((float((np.array(k["p"][:2])-p)@u),k,j) for k,j in nearby if abs((np.array(k["p"][:2])-p)@v)<max(.01,min(t["height"],k["height"])*.04)),key=lambda a:a[0])
        for a,b,c in zip(group,group[1:],group[2:]):
            if not a[0] <= (tip-p)@u <= c[0] or b[2]-a[2]!=c[2]-b[2] or b[2]==a[2]:continue
            d1=(b[0]-a[0])/abs(b[2]-a[2]);d2=(c[0]-b[0])/abs(c[2]-b[2])
            if d1<=0 or abs(d1-d2)>1e-4*d1:continue
            for factor in (.001,.01,1.):
                notes=[k for k,value in pitch if abs(value-factor*d1)<max(value*1e-4,1e-8)]
                if notes:
                    nearest=min(notes,key=lambda k:math.dist(k["p"][:2],tip))
                    candidates.append((abs((tip-p)@v),factor,[z[1]["instance"] for z in (a,b,c)]+[nearest["instance"]],[a[2],c[2]]))
    if not candidates:return None
    candidates.sort(key=lambda k:k[0]);distance=candidates[0][0]
    closest=[k for k in candidates if k[0]<=distance+height*.05]
    if len({k[1] for k in closest})!=1:return None
    return dict(m_per_drawing_unit=closest[0][1],basis="printed_frame_pitch_and_three_nearby_labels",handles=closest[0][2],nearby_frame_interval=closest[0][3])


def frame_attachment(cell,scale,idx,texts,height):
    """同一板边位于两支刻度之间的整数肋位；只有唯一解时报告局部肋号。"""
    if scale["basis"]!="printed_frame_pitch_and_three_nearby_labels":return None
    from itertools import product
    pools=[]
    first,last=(np.array(texts[k]["p"][:2]) for k in (scale["handles"][0],scale["handles"][2]))
    u=last-first
    if np.linalg.norm(u)<1e-10:return None
    u=u/np.linalg.norm(u)
    for label in scale["handles"][:3]:
        note=texts[label];p=np.asarray(note["p"][:2])
        v=np.array([-u[1],u[0]]);h=note["height"]
        choices=[]
        for i in idx.around(p,2*h):
            if i not in idx.is_line:continue
            ends=np.asarray(idx.paths[i].coords)
            delta=ends-p
            if np.ptp(delta@u)>h*1e-5:continue
            du=float(np.mean(delta@u));dv=min(abs(delta@v))
            if abs(du)>h or dv>2*h:continue
            choices.append((float(np.hypot(du,dv)),float(np.mean(ends@u)),idx.curves[i]["instance"]))
        if not choices:return None
        pools.append([(int(note["text"]),x,handle,x-p@u) for _,x,handle in choices])
    solutions={}
    for ticks in product(*pools):
        if np.ptp([v[3] for v in ticks])>height*.002:continue
        n0,n1,n2=[v[0] for v in ticks]
        x0,x1,x2=[v[1] for v in ticks]
        if abs(x1-x0-(x2-x0)*(n1-n0)/(n2-n0))>max(height*1e-4,1e-7):continue
        solutions[tuple(round(v[1],7) for v in ticks)]=[(n,x,h) for n,x,h,_ in ticks]
    if len(solutions)!=1:return None
    ticks=next(iter(solutions.values()))
    n=np.array([a[0] for a in ticks]);x=np.array([a[1] for a in ticks])
    pitch=(x[-1]-x[0])/(n[-1]-n[0])
    if abs(pitch)<1e-10 or max(abs(x-(x[0]+(n-n[0])*pitch)))>abs(pitch)*1e-4:return None
    answers=[]
    for h in cell["boundary_handles"]:
        j=next((j for j,c in enumerate(idx.curves) if c["instance"]==h),None)
        if j is None or j not in idx.is_line:continue
        e=np.asarray(idx.paths[j].coords)@u
        station=n[0]+(e.mean()-x[0])/pitch
        if np.ptp(e)<abs(pitch)*1e-4 and n.min()<=station<=n.max() and abs(station-round(station))<1e-4:
            answers.append((round(station),h))
    if len(set(i for i,h in answers))!=1:return None
    return dict(frame_number=answers[0][0],boundary_handles=[h for _,h in answers],grid_handles=[h for _,_,h in ticks],label_handles=scale["handles"][:3],basis="three_tick_lines_and_coincident_boundary")


def bounded_cells(idx,tip,radius,exclude,target_ids):
    center=np.array(tip)
    # Clip the search, then discard every cell touching its artificial boundary.
    clip=box(-radius,-radius,radius,radius);p=Point(0,0)
    precision=max(radius*1e-9,1e-8)
    lines=[];refs=[]
    for i in idx.around(tip,radius):
        c=idx.curves[i]
        if c["instance"] in exclude or c["type"] not in ("LINE","LWPOLYLINE","POLYLINE"):continue
        if any(c["geometry"].get("bulges",[])):continue
        pts=np.asarray(idx.paths[i].coords)-center
        geom=set_precision(LineString(pts).intersection(clip),precision)
        if not geom.is_empty and geom.length>precision:
            lines.append(geom);refs.append(c["instance"])
    if not lines:return []
    answer=[]
    for poly in polygonize(union_all(lines,grid_size=precision)):
        if poly.area<=precision**2 or not poly.is_valid or poly.interiors or poly.distance(p)>4*precision or poly.distance(clip.boundary)<=4*precision:continue
        outside=poly.exterior
        containing=poly.contains(p) and outside.distance(p)>4*precision
        if not containing and not target_ids:continue
        handles=[h for h,l in zip(refs,lines) if l.intersection(outside.buffer(precision*3)).length>precision*20]
        associated=containing or bool(set(target_ids)&set(handles))
        if associated:
            answer.append(dict(contour_wcs=(np.array(poly.exterior.coords)[:-1]+center).tolist(),boundary_handles=sorted(set(handles)),area_wcs2=poly.area,tip_relation="interior" if containing else "boundary"))
    return answer


def solid(profile,thickness,scale):
    pp=np.asarray(profile,dtype=float)
    origin=pp.min(axis=0)
    pp=(pp-origin)*scale
    # Candidate outlines with holes require their own positive evidence.
    polygon=Polygon(pp)
    from shapely import constrained_delaunay_triangles
    vertices=[];index={};faces=[]
    for face in constrained_delaunay_triangles(polygon).geoms:
        ix=[]
        for q in list(face.exterior.coords)[:-1]:
            if q not in index:index[q]=len(vertices);vertices.append(q)
            ix.append(index[q])
        faces.append(ix)
    mesh=trimesh.creation.extrude_triangulation(np.array(vertices),np.array(faces),thickness)
    return origin,mesh


def recover(drawings,notes,dest):
    results=[]
    for d in drawings:
        data=d["data"]; src=d["sha256"]; texts={t["instance"]:t for t in data["texts"]}
        use=[r for r in notes if r["source_sha256"]==src and r["type"] in {"bracket","plate","deck","floor","transverse_bulkhead","longitudinal_bulkhead","double_bottom_plate","bulkhead"} and r["leaders"] and r["modeling_status"]!="conflicting_dimensions" and len([v for v in r["dimensions"] if v["kind"]=="thickness"])==1]
        idxs={layout:LayoutIndex([c for c in data["curves"] if c["layout"]==layout],[]) for layout in {r["layout"] for r in use}}
        for r in use:
            t=texts[r["instance"]];idx=idxs[r["layout"]]
            thick=next(v for v in r["dimensions"] if v["kind"]=="thickness")
            if thick["value"]<=0:continue
            excluded=set(h for lead in r["leaders"] for h in lead["handles"])
            for lead in r["leaders"]:
                tip=np.array(lead["tip_wcs"][:2])
                radius=max(t["height"]*3,1e-7)
                cells=bounded_cells(idx,tip,radius,excluded,lead["target_instances"])
                # Do not select the smaller of two enclosed faces incident to an edge.
                if len(cells)!=1:
                    lead["local_cell_status"]="ambiguous" if cells else "no_bounded_cell"
                    lead["local_cell_candidates"]=cells
                    continue
                cell=cells[0]
                lead["local_cell_candidates"]=cells
                scale=ruler_scale(tip,r["layout"],data,t["height"])
                if scale is None and d["cad"].units in UNITS:
                    scale=dict(m_per_drawing_unit=UNITS[d["cad"].units],basis="source_INSUNITS",handles=[])
                if scale is None:
                    lead["local_cell_status"]="unresolved_scale"
                    continue
                # A bare t=... is not an approved millimetre measure. Only provide
                # a labelled alternative when other explicit thickness units support it.
                unit=thick["unit"];unit_handles=[r["instance"]]
                if unit is None:
                    cited=[(q,v) for q in notes if q["source_sha256"]==src and q["layout"]==r["layout"] for v in q["dimensions"] if v["kind"]=="thickness" and v["unit"]]
                    units={v["unit"] for q,v in cited}
                    if len(units)!=1:
                        lead["local_cell_status"]="unknown_thickness_unit"
                        continue
                    unit=units.pop()
                    unit_handles=[q["instance"] for q,v in cited if v["unit"]==unit]
                o,mesh=solid(cell["contour_wcs"],thick["value"]*METRE[unit],scale["m_per_drawing_unit"])
                qa=quality(mesh)
                if not qa["closed_verified"]:continue
                identifier=hashlib.sha256(repr((src,r["instance"],lead["handles"],cell["boundary_handles"])).encode()).hexdigest()[:20]
                file="local-"+identifier+".ply"
                write_solid(dest/file,mesh)
                basis="printed" if thick["unit"] else "same_sheet_thickness_unit_hypothesis"
                r["modeling_status"]="local_research_candidate"
                lead["local_cell_status"]="closed_local_candidate"
                results.append(dict(id=identifier,type=r["type"],asset=file,source_sha256=src,instance=r["instance"],leader=lead["handles"],
                    method="polygonized_original_edges_and_normal_extrusion",coordinate_frame="local_plate_axes_metres",ship_position_m=None,
                    paper_origin_wcs=o.tolist(),contour=cell,scale=scale,frame_attachment=frame_attachment(cell,scale,idx,texts,t["height"]),thickness_raw=thick,modeled_thickness_m=thick["value"]*METRE[unit],
                    thickness_unit_basis=basis,unit_evidence_handles=unit_handles,surface_side="unknown",material=r["material"],
                    unknowns=["ship_placement","as_built","connection","perforations_outside_observed_outline"]+([] if r["material"] else ["material"]),
                    quality=qa,estimated_volume_m3=abs(mesh.volume),engineering_approved=False))
    return results
