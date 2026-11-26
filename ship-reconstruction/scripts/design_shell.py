"""从可追溯的设计排水实体生成分层网格，并在训练水线处施加有界的半宽修订。"""
from collections import defaultdict
from pathlib import Path
import math

import numpy as np
import trimesh
from geometry import transform, quality, intersect


def split_levels(mesh, levels):
    """共享边只取一次交点；每个新三角面保留原设计三角面的索引。"""
    vertices=mesh.vertices.tolist()
    faces=mesh.faces.tolist()
    source=list(range(len(faces)))
    for height in sorted(set(levels)):
        # Resolve near-coincident plane events within a documented two-micrometre budget.
        for vertex in vertices:
            if abs(vertex[2]-height)<=2e-6:vertex[2]=height
        cuts={};new_faces=[];new_source=[]
        def cut(i,j):
            key=tuple(sorted((i,j)))
            if key not in cuts:
                a,b=(np.array(vertices[k]) for k in key)
                fraction=(height-a[2])/(b[2]-a[2])
                v=a+(b-a)*fraction;v[2]=height
                cuts[key]=len(vertices);vertices.append(v.tolist())
            return cuts[key]
        for tri,origin in zip(faces,source):
            zz=[vertices[k][2] for k in tri]
            if min(zz)>=height or max(zz)<=height:
                new_faces.append(tri);new_source.append(origin);continue
            # Clip to two half-planes. Strict crossings share an edge vertex;
            # incident vertices already on the plane are used in both polygons.
            for sign in (1,-1):
                polygon=[]
                for i,j in zip(tri,[*tri[1:],tri[0]]):
                    a,b=vertices[i][2]-height,vertices[j][2]-height
                    if a*sign>=0:polygon.append(i)
                    if a*b<0:polygon.append(cut(i,j))
                for i in range(1,len(polygon)-1):
                    new_faces.append([polygon[0],polygon[i],polygon[i+1]]);new_source.append(origin)
        faces,source=new_faces,new_source
    return np.array(vertices),np.asarray(faces),source


def native_field(mesh, guides, budget):
    """只在有双侧高度支撑的区间插值水线残差，保持原三角形连接。"""
    levels=sorted(set([*guides,float(mesh.bounds[0,2]),float(mesh.bounds[1,2])]))
    source_slices={}
    for z in guides:
        segments=trimesh.intersections.mesh_plane(mesh,[0,0,1],[0,0,z])
        source_slices[z]=segments[np.min(segments[:,:,1],axis=1)>=-1e-8]
    cache={}
    def sample(x,z):
        if z not in guides:return (0.,[])
        if (x,z) in cache:return cache[x,z]
        matches=[(y,h) for h,line in guides[z] for y in intersect(line,0,x)]
        s=source_slices[z]
        spans=(s[:,1,0]-s[:,0,0])
        ok=(np.abs(spans)>1e-12)&(np.min(s[:,:,0],axis=1)<=x)&(np.max(s[:,:,0],axis=1)>=x)
        native=s[ok,0,1]+(x-s[ok,0,0])/spans[ok]*(s[ok,1,1]-s[ok,0,1])
        result=None
        if len(native) and matches:
            values=[v for v,_ in matches];d=float(np.mean(values)-max(native))
            if max(values)-min(values)<=0.001 and abs(d)<=budget:
                result=(d,sorted({h for _,h in matches}))
        cache[x,z]=result
        return result
    proposed=mesh.vertices.copy();sources=defaultdict(list);rejected=[];used=[]
    for k,(x,y,z) in enumerate(mesh.vertices):
        if abs(y)<1e-8 or z<=levels[0] or z>=levels[-1]:continue
        i=np.searchsorted(levels,z);lo,hi=levels[i-1:i+1]
        a,b=sample(x,lo),sample(x,hi)
        if a is None or b is None:continue
        t=(z-lo)/(hi-lo);offset=(1-t)*a[0]+t*b[0]
        if not offset or abs(y)+offset<=0:continue
        proposed[k,1]=np.copysign(abs(y)+offset,y)
        sources[k]=sorted(set(a[1]+b[1]));used.append(abs(offset))
    return proposed,sources,rejected,used


