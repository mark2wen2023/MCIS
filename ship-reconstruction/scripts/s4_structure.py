"""从两幅有控制点的正交视图，登记并验证有标注的结构轮廓。"""
import argparse
import json
import re
from pathlib import Path
import ezdxf
import numpy as np
from shapely.geometry import Point, Polygon
from ezdxf.path import make_path
from cad_input import convert
from core.drawing_parser import fingerprint
from geometry import read_exchange, quality
from parts import extrude_registered
from s2lib import alignment, cad
from s4lib import annotations, panels, sections
from s4lib.mesh_io import write_solid
from s4lib.notes import parse

ROLES={"deck","transverse_bulkhead","longitudinal_bulkhead","frame","longitudinal","strong_beam","stiffener","compartment","tank","double_bottom_plate"}
PART=re.compile(r"PART\s+([\w.-]+)\s+(\w+)$",re.I)
NORMAL=re.compile(r"NORMAL\s*[:=]\s*([+-])([XYZ])$",re.I)
MEASURE=re.compile(r"(厚度|高度|THICKNESS|HEIGHT)\s*[:=：]",re.I)
LIMIT=1e-5


def views(drawings):
    records=[]
    for d in drawings:
        doc=d["cad"]
        data=d["data"] if "data" in d else cad.read(doc)
        frames=alignment.datum_controls(data)
        texts=[t for t in data["texts"] if t["layout"]=="Model" and "/" not in t["instance"]]
        document_links=[]
        for text in texts:
            ordinary=re.match(r"(图号|参见|详见)\s*[:=：]?\s*([\w.-]+)(?:\s+(?:rev|版次)\.?\s*[:=]?\s*([\w.-]+))?",text["text"].strip(),re.I)
            if ordinary:document_links.append(dict(role="DRAWING ID" if ordinary[1]=="图号" else "REF",id=ordinary[2].casefold(),revision=ordinary[3],instance=text["instance"]))
            link=re.fullmatch(r"(DRAWING ID|REF)\s*[:=]\s*([\w.-]+)",text["text"].strip(),re.I)
            if link:
                document_links.append(dict(role=link[1].upper(),id=link[2].casefold(),instance=text["instance"]))
        contours=[]
        for e in doc.modelspace().query("LWPOLYLINE"):
            if e.closed:
                pp=np.asarray(list(make_path(e).flattening(.0001)))[:,:2]
                polygon=Polygon(pp)
                if polygon.is_valid and polygon.area>0:
                    contours.append((e,pp,polygon))
        for t in texts:
            m=PART.fullmatch(t["text"].strip())
            natural=None if m else parse(t["text"])
            if not m and not (natural and natural["identity"] and natural["type"] in ROLES):continue
            row=dict(id=m[1] if m else natural["identity"],role=m[2].lower() if m else natural["type"],natural_identity=not bool(m),source_sha256=d["sha256"],part_handle=t["instance"],document_links=document_links,issues=[])
            records.append(row)
            if row["role"] not in ROLES:row["issues"].append("unrecognized_role")
            matches=[v for v in contours if v[2].covers(Point(t["p"][:2]))]
            if len(matches)!=1:
                row["issues"].append("missing_or_ambiguous_outline")
                continue
            e,pp,polygon=matches[0]
            if abs(polygon.convex_hull.area-polygon.area)>1e-12*polygon.area:
                row["issues"].append("nonconvex_projection_requires_review")
            if any(abs(v[0])>1e-12 for v in e.get_points("b")):
                row["issues"].append("curved_outline_requires_independent_tolerance")
            contained=[u for u in texts if polygon.covers(Point(u["p"][:2]))]
            controls=[f for f in frames if f["layout"]=="Model" and not f.get("block_instance") and f["status"]=="verified" and
                      np.all(np.column_stack((pp,np.ones(len(pp))))@np.asarray(f["hull_halfspaces"]).T <= 1e-8)]
            if len(controls)!=1:
                row["issues"].append("missing_or_ambiguous_transform")
                continue
            f=controls[0]
            M=np.asarray(f["paper_to_ship_m"])
            matrix=np.eye(4)
            matrix[:3,:2]=M[:,:2]
            cross=np.cross(M[:,0],M[:,1])
            matrix[:3,2]=cross/np.linalg.norm(cross)
            matrix[:3,3]=M[:,2]
            notes=[u for u in contained if MEASURE.match(u["text"].strip()) or (natural and u["instance"]==t["instance"] and any(v["kind"] in ("thickness","height") for v in natural["dimensions"]))]
            normals=[(u,NORMAL.fullmatch(u["text"].strip())) for u in contained if NORMAL.fullmatch(u["text"].strip())]
            row.update(outline_handle=e.dxf.handle,controls=f["controls"],matrix=matrix.tolist(),measure_handles=[u["instance"] for u in notes],
                       normal_handles=[u["instance"] for u,_ in normals],points_m=(np.column_stack((pp,np.ones(len(pp))))@M.T).tolist())
            if len(normals)==1:
                _,n=normals[0]
                row["normal"]=(np.eye(3)["XYZ".index(n[2].upper())]*(1 if n[1]=="+" else -1)).tolist()
    return records


