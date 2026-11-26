"""具有船轴配准和 CAD 面来源的构件及舱室。"""
import re
import numpy as np
import trimesh
from geometry import transform,quality

ROLES={"deck","bulkhead","frame","longitudinal","compartment","tank","plate"}


def extract_parts(drawings,specs):
    parts=[];issues=[]
    for spec in specs:
        if spec["role"] not in ROLES or not spec["source"].strip():
            raise ValueError("构件角色或配准依据缺失")
        found=[d for d in drawings if d["sha256"]==spec["source_sha256"] and d.get("cad") is not None]
        if len(found)!=1:
            raise ValueError("构件原图摘要不唯一")
        cad=found[0]["cad"]
        pts=[];tri=[];handles=[];unsupported=[]
        for e in cad.modelspace():
            if e.dxf.layer!=spec["layer"]:continue
            if e.dxftype()=="3DFACE":
                vs=list(e.wcs_vertices(close=False))
                polygons=[list(range(len(vs)))]
            elif e.dxftype()=="MESH":
                vs=list(e.vertices);polygons=list(e.faces)
            else:
                unsupported.append(e.dxf.handle);continue
            for poly in polygons:
                if len(poly) not in (3,4):
                    unsupported.append(e.dxf.handle);continue
                base=len(pts);points=transform(spec["matrix"],[vs[i] for i in poly])
                pts.extend(points)
                for ids in ([(0,1,2)] if len(poly)==3 else [(0,1,2),(0,2,3)]):
                    tri.append(tuple(base+i for i in ids));handles.append(e.dxf.handle)
        if unsupported:issues.append({"layer":spec["layer"],"unknown_geometry_handles":sorted(set(unsupported))})
        if not tri:continue
        vertices,inv=np.unique(pts,axis=0,return_inverse=True)
        faces=inv[np.array(tri)]
        mesh=trimesh.Trimesh(vertices,faces,process=False)
        parts.append((spec,mesh,handles,quality(mesh)))
    return parts,issues
