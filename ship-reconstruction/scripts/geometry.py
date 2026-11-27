"""曲线配准、半宽曲面、水密性检查以及船轴/交换轴变换。"""
import math
from collections import defaultdict
import numpy as np
import trimesh
from ezdxf.path import make_path
from core.mesh_validation import validate_mesh


def transform(matrix, points):
    a=np.asarray(matrix,dtype=object)
    if a.shape!=(4,4) or any(type(v) not in (int,float) or not math.isfinite(v) for v in a.flat):
        raise ValueError("需要四行四列有限数值变换矩阵")
    a=a.astype(float)
    if np.linalg.matrix_rank(a[:3,:3])!=3 or not np.array_equal(a[-1],[0,0,0,1]):
        raise ValueError("仅支持仿射坐标变换")
    return np.asarray(points,dtype=float) @ a[:3,:3].T + a[:3,3]


def read_curves(doc, specs):
    records=[]
    seen=set()
    for spec in specs:
        h=spec["handle"]
        if h in seen or h not in doc.entitydb or not spec["source"].strip():
            raise ValueError("曲线来源缺失或训练与留出重复")
        seen.add(h)
        kind=spec["kind"]
        if kind not in ("waterline","buttock","section") or spec["use"] not in ("constraint","holdout"):
            raise ValueError("曲线用途或类型无效")
        path=make_path(doc.entitydb[h])
        scale=np.linalg.norm(np.asarray(spec["matrix"],dtype=float)[:3,:3],ord=2)
        if not math.isfinite(scale) or scale<=0:
            raise ValueError("曲线坐标变换尺度无效")
        raw=list(path.flattening(0.0001/scale,segments=12))
        points=transform(spec["matrix"],raw)
        if spec.get("fold_halfbreadth") is True:
            points[:,1]=abs(points[:,1])
        fixed={"waterline":2,"buttock":1,"section":0}[kind]
        if len(points)<2 or np.ptp(points[:,fixed])>0.001 or not np.isfinite(points).all():
            raise ValueError("提取曲线的配准与所标注基准面不一致："+h)
        records.append({**spec,"points_m":points.tolist(),"flattening_m":0.0001})
    return records


def intersect(values, axis, plane):
    """折线上与平面的独立交点。多值分支留待识别。"""
    a,b=values[:-1],values[1:]
    delta=b[:,axis]-a[:,axis]
    crossed=(np.abs(delta)>1e-12)&(np.minimum(a[:,axis],b[:,axis])-1e-10<=plane)&(plane<=np.maximum(a[:,axis],b[:,axis])+1e-10)
    a,b,delta=a[crossed],b[crossed],delta[crossed]
    if not len(delta):
        return []
    return (a+(b-a)*np.clip((plane-a[:,axis])/delta,0,1)[:,None])[:,1].tolist()


def build_shell(rows, curves, symmetric, closure, subdivisions=1):
    original=sorted({r["x_m"] for r in rows})
    zs=sorted({r["z_m"] for r in rows})
    xs=sorted({*original,*(float(x) for a,b in zip(original,original[1:]) for x in np.linspace(a,b,subdivisions+1))})
    obs={(r["x_m"],r["z_m"]):r for r in rows}
    guides=[(r,np.array(r["points_m"])) for r in curves if r["use"]=="constraint" and r["kind"]!="buttock"]
    nodes={};conflicts=[];supplement=[]
    for x in xs:
        i=max(0,min(len(original)-2,int(np.searchsorted(original,x)-1)))
        for z in zs:
            raw=obs.get((x,z)); value=raw["breadth_m"] if raw else None
            source=[raw["handle"]] if value is not None else []
            candidates=[]
            for r,p in guides:
                fixed,axis,requested=(2,0,z) if r["kind"]=="waterline" else (0,2,x)
                if abs(p[0,fixed]-requested)<1e-6:
                    candidates.extend((v,r["handle"]) for v in intersect(p,axis,x if axis==0 else z))
            if candidates:
                vals=[v for v,_ in candidates]
                if max(vals)-min(vals)>0.001 or (value is not None and max(abs(v-value) for v in vals)>0.001):
                    conflicts.append(dict(x_m=x,z_m=z,raw_m=value,candidates=candidates))
                    # Drawing text survives as the reference hypothesis. Conflicting
                    # guide values do not fill blanks or modify a printed number.
                elif value is None:
                    value,h=candidates[0];source=[h];supplement.append(dict(x_m=x,z_m=z,breadth_m=value,handles=source))
            if value is None and raw is None:
                a,b=original[i:i+2]
                l,r=obs[a,z],obs[b,z]
                if l["breadth_m"] is not None and r["breadth_m"] is not None:
                    value=l["breadth_m"]+(r["breadth_m"]-l["breadth_m"])*(x-a)/(b-a)
                    source=[l["handle"],r["handle"]]
            if value is not None and value>=0:
                nodes[x,z]=(float(value),source)
    vertices=[];indices={};faces=[];evidence=[];degenerate=0
    def face(corners,role):
        nonlocal degenerate
        ids=[];handles=set()
        for x,z,side in corners:
            width,src=nodes[x,z];key=(x,side*width,z)
            if key not in indices:
                indices[key]=len(vertices);vertices.append(key)
            ids.append(indices[key]);handles.update(src)
        for a,b,c in ((0,1,2),(0,2,3)):
            tri=(ids[a],ids[b],ids[c])
            if len(set(tri))<3:
                degenerate+=1;continue
            faces.append(tri);evidence.append(dict(role=role,handles=sorted(handles)))
    complete=len(nodes)==len(xs)*len(zs)
    sides=(1,-1) if symmetric else (1,)
    for a,b in zip(xs,xs[1:]):
        for l,u in zip(zs,zs[1:]):
            if not all(k in nodes for k in ((a,l),(a,u),(b,l),(b,u))):
                continue
            for s in sides:
                ring=[(a,l,s),(a,u,s),(b,u,s),(b,l,s)]
                face(ring if s==1 else ring[::-1],"side")
    if closure and symmetric and complete:
        for a,b in zip(xs,xs[1:]):
            for z,top in ((zs[-1],True),(zs[0],False)):
                ring=[(a,z,-1),(b,z,-1),(b,z,1),(a,z,1)]
                face(ring if top else ring[::-1],"table_boundary_cap")
        for l,u in zip(zs,zs[1:]):
            for x,bow in ((xs[-1],True),(xs[0],False)):
                ring=[(x,l,-1),(x,l,1),(x,u,1),(x,u,-1)]
                face(ring if bow else ring[::-1],"table_boundary_cap")
    if not faces:
        raise ValueError("没有四角有来源的可建模单元")
    mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    return mesh,evidence,dict(complete_grid=complete,coincident_degenerate_candidates_removed=degenerate,
        conflicts=conflicts,derived_values=supplement,grid_shape=[len(xs),len(zs)])


