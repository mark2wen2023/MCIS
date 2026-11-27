"""统一图纸入口。船体、局部结构和设备各自保留准入结果。"""
import argparse
import traceback
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from cad_input import fingerprint
from coordinate_contract import contract,export_mesh,read_meta,TO_GLTF
from s6_equipment.intake import extract as extract_equipment
from s2 import process,check
from s3_s21 import reconstruct
from s41_validate import check as validate_structure


def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False,default=lambda v:v.tolist()))


def local_mesh(model,installation,folder):
    mesh=trimesh.load_mesh(folder/model["asset"],process=False)
    src=(np.array(model["contour"]["contour_wcs"])-model["paper_origin_wcs"])*model["scale"]["m_per_drawing_unit"]
    target=np.array(installation["vertices_dx_z_m"])
    design=np.column_stack((src,np.ones(len(src))))
    M,_,rank,_=np.linalg.lstsq(design,target,rcond=None)
    if rank!=3 or np.max(abs(design@M-target))>1e-7 or not np.allclose(M[:2].T@M[:2],np.eye(2),atol=1e-7,rtol=0):
        raise ValueError("局部轮廓配准缺少刚性唯一解")
    normal=-np.sign(np.linalg.det(M[:2]))
    transform=np.array([[M[0,0],M[1,0],0,M[2,0]],[0,0,normal,-normal*model["modeled_thickness_m"]/2],
                        [M[0,1],M[1,1],0,M[2,1]],[0,0,0,1]])
    mesh.apply_transform(transform)
    return mesh

def compare_reference(path,local,source_hashes):
    extras=read_meta(path)
    if (extras.get("research_only") is not True or extras.get("engineering_approved") is not False
        or "global_ship_y_m" not in extras or extras["global_ship_y_m"] is not None
        or extras.get("source_sha256") not in source_hashes):raise ValueError("局部参考资产缺少原图或未知位置说明")
    scene=trimesh.load_scene(path,process=False);matched=[]
    if len(scene.graph.nodes_geometry)!=len(local):raise ValueError("局部参考节点数量不一致")
    for node in scene.graph.nodes_geometry:
        matrix,key=scene.graph[node];m=scene.geometry[key].copy();m.apply_transform(matrix)
        candidates=[]
        for ident,other in local.items():
            a=m.vertices;b=other.vertices@TO_GLTF.T
            if len(m.faces)!=len(other.faces) or not m.is_volume:continue
            gap=max(cKDTree(a).query(b)[0].max(),cKDTree(b).query(a)[0].max())
            if gap<1e-5:candidates.append((ident,float(gap)))
        if len(candidates)!=1 or candidates[0][0] in [r["model_id"] for r in matched]:raise ValueError("局部参考无法唯一关联")
        matched.append(dict(node=node,model_id=candidates[0][0],vertices_max_gap_m=candidates[0][1]))
    return dict(source_glb_sha256=fingerprint(path),storage="gltf_y_up",reference_frame="frame_section_display",nodes=matched)

def hull_stage(src,out,oda,before,mode):
    g=process(src,out,oda)
    save(out/"geometry.json",g)
    if sorted(r["source_sha256"] for r in g["inventory"])!=before:
        raise ValueError("船体输入指纹与清单不一致")
    audit=check(g)
    try:
        mesh,qa=reconstruct(g,upstream_check=lambda _:audit)
    except ValueError as exc:
        return dict(status="blocked",reason=str(exc),admission=g["modeling_admission"],issues=audit["issues"])
    frame="vessel" if qa["absolute_frame"] else "local_hull"
    asset=export_mesh(out/(mode+"-hull.glb"),mesh,contract(frame,mesh.bounds.mean(axis=0)),mode=mode)
    return dict(status="exported",reason=None,asset=asset,evidence=qa)


