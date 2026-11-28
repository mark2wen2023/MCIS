"""统一图纸入口。船体、局部结构和设备各自保留准入结果。"""
import argparse
import traceback
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
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


def local_curve_fallback(upstream, files, src, stage, oda, mode, profile, expected):
    from curve_patch import deliver
    from reconstruct import geometry_input, write_asset
    folder = stage / (mode + "-surfaces")
    folder.mkdir()
    receipt = dict(assets={}, vertex_budget_m=1e-5, mode=mode, engineering_approved=False,
                   profile_sha256=expected)
    if expected is None or not profile.is_file():
        return {**upstream, "curve_reason":"缺少配准文件"}
    copy = folder / "registration.json"
    shutil.copyfile(profile, copy)
    if fingerprint(copy)!=expected:
        return {**upstream, "curve_reason":"配准文件在采集时改变"}
    config = json.loads(copy.read_bytes())
    hashes = {c["source_sha256"] for r in config["regions"] for c in r["curves"]}
    sources = [f for f in files if fingerprint(f) in hashes]
    entries = geometry_input(src,sources,folder,oda,receipt)
    deliver(entries,config,folder,receipt,write_asset,save)
    save(folder/"patch-report.json",receipt)
    if not profile.is_file() or fingerprint(profile)!=expected:
        raise ValueError("配准证据在计算中变化")
    if not receipt["assets"]:
        return {**upstream, "curve_regions":receipt["regions"]}
    return dict(status="partial", reason="仅交付有约束的开放半宽片体；整船仍阻塞",
                whole_hull=upstream, curve_regions=receipt["regions"],
                patches=[dict(file=folder.name+"/"+a["path"],sha256=a["sha256"])
                         for a in receipt["assets"].values()])


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


STAGES = ("hull", "structure", "equipment")


def snapshot(src):
    return {p.relative_to(src).as_posix(): fingerprint(p) for p in sorted(src.rglob("*"))
            if p.is_file() and p.suffix.lower() in (".dwg", ".dxf")}


def delivery_refs(report):
    refs = {}
    def add(stage, path, sha=None):
        if path in refs or Path(path).is_absolute() or ".." in Path(path).parts:
            raise ValueError("交付路径冲突或越界")
        refs[path] = (stage, sha)

    for stage in STAGES:
        r = report[stage]
        if r["status"] not in ("partial", "exported"):
            continue
        if stage == "hull":
            if "patches" in r:
                for a in r["patches"]:
                    add(stage, a["file"], a["sha256"])
            else:
                a = r["asset"]
                add(stage, a["file"], a["sha256"])
        elif stage == "structure":
            for item in r["partial_placements"]:
                a = item["asset"]
                add(stage, a["file"], a["sha256"])
            for item in r["registered_components"]:
                if item["geometry_status"] == "research_geometry_verified":
                    add(stage, "structure/" + item["asset"], item["asset_sha256"])
            ref = r.get("reference_readback", {})
            if "file" in ref:
                add(stage, ref["file"], ref["source_glb_sha256"])
        else:
            for a in r["assets"]:
                add(stage, a["file"], a["sha256"])
                add(stage, a["json"])
    return refs


def file_inventory(out, report):
    refs = delivery_refs(report)
    rows = []
    roots = {root: stage for stage in STAGES for root in report[stage].get("published_roots", [])}
    for path in sorted(out.rglob("*")):
        rel = path.relative_to(out)
        name = rel.as_posix()
        if path.is_symlink():
            raise ValueError("输出含符号链接：" + name)
        if name == "manifest.json" or path.is_dir():
            continue
        if not path.is_file():
            raise ValueError("输出含非普通文件：" + name)
        root = rel.parts[0]
        owner = roots.get(root, "run")
        digest = fingerprint(path)
        role = "intermediate_evidence"
        if "diagnostics" in rel.parts[:-1] or root == "invalidated" or path.suffix == ".log":
            role = "diagnostic"
            if root == "diagnostics" and len(rel.parts) > 1:
                owner = Path(rel.parts[1]).stem
        elif name in refs:
            owner, expected = refs.pop(name)
            if expected and digest != expected:
                raise ValueError("交付指纹不一致：" + name)
            role = "research_demo" if report["mode"] == "demo" else "strict_delivery"
        rows.append(dict(path=name, bytes=path.stat().st_size, sha256=digest, role=role,
                         stage=owner, mode=report["mode"]))
    if refs:
        raise ValueError("缺少交付文件：" + ", ".join(sorted(refs)))
    return rows