def from_design(directory,entries,spec,curves,keep_topology=False):
    if not spec['source'].strip() or not 0<spec["max_correction_m"] or not math.isfinite(spec["max_correction_m"]):
        raise ValueError("设计实体配准和修订预算缺失")
    candidates=[r for r in entries if r["sha256"]==spec["source_sha256"] and Path(r["file"]).suffix.lower()==".stl"]
    if len(candidates)!=1:raise ValueError("设计排水实体源文件缺失或不唯一")
    path=directory/candidates[0]["file"]
    raw=trimesh.load_mesh(path,process=False)
    verts,inverse=np.unique(transform(spec["matrix"],raw.vertices),axis=0,return_inverse=True)
    f=inverse[raw.faces]
    if np.linalg.det(np.asarray(spec["matrix"])[:3,:3])<0:f=f[:,::-1]
    source=trimesh.Trimesh(verts,f,process=False)
    if not quality(source)["closed_verified"]:
        raise ValueError("原设计排水实体须为经独立自交、方向和流形检查的单一闭合体")
    guides=defaultdict(list)
    for c in curves:
        if c["kind"]=="waterline" and c["use"]=="constraint":
            p=np.array(c["points_m"]);guides[float(p[0,2])].append((c["handle"],p))
    if not guides:raise ValueError("设计实体修订需要原图约束水线；留出水线只用于验证")
    if keep_topology:
        raw_split=source
        faces=source.faces
        origin=range(len(faces))
        vertices,sources,rejected,used=native_field(source,guides,spec["max_correction_m"])
    else:
        vertices,faces,origin=split_levels(source,guides)
        raw_split=trimesh.Trimesh(vertices.copy(),faces,process=False)
        sources=defaultdict(list);rejected=[];used=[]
        for height,lines in guides.items():
            for k in np.flatnonzero(vertices[:,2]==height):
                x,y,_=vertices[k]
                if y==0:continue
                widths=[]
                for handle,line in lines:
                    widths.extend((v,handle) for v in intersect(line,0,x))
                if not widths:continue
                if max(v for v,h in widths)-min(v for v,h in widths)>0.001:
                    rejected.append([int(k),"multiple_curve_branches"]);continue
                target,h=widths[0];offset=target-abs(y)
                if abs(offset)>spec["max_correction_m"]:
                    rejected.append([int(k),"over_budget",float(offset)]);continue
                vertices[k,1]=math.copysign(target,y)
                sources[k]=sorted({h for _,h in widths});used.append(float(abs(offset)))
    if not used:
        raise ValueError("没有在登记坐标和预算内与设计壳相交的训练水线")
    attempts=[]
    delta=vertices-raw_split.vertices
    limited=set()
    for fraction in (1.,0.5,0.25,0.125,0.0625,0.03125):
        # Back out corrections at vertices of folded faces, then repeat because
        # adjacent faces share vertices. Unaffected waterline edits survive.
        trial=delta*fraction
        limited=set()
        for attempt in range(12):
            mesh=trimesh.Trimesh(raw_split.vertices+trial,faces,process=False)
            bad=np.einsum("ij,ij->i",raw_split.face_normals,mesh.face_normals)<=0
            if not bad.any():break
            remove=np.unique(faces[bad])
            limited.update(int(k) for k in remove if np.any(trial[k]))
            trial[remove]=0
        qa=quality(mesh)
        flipped=int(np.count_nonzero(bad))
        attempts.append(dict(fraction=fraction,closed=qa["closed_verified"],flipped=flipped,
                withdrawn_vertices=len(limited),degenerate=qa["topology"]["degenerate_faces"],
                self_intersections=qa["self_intersection_pairs"]))
        if qa["closed_verified"] and not flipped and np.any(trial):break
    else:
        raise ValueError("原图水线产生折叠或退化，拒绝替换设计实体："+str(attempts))
    for k in limited:sources.pop(k,None)
    evidence=[{"role":"design_shell","source_sha256":spec["source_sha256"],"source_triangle":int(o),
               "handles":sorted({h for k in tri for h in sources[k]})} for o,tri in zip(origin,faces)]
    return mesh,evidence,{"source":spec,"input_faces":len(source.faces),"refined_faces":len(mesh.faces),
        "split_only_volume_change_m3":float(raw_split.volume-source.volume),"changed_vertices":int(np.any(trial!=0,axis=1).sum()),
        "constrained_vertices":len(used)-len(limited),"withdrawn_vertices":sorted(limited),"max_abs_change_m":float(np.abs(trial).max()),"fraction":fraction,"attempts":attempts,"plane_snap_limit_m":0. if keep_topology else 2e-6,"rejected":rejected,
        "method":"原设计拓扑，按同站两相邻训练水线插值半宽修正，最底与最顶边界固定" if keep_topology else "按原图训练水线分割设计三角面，唯一且在预算内的交点约束半宽；其余点延用设计实体",
        "scope":"以原始设计排水实体为辅助输入的研究情景","holdout_used_in_fit":False}
