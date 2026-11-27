"""在共同的船轴米制坐标中，核对闭合船体和结构实体的相交、接触与裁切。"""
import argparse
import json
from pathlib import Path
import numpy as np
import trimesh
from shapely import Polygon
from core.drawing_parser import fingerprint
from geometry import quality,read_exchange


def load(path):
    if path.suffix.lower()==".glb":
        return read_exchange(path)
    if path.suffix.lower()!=".ply":
        raise ValueError("支持船轴米制 PLY，或项目交换坐标的 GLB")
    mesh=trimesh.load_mesh(path,process=False)
    if not isinstance(mesh,trimesh.Trimesh):raise ValueError("输入需要三角网格")
    return mesh


def contact_area(A,B,pairs,tol):
    total=0.
    for i,j in pairs:
        a,b=A.triangles[i],B.triangles[j]
        normal=A.face_normals[i]
        if np.linalg.norm(np.cross(normal,B.face_normals[j]))>1e-10 or max(abs((b-a[0])@normal))>tol:continue
        u=a[1]-a[0];u=u/np.linalg.norm(u)
        uv=np.column_stack((u,np.cross(normal,u)))
        total+=Polygon((a-a[0])@uv).intersection(Polygon((b-a[0])@uv)).area
    return float(total)


def classify(hull,part,role):
    from igl.copyleft import cgal
    audit=[quality(m) for m in (hull,part)]
    result=dict(state="blocked",closure_verified=False,role=role,hull_quality=audit[0],component_quality=audit[1],
                metrics={},contact_area_m2=None,connection="unknown",engineering_approved=False)
    if not all(v["closed_verified"] for v in audit):
        result["reason"]="closed_consistent_manifold_solids_required"
        return result,None
    # Work about a local origin. Keep original coordinates for the returned mesh.
    origin=np.asarray(hull.bounds).mean(0)
    a=np.ascontiguousarray(hull.vertices-origin);b=np.ascontiguousarray(part.vertices-origin)
    F=np.asarray(hull.faces,dtype=np.int64);G=np.asarray(part.faces,dtype=np.int64)
    H=float(hull.volume);P=float(part.volume)
    def boolean(op):
        v,f,source=cgal.mesh_boolean(b,G,a,F,op)
        mesh=trimesh.Trimesh(v,f,process=False) if len(f) else None
        volume=0. if mesh is None else float(mesh.volume)
        return volume,mesh,source
    inside,cut,sources=boolean("intersection")
    outside,rest,_=boolean("minus")
    pairs=cgal.intersect_other(a,F,b,G,detect_only=True)[0]
    scale=max(hull.scale,part.scale)
    area=contact_area(hull,part,pairs,max(1e-12,scale*1e-12))
    tol=max(np.finfo(float).eps*max(H,P)*128,1e-12*min(H,P))
    result.update(metrics=dict(intersection_m3=inside,outside_m3=outside,component_m3=P,hull_m3=H,conservation_error_m3=abs(inside+outside-P),volume_tolerance_m3=tol),
                  contact_area_m2=area,intersecting_face_pairs=len(pairs))
    if abs(inside+outside-P)>tol or min(inside,outside)<-tol:
        result["reason"]="boolean_volume_inconsistent"
        return result,None
    if cut is not None:
        bodies=cut.split(only_watertight=False)
        if not len(bodies) or not all(quality(m)["closed_verified"] for m in bodies):
            result["reason"]="clipped_solid_failed_mesh_quality"
            return result,None
        cut.apply_translation(origin)
        result["clipped_face_sources"]=[dict(mesh="component" if q<len(G) else "hull",face=int(q if q<len(G) else q-len(G))) for q in sources]
    if cut is None:state="touching" if len(pairs) else "outside"
    elif rest is None:state="coincident" if abs(H-P)<=tol and area>=min(hull.area,part.area)*(1-1e-9) else "inside"
    else:state="crossing"
    result.update(state=state,closure_verified=True)
    return result,cut


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("hull",type=Path);p.add_argument("component",type=Path)
    p.add_argument("--out",type=Path,required=True);p.add_argument("--role",default="component")
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    try:
        r,m=classify(load(a.hull),load(a.component),a.role)
    except (ImportError,OSError,RuntimeError,ValueError,AttributeError,IndexError) as exc:
        r=dict(state="blocked",closure_verified=False,metrics={},contact_area_m2=None,reason=str(exc),engineering_approved=False);m=None
    r.update(hull_sha256=fingerprint(a.hull),component_sha256=fingerprint(a.component),coordinates="ship_axes_metres")
    if m is not None:(a.out/"clipped.ply").write_bytes(m.export(file_type="ply"))
    (a.out/"relation.json").write_text(json.dumps(r,ensure_ascii=False,allow_nan=False,indent=2))
    return 4 if r["state"]=="blocked" else 0


if __name__=="__main__":raise SystemExit(main())