def compute(drawings, dest, hull=None):
    from shapely import MultiPoint
    import igl
    notes=[];view_titles=[]
    for drawing in drawings:
        drawing["data"]=cad.read(drawing["cad"])
        items,titles=annotations.observations(drawing["data"],drawing["sha256"])
        notes.extend(items)
        view_titles.extend(dict(source_sha256=drawing["sha256"],**t) for t in titles)
    conflicts=annotations.target_conflicts(notes)
    observations=views(drawings)
    results=[]
    hull_qa=quality(hull) if hull is not None else None
    for key in sorted({r["id"] for r in observations}):
        rows=[r for r in observations if r["id"]==key]
        issues=sorted({s for r in rows for s in r["issues"]})
        r=dict(id=key,type=rows[0]["role"],sources=rows,unknowns=["material","joint_type"],assumptions=[],issues=issues,geometry_status="blocked")
        results.append(r)
        if len(rows)!=2 or len({v["source_sha256"] for v in rows})!=2 or len({v["role"] for v in rows})!=1:
            issues.append("two_unique_consistent_views_required")
        if not issues:
            a,b=rows
            links=lambda row,role:{v["id"] for v in row["document_links"] if v["role"]==role}
            if not (links(a,"REF") & links(b,"DRAWING ID") or links(b,"REF") & links(a,"DRAWING ID")):
                issues.append("missing_cross_sheet_reference")
        if not issues:
            revisions=[{v.get("revision") for v in row["document_links"] if v.get("revision")} for row in rows]
            if all(revisions) and revisions[0]!=revisions[1]:issues.append("revision_agreement_unresolved")
        if issues: continue
        primary=[v for v in rows if v["measure_handles"] or v["normal_handles"]]
        if len(primary)!=1 or len(primary[0]["measure_handles"])!=1:
            issues.append("missing_or_ambiguous_signed_measure")
            continue
        a=primary[0];b=next(v for v in rows if v is not a)
        M=np.asarray(b["matrix"])
        if "normal" not in a and a.get("natural_identity") and not a["normal_handles"]:
            axis=np.asarray(a["matrix"])[:3,2]
            elevations=(np.array(b["points_m"])-np.array(a["points_m"])[0])@axis
            if abs(min(elevations))<=LIMIT and max(elevations)>LIMIT:a["normal"]=axis.tolist()
            elif abs(max(elevations))<=LIMIT and min(elevations)<-LIMIT:a["normal"]=(-axis).tolist()
            if "normal" in a:a["normal_source"]=dict(source_sha256=b["source_sha256"],outline_handle=b["outline_handle"],controls=b["controls"])
        if "normal" not in a:
            issues.append("missing_or_ambiguous_signed_measure")
            continue
        normal=np.asarray(a["normal"])
        if abs(M[:3,2]@normal)>1e-7:
            issues.append("second_view_cannot_measure_extrusion")
            continue
        spec=dict(natural_identity=a["natural_identity"],role=a["role"],source_sha256=a["source_sha256"],outline_handle=a["outline_handle"],measure_handle=a["measure_handles"][0],matrix=a["matrix"],positive_normal=a["normal"])
        try:
            item,mesh,handles,qa=extrude_registered(drawings,[spec])[0]
        except ValueError as exc:
            issues.append(str(exc))
            continue
        basis=np.column_stack([v/np.linalg.norm(v) for v in (M[:3,0],np.cross(M[:3,2],M[:3,0]))])
        # This preview supports solid prisms whose independent projection is convex.
        poly=Polygon(np.asarray(b["points_m"])@basis)
        projected=MultiPoint(mesh.vertices@basis).convex_hull
        residual=projected.boundary.hausdorff_distance(poly.boundary)
        r["second_view_error_m"]=float(residual)
        if abs(poly.area-poly.convex_hull.area)>LIMIT**2 or residual>LIMIT:
            issues.append("independent_projection_conflict")
            continue
        r.update(method="registered_closed_outline_extrusion",dimension_m=item["length_m"],extent_m=mesh.extents.tolist(),bounds_m=mesh.bounds.tolist(),quality=qa,geometry_status="research_geometry_verified",
                 face_source=dict(source_sha256=a["source_sha256"],outline_handle=a["outline_handle"],measure_handle=a["measure_handles"][0],face_count=len(handles)))
        if hull is not None and hull_qa["closed_verified"]:
            vertices=np.ascontiguousarray(mesh.vertices)
            squared=igl.point_mesh_squared_distance(vertices,np.asarray(hull.vertices),np.asarray(hull.faces,dtype=np.int64))[0]
            r["hull_relation"]=dict(method="vertex_to_surface_distance",min_distance_m=float(np.sqrt(squared.min())),vertices_in_contact=int(np.count_nonzero(squared<=LIMIT**2)),tolerance_m=LIMIT)
        else:
            r["unknowns"].append("hull_attachment")
        r["asset"]=key+".ply"
        write_solid(dest/r["asset"],mesh)
        r["asset_sha256"]=fingerprint(dest/r["asset"])
    return dict(schema_version="4.0",section_templates=sections.section_templates(notes),profile_matches=sections.profile_matches(notes),conflicts=conflicts,local_models=panels.recover(drawings,notes,dest),components=results,observations=notes,view_titles=view_titles,identity_candidates=annotations.associations(notes),hull_quality=hull_qa,engineering_approved=False,view_tolerance_m=LIMIT)


