"""S6 的船轴、构件与关节使用米制右手系，交换文件明确记录轴与原点。"""
import hashlib
import json
import struct
import numpy as np
import trimesh
from geometry import quality

TO_GLTF=np.array([[1.,0,0],[0,0,1],[0,-1,0]])
FRAMES={"vessel","local_hull","frame_section_display","component","joint"}

def vector(values):
    a=np.array(values,dtype=object)
    if a.shape!=(3,) or any(type(v) not in (float,int,np.float64,np.int64) for v in a):
        raise ValueError("需要三个有限实数")
    a=a.astype(float)
    if not np.isfinite(a).all():raise ValueError("坐标非有限")
    return a

def contract(frame,origin):
    if frame not in FRAMES:raise ValueError("未知坐标系")
    return dict(version="S6.1",reference_frame=frame,storage="gltf_y_up",unit="m",
                origin_in_reference_m=vector(origin).tolist(),reference_to_storage_rotation=TO_GLTF.tolist())

def convert(points,source,target,meta,direction=False):
    if meta!=contract(meta["reference_frame"],meta["origin_in_reference_m"]):raise ValueError("坐标契约不一致")
    p=np.stack([vector(v) for v in points]);o=np.zeros(3) if direction else vector(meta["origin_in_reference_m"])
    reference=meta["reference_frame"]
    if (source,target)==(reference,"gltf_y_up"):return (p-o)@TO_GLTF.T
    if (source,target)==("gltf_y_up",reference):return p@TO_GLTF+o
    raise ValueError("重复转换或坐标系不匹配")

def joint_in_exchange(pivot,axis,parent,meta):
    a=vector(axis)
    if abs(np.linalg.norm(a)-1)>1e-9:raise ValueError("关节轴必须具有明确的单位方向")
    return dict(parent_frame=parent,storage="gltf_y_up",
                pivot_m=convert([pivot],parent,"gltf_y_up",meta)[0].tolist(),
                axis=convert([a],parent,"gltf_y_up",meta,direction=True)[0].tolist())

def read_meta(path):
    b=path.read_bytes()
    if len(b)<20 or struct.unpack_from("<4sII",b)!=(b"glTF",2,len(b)):raise ValueError("GLB头部无效")
    n,typ=struct.unpack_from("<I4s",b,12)
    if typ!=b"JSON" or n>len(b)-20:raise ValueError("GLB描述截断")
    return json.loads(b[20:20+n])["asset"].get("extras",{})

def export_mesh(path,mesh,meta,*,mode="strict"):
    out=mesh.copy()
    ref=meta["reference_frame"]
    out.vertices=convert(mesh.vertices,ref,"gltf_y_up",meta)
    scene=trimesh.Scene(out)
    path.write_bytes(trimesh.exchange.gltf.export_glb(scene,tree_postprocessor=lambda j:j["asset"].update(extras={"coordinates":meta,"mode":mode,"formal_calculation_authorized":False})))
    if read_meta(path).get("coordinates")!=meta:raise ValueError("GLB坐标旁件不一致")
    actual=trimesh.load_scene(path,process=False).to_geometry()
    actual.vertices=convert(actual.vertices,"gltf_y_up",ref,meta)
    if not np.array_equal(actual.faces,mesh.faces):raise ValueError("GLB三角拓扑改变")
    error=float(np.max(np.linalg.norm(actual.vertices-mesh.vertices,axis=1)))
    qa=quality(actual)
    if error>1e-5 or not qa["closed_verified"]:
        path.unlink()
        raise ValueError("交换成品超出研究精度或闭合预算")
    return dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                coordinates=meta,vertex_max_error_m=error,quality=qa)