def structure_stage(src,out,oda,before,reference,mode,assumptions):
    from igl.copyleft import cgal
    if not callable(getattr(cgal,"remesh_self_intersections",None)):
        raise ImportError("CGAL 自交检测不可用")
    folder=out/"structure"
    args=[sys.executable,str(Path(__file__).with_name("s41.py")),str(src),"--out",str(folder),"--mode","observe"]
    if oda:args+=["--oda",str(oda)]
    p=subprocess.run(args,capture_output=True,text=True);(out/"structures.log").write_text(p.stdout+p.stderr)
    if p.returncode not in (0,4):raise ValueError("结构程序失败，见 structures.log")
    errors=validate_structure(folder)
    if errors:raise ValueError(str(errors))
    s=json.loads((folder/"structures.json").read_bytes());graph=json.loads((folder/"evidence-graph.json").read_bytes())
    if sorted(d["source_sha256"] for d in s["sources"])!=before:raise ValueError("结构原件不一致")
    positions={i["model_id"]:i for i in graph["installations"]}
    assets=[];local={};withheld=[]
    for m in s["local_models"]:
        placement=positions[m["id"]]
        if placement["status"]!="partial_xz":continue
        if m["thickness_unit_basis"]!="printed" and (mode=="strict" or m["thickness_unit_basis"] not in assumptions):
            withheld.append(dict(model_id=m["id"],reason=m["thickness_unit_basis"],projection=placement))
            continue
        mesh=local_mesh(m,placement,folder);local[m["id"]]=mesh
        asset=export_mesh(out/(mode+"-"+m["id"]+".glb"),mesh,contract("frame_section_display",[0,0,0]),mode=mode)
        assets.append(dict(model_id=m["id"],asset=asset,evidence=placement,source=m["source_sha256"],
                           source_ply_sha256=m["asset_sha256"],thickness_basis=m["thickness_unit_basis"],
                           transverse_installation_m=None,physical_thickness_direction=None,weld=None))
    result=dict(observations=len(s["observations"]),local_solids=len(s["local_models"]),partial_placements=assets,
                              registered_components=s["components"],unknown_installs=[m["id"] for m in s["local_models"] if m["id"] not in local])
    registered=[r for r in s["components"] if r.get("geometry_status")=="research_geometry_verified"]
    result["withheld"]=withheld
    unresolved=len(registered)<len(s["components"]) or bool(result["unknown_installs"])
    result["status"]="partial" if assets or (registered and unresolved) else ("exported" if registered else "blocked")
    result["reason"]="only local placement supported" if assets else (None if registered else "insufficient verified geometry or installation evidence")
    if reference and local:
        try:
            verified=compare_reference(reference,local,before)
        except (ValueError,KeyError,OSError,TypeError) as exc:
            result["reference_readback"]=dict(status="blocked",reason=str(exc))
            return result
        # Preserve the original nodes and their display-only transverse datum.
        path=out/(mode+"-verified-local-section.glb")
        path.write_bytes(reference.read_bytes())
        if fingerprint(path)!=verified["source_glb_sha256"]:raise ValueError("局部参考资产已改变")
        verified.update(file=path.name,ship_y_m=None,thickness_side=None,weld=None)
        result["reference_readback"]=verified
    return result


def snapshot(src):
    return {p.name:fingerprint(p) for p in sorted(src.iterdir()) if p.is_file() and p.suffix.lower() in (".dwg",".dxf")}


