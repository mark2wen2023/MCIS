"""调用 S5 合成设备注记解析。证据与原始 DWG、转换件及 CAD 句柄分别绑定。"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
import trimesh
from cad_input import convert as cad_convert,fingerprint
from coordinate_contract import contract,read_meta,TO_GLTF
from . import drawing,standard_export
from .exchange import SHIP_TO_GLTF
from .runtime import Runtime
from .structures import attach


def read_articulation(path,config):
    if fingerprint(path)!=config["model_sha256"] or read_meta(path).get("coordinates")!=config["coordinates"]:
        raise ValueError("模型与关节旁件不匹配")
    if config["coordinates"]!=contract("vessel",[0,0,0]) or config["axes"]!="x_forward_y_up_z_starboard":
        raise ValueError("关节坐标声明无效")
    scene=trimesh.load_scene(path,process=False)
    Runtime(scene,config)
    return scene


def extract(files,out,oda,synthetic,hull=None):
    if not np.array_equal(TO_GLTF,SHIP_TO_GLTF[:3,:3]):raise ValueError("交换轴矩阵不一致")
    assets=[];rejected=[];sources=[];count=0
    with TemporaryDirectory() as tmp:
        for i,source in enumerate(files):
            cache=Path(tmp)/str(i);cache.mkdir()
            sha=fingerprint(source);dxf,adapter=cad_convert(source,cache,oda)
            dest=cache/"raw";cfg=drawing.run(dxf,dest)
            sources.append(dict(original=sha,parsed_dxf=fingerprint(dxf),conversion=adapter,recognized=len(cfg["joints"]),rejected=len(cfg["rejected"])))
            rejected.extend(dict(original=sha,**r) for r in cfg["rejected"])
            count+=len(cfg["joints"])
            if not cfg["joints"]:continue
            if not synthetic:
                rejected.extend(dict(original=sha,handle=j["evidence"]["annotation"],reason="synthetic axis convention only") for j in cfg["joints"])
                continue
            scene=trimesh.load_scene(dest/"equipment.glb",process=False)
            scene,c=standard_export.convert(scene,cfg)
            for j in c["joints"]:j["evidence"]["original_source_sha256"]=sha
            if hull is not None:
                # Registration is explicitly declared by the synthetic case. Restore
                # the centred hull's origin in the equipment's exchange basis once.
                asset=hull["asset"];m=asset["coordinates"];path=out/asset["file"]
                if fingerprint(path)!=asset["sha256"] or read_meta(path)["coordinates"]!=m or m["reference_frame"]!="vessel":
                    raise ValueError("船体交换坐标或凭据无效")
                transform=np.eye(4);transform[:3,3]=TO_GLTF@np.array(m["origin_in_reference_m"])
                scene,c=attach(scene,c,[dict(id="hull",asset=path,sha256=asset["sha256"],registration="synthetic_common_datum",
                                            frame=c["axes"],transform=transform.tolist(),evidence={"source_sha256":sha})])
            meta=contract("vessel",[0,0,0])
            target=out/("equipment-"+sha[:16]+".glb")
            target.write_bytes(trimesh.exchange.gltf.export_glb(scene,tree_postprocessor=lambda j:j["asset"].update(extras={"coordinates":meta})))
            c.update(coordinates=meta,model_sha256=fingerprint(target),model_file=target.name,scope="synthetic_common_datum")
            scene2=read_articulation(target,c)
            for node in scene.graph.nodes_geometry:
                a,key=scene.graph[node];b,key2=scene2.graph[node]
                first=scene.geometry[key];second=scene2.geometry[key2]
                if not np.array_equal(first.faces,second.faces):raise ValueError("设备读回拓扑不一致")
                x=trimesh.transform_points(first.vertices,a);y=trimesh.transform_points(second.vertices,b)
                if np.max(np.linalg.norm(x-y,axis=1))>1e-5:
                    target.unlink()
                    raise ValueError("设备读回位置超限")
            if read_meta(target)["coordinates"]!=meta:raise ValueError("设备坐标丢失")
            sidecar=target.with_suffix(".json")
            sidecar.write_text(json.dumps(c,allow_nan=False,indent=2))
            assets.append(dict(file=target.name,sha256=c["model_sha256"],json=sidecar.name,nodes=len(c["joints"])))
    return dict(status="exported_synthetic" if assets else "blocked",sources=sources,recognized=count,rejected=rejected,
                reason=None if assets else "no supported approved placement from these drawings",assets=assets)