def quality(mesh):
    check=validate_mesh(mesh.vertices.tolist(),mesh.faces.tolist())
    topology={k:len(v) if isinstance(v,list) else v for k,v in check.items()}
    intersections=None; manifold=None; verification_error=None
    try:
        import igl
        from igl.copyleft import cgal
        manifold=bool(igl.is_vertex_manifold(np.ascontiguousarray(mesh.faces,dtype=np.int64)).all())
        hits=cgal.remesh_self_intersections(np.ascontiguousarray(mesh.vertices),np.ascontiguousarray(mesh.faces,dtype=np.int64),detect_only=True)[2]
        intersections=len(hits)
    except (ImportError,OSError,AttributeError,RuntimeError) as exc:
        verification_error=f"{type(exc).__name__}: {exc}"
    angles=np.rad2deg(mesh.face_angles)
    longest=mesh.edges_unique_length.max()
    return dict(verification_status="environment_blocked" if verification_error else "executed", verification_error=verification_error, vertex_manifold=manifold,min_angle_deg=float(angles.min()),max_edge_m=float(longest),topology=topology,self_intersection_pairs=intersections,components=int(mesh.body_count),
                signed_volume_m3=float(mesh.volume),area_m2=float(mesh.area),
                closed_verified=bool(check["edge_closed_candidate"] and mesh.body_count==1 and
                    mesh.is_watertight and mesh.is_winding_consistent and mesh.is_volume and manifold and intersections==0))


def exchange(mesh):
    m=mesh.copy()
    m.apply_transform([[1,0,0,0],[0,0,1,0],[0,-1,0,0],[0,0,0,1]])
    return m


def read_exchange(path):
    scene=trimesh.load_scene(path,process=False)
    mesh=scene.to_geometry()
    mesh.apply_transform([[1,0,0,0],[0,0,-1,0],[0,1,0,0],[0,0,0,1]])
    return mesh


def hydro(mesh,drafts):
    """按水平面切闭合网格，独立导出浸没体积和水线面积。"""
    results=[]
    for draft in drafts:
        if type(draft) not in (int,float) or not math.isfinite(draft):
            raise ValueError("吃水应为有限的船轴米制坐标")
        if draft<=mesh.bounds[0,2]:
            results.append(dict(draft_m=draft,volume_m3=0.,waterplane_m2=0.,center_of_buoyancy_m=None));continue
        if draft>=mesh.bounds[1,2]:
            results.append(dict(draft_m=draft,volume_m3=float(mesh.volume),waterplane_m2=None,
                                center_of_buoyancy_m=mesh.center_mass.tolist()));continue
        # Signed tetrahedral volume against a point in the cutting plane; the
        # omitted horizontal lid has zero tetrahedral volume and first moment.
        cut=mesh.slice_plane([0,0,draft],[0,0,-1],cap=False)
        origin=np.array([0.,0.,draft])
        tri=cut.triangles-origin
        volumes=np.einsum("ij,ij->i",tri[:,0],np.cross(tri[:,1],tri[:,2]))/6.
        v=math.fsum(volumes);center=origin+(volumes[:,None]*tri.sum(axis=1)/4.).sum(axis=0)/v
        aw=-0.5*np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])[:,2].sum()
        results.append(dict(draft_m=draft,volume_m3=v,waterplane_m2=float(aw),center_of_buoyancy_m=center.tolist()))
    return results