def main(extension=None):
    import tempfile
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("input",type=Path)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--mode",choices=["model","observe"],default="model")
    p.add_argument("--oda",type=Path)
    p.add_argument("--hull-glb",type=Path)
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory() as tmp:
        drawings=[]
        for path in sorted(a.input.iterdir()):
            if path.suffix.lower() in (".dxf",".dwg"):
                sha=fingerprint(path)
                converted,adapter=convert(path,Path(tmp),a.oda)
                drawings.append(dict(sha256=sha,cad=ezdxf.readfile(converted),conversion=adapter,dxf_sha256=fingerprint(converted)))
                if fingerprint(path)!=sha:raise ValueError("输入图纸已改变")
        result=compute(drawings,a.out,read_exchange(a.hull_glb) if a.hull_glb else None)
        result["sources"]=[dict(source_sha256=d["sha256"],dxf_sha256=d["dxf_sha256"],conversion=d["conversion"]) for d in drawings]
        result["hull_sha256"]=fingerprint(a.hull_glb) if a.hull_glb else None
    (a.out/"structures.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
    if extension is not None:
        extension(drawings,result,a.out)
    if a.mode=="observe":return 0 if result["observations"] else 4
    if not result["components"] and result["local_models"]:return 0
    return 0 if result["components"] and all(v["geometry_status"]=="research_geometry_verified" for v in result["components"]) else 4


if __name__=="__main__":raise SystemExit(main())
