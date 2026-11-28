#!/usr/bin/env python3
"""从工程 DWG/DXF 离线生成研究级几何及逐项证据。"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import time

import ezdxf
import numpy as np
import trimesh
from jsonschema import Draft202012Validator

from cad_input import AXES,classify,convert,extract
from core.drawing_parser import fingerprint,parse_drawing
from geometry import build_shell,exchange,read_exchange,hydro,quality,read_curves
from parts import extract_parts,discover_parts,extrude_registered
from design_shell import from_design


def save(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf8")


def geometry_input(directory, sources, out, oda, report):
    converted=out/"converted";converted.mkdir()
    records=[]
    for path in sources:
        h=fingerprint(path)
        record={"file":str(path.relative_to(directory)),"sha256":h}
        records.append(record)
        if path.suffix.lower() not in (".dwg",".dxf"):
            record["role"]="supporting_document";continue
        try:
            dx,adapter=convert(path,converted,oda)
            parsed=parse_drawing(dx)
            if parsed["document"]["status"]=="failed":raise ValueError(str(parsed["issues"]))
            record.update(parsed=parsed,cad=ezdxf.readfile(dx),conversion=adapter,dxf_sha256=fingerprint(dx),
                classification=classify(parsed),entity_count=len(parsed["entities"]),read_issues=parsed["issues"])
        except (ValueError,OSError,RuntimeError,TimeoutError,ezdxf.DXFError) as exc:
            record["error"]=str(exc)
        if fingerprint(path)!=h:raise ValueError("源文件读取期间发生变化")
    report["sources"]=[{k:v for k,v in r.items() if k not in ("parsed","cad")} for r in records]
    return records


def write_asset(out,role,filename,mesh,report):
    path=out/filename
    exchanged=exchange(mesh)
    if report.get("domain")=="registered_halfbreadth_patches":
        from coordinate_contract import contract
        extras=dict(mode=report.get("mode","strict"),engineering_approved=False,formal_calculation_authorized=False,
                    domain="open_unsigned_halfbreadth",coordinates=contract("local_hull",[0,0,0]))
        path.write_bytes(trimesh.exchange.gltf.export_glb(trimesh.Scene(exchanged),
                         tree_postprocessor=lambda data:data["asset"].update(extras=extras)))
    else:
        path.write_bytes(exchanged.export(file_type="glb"))
    readback=read_exchange(path)
    if len(mesh.faces)!=len(readback.faces) or readback.vertices.shape!=mesh.vertices.shape:
        raise ValueError("GLB 读回拓扑变化")
    error=float(np.max(np.linalg.norm(mesh.vertices-readback.vertices,axis=1)))
    if not np.array_equal(mesh.faces,readback.faces) or error>report["vertex_budget_m"]:
        raise ValueError("GLB 读回的顶点顺序、连接或精度超过预算")
    a,b=mesh.triangles,readback.triangles
    edges0,edges1=(np.roll(t,-1,axis=1)-t for t in (a,b))
    l0,l1=(np.linalg.norm(e,axis=2) for e in (edges0,edges1))
    cross0,cross1=(np.cross(e[:,0],e[:,1]) for e in (edges0,edges1))
    areas0,areas1=(np.linalg.norm(c,axis=1)*0.5 for c in (cross0,cross1))
    edge_error=np.abs(l1-l0);area_error=np.abs(areas0-areas1)
    if (np.any(np.einsum("ij,ij->i",cross0,cross1)<=0) or
            np.any(edge_error>1e-7+1e-3*l0) or np.any(area_error>1e-10+1e-3*areas0)):
        raise ValueError("GLB 往返存在法向翻转、退化或边长与面积超出研究预算")
    qa=quality(readback)
    if role in ("displacement","proxy") and not qa["closed_verified"]:
        raise ValueError("导出后的实体未通过闭合与自交复核")
    report["assets"][role]={"path":filename,"sha256":fingerprint(path),"faces":len(mesh.faces),
                             "roundtrip_vertex_error_m":error,"max_edge_error_m":float(edge_error.max()),
                             "max_area_error_m2":float(area_error.max()),"quality":qa}
    return readback


def run(directory,files,out,profile,oda,report):
    entries=geometry_input(directory,files,out,oda,report)
    selected=[]
    for item in entries:
        if "parsed" not in item:continue
        if profile and profile["source_sha256"]!=item["sha256"]:continue
        data=extract(item["parsed"],profile.get("table"))
        if data:selected.append((item,data))
    if len(selected)!=1:
        raise ValueError("需要可唯一判读的型值表、纵横轴与工程单位，或提供绑定图纸指纹的配置")
    item,(rows,table,declared,table_config)=selected[0]
    if profile:
        frame=profile["frame"];symmetric=profile["symmetric"]
        if frame["axes"]!=AXES or not frame["source"].strip():raise ValueError("船轴缺少依据")
    else:
        symmetric=declared["symmetric"];frame={"axes":AXES,"source":declared["notes"]}
    report.update(frame=frame,symmetric=symmetric,source_sha256=item["sha256"],dxf_sha256=item["dxf_sha256"])
    save(out/"table.json",table)
    save(out/"offsets.json",dict(rows=rows,source_sha256=item["sha256"],dxf_sha256=item["dxf_sha256"],
         paper_frame=table["frame"],engineering_mapping=table_config,ship_frame=frame))
    report["offsets"]={"total":len(rows),"printed":sum(r["raw"] is not None for r in rows),
                       "unknown":sum(r["raw"] is None for r in rows)}
    curves=read_curves(item["cad"],profile.get("curves",[]))
    save(out/"curves.json",curves)
    # Closing the tabulated domain represents a named research hypothesis;
    # actual ship endpoints and upper/lower limits require their own evidence.
    closure=profile.get("close_table_domain",True)
    mesh,faces,construction=build_shell(rows,curves,symmetric,closure,profile.get("subdivisions",4 if curves else 1))
    report.update(construction=construction,domain="已观测型值域",boundary_basis=profile.get("boundary_source") or
                  "研究假设：在型值表端站、最高与最低层作平面封盖，仅计算该型值域")
    if profile.get("design_shell"):
        write_asset(out,"offset_surface","offset-surface.glb",mesh,report)
        save(out/"offset-face-evidence.json",dict(source_sha256=item["sha256"],faces=faces))
        report["assets"]["offset_surface"]["evidence"]="offset-face-evidence.json"
        try:
            mesh,faces,refinement=from_design(directory,entries,profile["design_shell"],curves)
        except ValueError as exc:
            report["issues"].append({"design_shell_rejected":str(exc)})
        else:
            report.update(design_refinement=refinement,domain="原始设计排水实体及原图水线",
                          boundary_basis=profile["design_shell"]["source"])
    try:
        contact=write_asset(out,"contact","contact.glb",mesh,report)
    except ValueError as exc:
        if "design_refinement" not in report:raise
        report["issues"].append({"split_mesh_exchange_rejected":str(exc)})
        mesh,faces,refinement=from_design(directory,entries,profile["design_shell"],curves,keep_topology=True)
        report["design_refinement"]=refinement
        contact=write_asset(out,"contact","contact.glb",mesh,report)
    qa=quality(contact);report["mesh"]=qa
    save(out/"face-evidence.json",dict(source_sha256=item["sha256"],dxf_sha256=item["dxf_sha256"],
            asset_sha256=report["assets"]["contact"]["sha256"],frame=frame,faces=faces))
    report["assets"]["contact"]["evidence"]="face-evidence.json"
    holdouts=[c for c in curves if c["use"]=="holdout"]
    if holdouts:
        import igl
        measured=[]
        for curve in holdouts:
            points=np.array(curve["points_m"])
            sq,_,_=igl.point_mesh_squared_distance(points,np.array(contact.vertices),np.array(contact.faces,dtype=np.int64))
            distances=np.sqrt(np.maximum(0,sq))
            measured.append(dict(handle=curve["handle"],kind=curve["kind"],samples=len(points),
                    mae_m=float(distances.mean()),p95_m=float(np.percentile(distances,95)),
                    max_m=float(distances.max()),rmse_m=float(np.sqrt(np.mean(sq)))))
        save(out/"heldout.json",dict(method="整条留出曲线折线采样到已读回接触网格的单向最近距离",
                source_sha256=item["sha256"],asset_sha256=report["assets"]["contact"]["sha256"],curves=measured))
    parts,part_issues=extract_parts(entries,profile.get("components",discover_parts(entries)))
    parts.extend(extrude_registered(entries,profile.get("extrusions",[])))
    report["issues"].extend(part_issues)
    scene=trimesh.Scene();scene.add_geometry(exchange(mesh),node_name="hull")
    for index,(spec,part,handles,pqa) in enumerate(parts):
        key=f"{spec['role']}-{index}"
        verified=pqa["closed_verified"] if spec["role"] in ("tank","compartment") else None
        write_asset(out,key,key+".glb",part,report)
        report["components"].append({"id":key,"source":spec,"handles":handles,"quality":pqa,
                                    "enclosed_compartment_verified":verified})
        scene.add_geometry(exchange(part),node_name=key)
    display=out/"display.glb";display.write_bytes(scene.export(file_type="glb"))
    nodes=trimesh.load_scene(display,process=False).graph.nodes_geometry
    if set(nodes)!={"hull",*(v["id"] for v in report["components"])}:
        raise ValueError("构件树读回失败")
    report["assets"]["display"]={"path":display.name,"sha256":fingerprint(display),"nodes":sorted(nodes)}
    report["components_unknown"]=sorted({"deck","bulkhead","frame","longitudinal","tank","compartment"}-
                                         {s["role"] for s,_,_,_ in parts})
    if qa["closed_verified"]:
        solid=write_asset(out,"displacement","displacement.glb",mesh,report)
        proxy=solid.convex_hull
        write_asset(out,"proxy","proxy.glb",proxy,report)
        report["assets"]["proxy"]["method"]="排水 GLB 读回顶点的单凸包，适用于粗筛"
        report["assets"]["proxy"]["relative_volume_excess"]=float(proxy.volume/mesh.volume-1)
        drafts=profile.get("drafts_m",sorted({r["z_m"] for r in rows}))
        save(out/"hydrostatics.json",hydro(solid,drafts))
    else:
        report["issues"].append("几何域开放或闭合检查未通过，排水和刚体代理待补证")
    fem=out/"shell-candidate.inp"
    if not qa["topology"]["degenerate_faces"] and qa["self_intersection_pairs"]==0:
        with fem.open("w") as f:
            f.write("** Research geometry only, metres. No thickness, loads or materials assigned.\n*NODE\n")
            for i,(x,y,z) in enumerate(mesh.vertices,1):f.write(f"{i}, {x:.17g}, {y:.17g}, {z:.17g}\n")
            f.write("*ELEMENT, TYPE=S3, ELSET=OBSERVED_DOMAIN\n")
            for i,(a,b,c) in enumerate(mesh.faces+1,1):f.write(f"{i}, {a}, {b}, {c}\n")
        report["assets"]["fem_geometry"]={"path":fem.name,"sha256":fingerprint(fem),"solver_ready":False,
                                           "unknown":["thickness","material","joints","supports"]}
    report["status"]="bounded_model" if "displacement" in report["assets"] else "partial_surface"


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("input",type=Path)
    parser.add_argument("--out",type=Path,required=True);profiles=parser.add_mutually_exclusive_group();profiles.add_argument("--profile",type=Path)
    profiles.add_argument("--curve-profile",type=Path,help="绑定原图及坐标证据的局部开片；允许无型值表")
    parser.add_argument("--oda",help="本机 ODAFileConverter 可执行路径")
    args=parser.parse_args();source=args.input.resolve(strict=True);dest=args.out.resolve()
    directory=source if source.is_dir() else source.parent
    if dest.exists() or (source.is_dir() and dest.is_relative_to(source)):
        parser.error("输出应为输入目录之外的新目录")
    dest.parent.mkdir(exist_ok=True,parents=True)
    start=time.monotonic()
    report=dict(schema_version="1",status="needs_evidence",sources=[],issues=[],assets={},components=[],
                research_only=True,engineering_approved=False,vertex_budget_m=0.0001)
    with tempfile.TemporaryDirectory(dir=dest.parent) as tmp:
        path=Path(tmp)/"run";path.mkdir()
        try:
            profile=json.loads(args.profile.read_bytes()) if args.profile else {}
            if args.profile:
                schema=json.loads((Path(__file__).resolve().parents[1]/"schemas/profile.schema.json").read_bytes())
                Draft202012Validator(schema).validate(profile)
                report["profile_sha256"]=fingerprint(args.profile)
            files=sorted(source.rglob("*")) if source.is_dir() else [source]
            inputs=[p for p in files if p.is_file()]
            if args.curve_profile:
                from curve_patch import deliver
                content=args.curve_profile.read_bytes()
                definition=json.loads(content)
                report["profile_sha256"]=hashlib.sha256(content).hexdigest()
                entries=geometry_input(directory,inputs,path,args.oda,report)
                deliver(entries,definition,path,report,write_asset,save)
            else:
                run(directory,inputs,path,profile,args.oda,report)
        except Exception as exc:
            report["issues"].append({"stage_error":type(exc).__name__,"message":str(exc)[:2000]})
            report["status"]="needs_evidence"
            report["intermediate_assets_only"]=True
        report["seconds"]=time.monotonic()-start
        save(path/"report.json",report)
        if dest.exists():raise FileExistsError(dest)
        path.rename(dest)
    print(json.dumps({"status":report["status"],"report":str(dest/"report.json")},ensure_ascii=False))
    return 4 if report["status"]=="needs_evidence" else 0

if __name__=="__main__":
    raise SystemExit(main())