def verify(out):
    report = json.loads((out / "manifest.json").read_bytes())
    if report.get("sealed") is not True or report.get("inventory_version") != 1:
        raise ValueError("运行清单尚未封存或版本不支持")
    mode = report["mode"]
    if mode not in ("strict", "demo") or bool(report["assumptions"]) != (mode == "demo"):
        raise ValueError("模式与假设不符")
    if (report["engineering_approved"] is not False or report["formal_calculation_authorized"] is not False
            or any(report[s]["mode"] != mode or report[s]["formal_calculation_authorized"] is not False
                   or report[s]["status"] not in ("partial", "exported", "blocked", "failed") for s in STAGES)):
        raise ValueError("授权、模式或分项状态不符")
    quality = json.loads((out / (mode + "-quality.json")).read_bytes())
    if quality != {k: report[k] for k in (*STAGES, "mode", "assumptions", "status", "formal_calculation_authorized")}:
        raise ValueError("质量记录与清单不符")
    if report["files"] != file_inventory(out, report):
        raise ValueError("递归文件、角色、尺寸或指纹与清单不符")
    return report


def run(src,out,oda=None,reference=None,synthetic=False,*,mode=None,assumptions=(),recover_from=None,curve_profile=None):
    mode=mode or ("demo" if synthetic else "strict")
    if mode not in ("strict","demo") or (mode=="strict" and (synthetic or assumptions)):
        raise ValueError("严格模式不能接收演示假设")
    notes=list(assumptions)
    if synthetic:notes.append("synthetic_common_datum")
    if any(not isinstance(n,str) or not n.strip() for n in notes):raise ValueError("假设必须为非空文字")
    if mode=="demo" and not notes:
        raise ValueError("演示模式需要明确假设")
    intake_error = None
    try:
        inputs = snapshot(src)
        ref_hash = fingerprint(reference) if reference else None
    except OSError as exc:
        inputs, ref_hash, intake_error = {}, None, str(exc)
    identity = dict(drawings=inputs, reference_sha256=ref_hash,
                    synthetic_common_datum=synthetic, mode=mode, assumptions=notes)
    if curve_profile is not None:
        identity["curve_profile_sha256"] = fingerprint(curve_profile) if curve_profile.is_file() else None
    recovery = None
    if recover_from is not None:
        previous = recover_from / "manifest.json"
        old = json.loads(previous.read_bytes())
        if old.get("request") != identity:
            raise ValueError("恢复要求相同原件、参考资产、模式与假设")
        recovery = dict(previous_manifest_sha256=fingerprint(previous), strategy="full_replay")
    out.mkdir(parents=True,exist_ok=False)
    report=dict(mode=mode,assumptions=notes,engineering_approved=False,formal_calculation_authorized=False,
                request=identity, recovery=recovery, sealed=False, inventory_version=1)
    with TemporaryDirectory(prefix="s6-input-") as temporary:
        return _execute(src, out, oda, reference, synthetic, report, Path(temporary), intake_error, curve_profile)


