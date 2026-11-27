"""具有船轴配准和 CAD 面来源的构件及舱室。"""
from cad_input import declarations
import numpy as np
import trimesh
from geometry import transform,quality

ROLES={"deck","bulkhead","frame","longitudinal","compartment","tank","plate"}


def discover_parts(drawings):
    """A signed ship frame, model-space units and an explicit role-named layer are all required."""
    specs=[]
    for item in drawings:
        if "cad" not in item:continue
        declared=declarations(item["parsed"]["entities"])
        if not declared["frame"]:continue
        cad=item["cad"]
        factor={4:0.001,5:0.01,6:1.0}.get(cad.header.get("$INSUNITS",0))
        if factor is None:continue
        for layer in sorted({e.dxf.layer for e in cad.modelspace() if e.dxftype() in ("MESH","3DFACE")}):
            role=layer.split(".",1)[0].lower()
            if role not in ROLES:continue
            specs.append(dict(role=role,layer=layer,source_sha256=item["sha256"],
                matrix=np.diag([factor,factor,factor,1.]).tolist(),
                source="三维模型空间图层 "+layer+"；$INSUNITS；船轴注记 "+",".join(declared["notes"])))
    return specs


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
        if np.linalg.det(np.asarray(spec["matrix"])[:3,:3])<0:faces=faces[:,::-1]
        mesh=trimesh.Trimesh(vertices,faces,process=False)
        parts.append((spec,mesh,handles,quality(mesh)))
    return parts,issues


def extrude_registered(drawings, specs):
    """逐一读取已配准的封闭轮廓及其标注，沿登记的正法线挤出。"""
    import re
    from ezdxf.path import make_path
    from shapely import Polygon, constrained_delaunay_triangles

    parts = []
    for spec in specs:
        candidates = [d for d in drawings if d["sha256"] == spec["source_sha256"] and "cad" in d]
        if len(candidates) != 1:
            raise ValueError("挤出构件图纸摘要缺失或不唯一")
        doc = candidates[0]["cad"]
        curve = doc.entitydb.get(spec["outline_handle"])
        note = doc.entitydb.get(spec["measure_handle"])
        if curve is None or curve.dxftype() != "LWPOLYLINE" or not curve.closed:
            raise ValueError("挤出需要已定位的封闭 CAD 多段线")
        if note is None or note.dxftype() not in ("TEXT", "MTEXT"):
            raise ValueError("构件缺少原图厚度或高度注记")
        label = note.plain_text() if note.dxftype() == "MTEXT" else note.dxf.text
        match = re.fullmatch(r"\s*(厚度|高度|THICKNESS|HEIGHT)\s*[:=：]\s*([0-9]+(?:\.[0-9]+)?)\s*(mm|m|毫米|米)\s*", label, re.I)
        if match:
            dimension, value, unit = match.groups()
            is_height = dimension.lower() in ("height", "高度")
            length = float(value) * (0.001 if unit.lower() in ("mm","毫米") else 1.)
        elif spec.get("natural_identity"):
            from s4lib.notes import parse
            observation=parse(label)
            dimensions=[v for v in (observation or {}).get("dimensions",[]) if v["kind"] in ("height","thickness")]
            if len(dimensions)!=1 or not dimensions[0]["unit"]:
                raise ValueError("构件尺寸标注的类型、数值或单位无法唯一确定")
            value=dimensions[0]
            length=value["value"]*{"mm":.001,"cm":.01,"m":1.,"in":.0254}[value["unit"]]
            is_height=value["kind"]=="height"
        else:
            raise ValueError("构件尺寸需要唯一数值、单位及明确的厚度或高度标注")
        if is_height != (spec["role"] in ("tank", "compartment")):
            raise ValueError("标注类型与构件用途不匹配")
        if length <= 0:raise ValueError("挤出尺寸必须为正")
        matrix = spec["matrix"]
        scale = np.linalg.norm(np.asarray(matrix,dtype=float)[:3,:3],ord=2)
        points = transform(matrix,list(make_path(curve).flattening(0.0001/scale)))
        if np.linalg.norm(points[-1]-points[0])>1e-9:raise ValueError("轮廓未闭合")
        points = points[:-1]
        normal = np.asarray(spec["positive_normal"], dtype=float)
        if abs(np.linalg.norm(normal)-1)>1e-9:raise ValueError("挤出方向须为船轴单位向量")
        local = points - points[0]
        if np.max(np.abs(local @ normal))>1e-7:raise ValueError("轮廓与挤出方向不垂直")
        u=local[np.argmax(np.linalg.norm(local,axis=1))]
        u=u/np.linalg.norm(u)
        v=np.cross(normal,u)
        xy=np.column_stack((local@u,local@v))
        polygon=Polygon(xy)
        if not polygon.is_valid or polygon.area<=0:raise ValueError("轮廓自交或面积为零")
        indices={tuple(point):i for i,point in enumerate(xy)}
        tris=[]
        for triangle in constrained_delaunay_triangles(polygon).geoms:
            tris.append([indices[tuple(k)] for k in list(triangle.exterior.coords)[:3]])
        solid=trimesh.creation.extrude_triangulation(xy,np.asarray(tris),length)
        x,y,z=solid.vertices.T
        solid.vertices=points[0]+x[:,None]*u+y[:,None]*v+z[:,None]*normal
        qa=quality(solid)
        if not qa["closed_verified"]:raise ValueError("挤出构件未通过闭合和自交检查")
        parts.append(({**spec,"measured_text":label,"length_m":length},solid,
                      [curve.dxf.handle]*len(solid.faces),qa))
    return parts