def run(src,out,oda=None,reference=None,synthetic=False,*,mode=None,assumptions=()):
    mode=mode or ("demo" if synthetic else "strict")
    if mode not in ("strict","demo") or (mode=="strict" and (synthetic or assumptions)):
        raise ValueError("严格模式不能接收演示假设")
    notes=list(assumptions)
    if synthetic:notes.append("synthetic_common_datum")
    if any(not isinstance(n,str) or not n.strip() for n in notes):raise ValueError("假设必须为非空文字")
    if mode=="demo" and not notes:
        raise ValueError("演示模式需要明确假设")
    out.mkdir(parents=True,exist_ok=False)
    report=dict(mode=mode,assumptions=notes,engineering_approved=False,formal_calculation_authorized=False)
    stages=("hull","structure","equipment")
    for name in stages:report[name]=dict(status="pending",reason=None)
    def checkpoint():
        tmp=out/"manifest.tmp"
        save(tmp,report)
        tmp.replace(out/"manifest.json")
    def complete():
        states=[report[k]["status"] for k in stages]
        report["status"]=("exported" if all(v=="exported" for v in states) else
                          "partial" if any(v in ("exported","partial") for v in states) else
                          "failed" if "failed" in states else "blocked")
        for name in stages:
            report[name].update(mode=mode,formal_calculation_authorized=False)
        save(out/(mode+"-quality.json"),{k:report[k] for k in (*stages,"mode","assumptions","status","formal_calculation_authorized")})
        checkpoint()
        return report
    try:
        inputs=snapshot(src)
        before=sorted(inputs.values())
        if not before or len(set(before))!=len(before):raise ValueError("缺少图纸或输入重复")
    except (OSError,ValueError) as exc:
        for name in stages:report[name]=dict(status="blocked",reason=str(exc),category="input")
        return complete()
    files=[src/name for name in inputs]
    report.update(sources=before,json_frames={"geometry.json":"S2.1 per-field WCS or ship candidate",
            "structure/structures.json":"S4 local axes or verified projections; intermediate research evidence",
            "structure/evidence-graph.json":"WCS and partial XZ",
            "manifest.json":"per-asset references"})
    checkpoint()
    published=[]
    for name in stages:
        stage=out/(".running-"+name);stage.mkdir()
        moved=[]
        report[name]=dict(status="running",reason=None)
        checkpoint()
        try:
            if name=="hull":result=hull_stage(src,stage,oda,before,mode)
            elif name=="structure":result=structure_stage(src,stage,oda,before,reference,mode,notes)
            else:
                hull=report["hull"]
                registered=hull if hull.get("evidence",{}).get("absolute_frame") else None
                result=extract_equipment(files,stage,oda,synthetic,registered,hull_dir=out)
                if result["assets"]:result["status"]="partial" if result["rejected"] else "exported"
            if snapshot(src)!=inputs:raise ValueError("输入图纸发生变化")
            for item in list(stage.iterdir()):
                dest=out/item.name
                if dest.exists():raise ValueError("分项输出文件重名")
                item.rename(dest);moved.append(dest)
            result["published_files"]=[v.name for v in moved if v.is_file()]
            if name=="structure":result["intermediate_source_evidence"]="structure/"
            stage.rmdir()
            published.extend(moved)
        except Exception as exc:
            # Preserve diagnostic files without exposing a failed asset as a delivery.
            stage.mkdir(exist_ok=True)
            for dest in reversed(moved):dest.rename(stage/dest.name)
            quarantine=out/"diagnostics";quarantine.mkdir(exist_ok=True)
            stage.rename(quarantine/name)
            (quarantine/(name+".log")).write_text(traceback.format_exc())
            dep=isinstance(exc,(ImportError,ModuleNotFoundError))
            result=dict(status="blocked" if dep else "failed",category="environment" if dep else "execution",
                        reason=f"{type(exc).__name__}: {exc}",diagnostics=f"diagnostics/{name}.log")
        result["mode"]=mode
        result["formal_calculation_authorized"]=False
        report[name]=result
        if name=="structure" and "reference_readback" in result:report["reference_readback"]=result["reference_readback"]
        checkpoint()
    try:stable=snapshot(src)==inputs
    except OSError:stable=False
    if not stable:
        folder=out/"invalidated";folder.mkdir()
        for dest in published:dest.rename(folder/dest.name)
        report.pop("reference_readback",None)
        for name in stages:report[name]=dict(status="blocked",reason="原图身份改变，产物已隔离",category="input")
    return complete()

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("drawings",type=Path);p.add_argument("--out",type=Path,required=True)
    p.add_argument("--oda",type=Path);p.add_argument("--local-reference",type=Path)
    p.add_argument("--synthetic-common-datum",action="store_true",help="仅供已声明相同原点的合成输入")
    p.add_argument("--mode",choices=["strict","demo"])
    p.add_argument("--assumption",action="append",default=[])
    a=p.parse_args()
    result=run(a.drawings,a.out,a.oda,a.local_reference,a.synthetic_common_datum,mode=a.mode,assumptions=a.assumption)
    print(json.dumps({k:result[k] for k in ("mode","status")}))
    raise SystemExit(1 if any(result[k]["status"]=="failed" for k in ("hull","structure","equipment")) else 4 if result["status"]=="blocked" else 0)