def _execute(src, out, oda, reference, synthetic, report, frozen, intake_error, curve_profile):
    inputs = report["request"]["drawings"]
    mode, notes = report["mode"], report["assumptions"]
    stages = STAGES
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
        report["files"] = file_inventory(out, report)
        report["sealed"] = True
        checkpoint()
        return report
    checkpoint()
    try:
        if intake_error:
            raise ValueError(intake_error)
        for name, sha in inputs.items():
            target = frozen / "drawings" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src / name, target)
            if fingerprint(target) != sha:
                raise ValueError("原件在采集时改变")
        ref_copy = None
        if reference:
            ref_copy = frozen / "reference.glb"
            shutil.copyfile(reference, ref_copy)
            if fingerprint(ref_copy) != report["request"]["reference_sha256"]:
                raise ValueError("参考资产在采集时改变")
        before=sorted(inputs.values())
        if not before or len(set(before))!=len(before):raise ValueError("缺少图纸或输入重复")
    except (OSError,ValueError) as exc:
        for name in stages:report[name]=dict(status="blocked",reason=str(exc),category="input")
        return complete()
    def inputs_match():
        try:
            return (snapshot(src) == inputs and
                    (reference is None or fingerprint(reference) == report["request"]["reference_sha256"]))
        except OSError:
            return False

    changed = False
    frozen_src = frozen / "drawings"
    files=[frozen_src/name for name in inputs]
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
            if name=="hull":
                result=hull_stage(frozen_src,stage,oda,before,mode)
                if curve_profile is not None and result["status"]=="blocked":
                    result=local_curve_fallback(result, files, frozen_src, stage, oda, mode,
                                                curve_profile, report["request"]["curve_profile_sha256"])
            elif name=="structure":result=structure_stage(frozen_src,stage,oda,before,ref_copy,mode,notes)
            else:
                hull=report["hull"]
                registered=hull if hull.get("evidence",{}).get("absolute_frame") else None
                result=extract_equipment(files,stage,oda,synthetic,registered,hull_dir=out)
                if result["assets"]:result["status"]="partial" if result["rejected"] else "exported"

            for item in list(stage.iterdir()):
                dest=out/item.name
                if dest.exists():raise ValueError("分项输出文件重名")
                item.rename(dest);moved.append(dest)
            result["published_roots"]=sorted(v.name for v in moved)
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
        changed = not inputs_match() or changed
        report[name]=result
        if name=="structure" and "reference_readback" in result:report["reference_readback"]=result["reference_readback"]
        checkpoint()
    if changed or not inputs_match():
        folder=out/"invalidated";folder.mkdir()
        for dest in published:dest.rename(folder/dest.name)
        report.pop("reference_readback",None)
        save(folder/"stage-outcomes.json",{name:report[name] for name in stages})
        for name in stages:report[name]=dict(status="blocked",reason="输入身份改变，产物已隔离",category="input")
    return complete()

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("drawings",type=Path,nargs="?");p.add_argument("--out",type=Path,required=True)
    p.add_argument("--oda",type=Path);p.add_argument("--local-reference",type=Path)
    p.add_argument("--synthetic-common-datum",action="store_true",help="仅供已声明相同原点的合成输入")
    p.add_argument("--recover-from",type=Path,help="绑定旧清单，在新目录从冻结输入完整重跑")
    p.add_argument("--verify", action="store_true",help="校验 --out 中已封存的运行；无需指定图纸")
    p.add_argument("--mode",choices=["strict","demo"])
    p.add_argument("--assumption",action="append",default=[])
    p.add_argument("--curve-profile",type=Path,help="整船阻塞时，按原图指纹及配准证据交付独立开片")
    a=p.parse_args()
    if a.verify:
        result=verify(a.out)
        print(json.dumps(dict(verified=True, mode=result["mode"], files=len(result["files"]))))
        raise SystemExit(0)
    if a.drawings is None:p.error("运行需要图纸目录")
    result=run(a.drawings,a.out,a.oda,a.local_reference,a.synthetic_common_datum,mode=a.mode,assumptions=a.assumption,recover_from=a.recover_from,curve_profile=a.curve_profile)
    print(json.dumps({k:result[k] for k in ("mode","status")}))
    raise SystemExit(1 if any(result[k]["status"]=="failed" for k in ("hull","structure","equipment")) else 4 if result["status"]=="blocked" else 0)
