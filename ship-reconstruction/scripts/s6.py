"""统一图纸入口。船体、局部结构和设备各自保留准入结果。"""
import argparse
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

def run(src,out,oda=None,reference=None,synthetic=False):
    out.mkdir(parents=True,exist_ok=False)
    files=sorted(p for p in src.iterdir() if p.suffix.lower() in (".dwg",".dxf") and p.is_file())
    def hashes():return sorted(fingerprint(p) for p in files)
    before=hashes()
    if not before:raise ValueError("没有图纸")
    if len(before)!=len(set(before)):raise ValueError("重复输入图纸")
    g=process(src,out,oda);save(out/"geometry.json",g)
    audit=check(g)
    if sorted(r["source_sha256"] for r in g["inventory"])!=before:raise ValueError("图纸清单不匹配")
    report=dict(engineering_approved=False,sources=before,
        json_frames={"geometry.json":"S2.1: separate drawing WCS and metre ship candidates",
                     "structure/structures.json":"mixed: labelled WCS, local_plate_axes_metres and registered ship",
                     "structure/evidence-graph.json":"mixed: WCS, frame-relative dx and BL height",
                     "manifest.json":"per-asset contract, no common installation origin"},
        equipment=dict(status="blocked",reason="no verified equipment or joint handoff for input drawings",exported=0,denominator=None))
    try:
        mesh,qa=reconstruct(g,upstream_check=lambda _:audit)
        meta=contract("vessel" if qa["absolute_frame"] else "local_hull",mesh.bounds.mean(axis=0))
        report["hull"]=dict(status="exported",asset=export_mesh(out/"hull.glb",mesh,meta),evidence=qa)
    except ValueError as exc:report["hull"]=dict(status="blocked",reason=str(exc),admission=g["modeling_admission"],issues=audit["issues"])
    try:
        from igl.copyleft import cgal
        if not callable(getattr(cgal,"remesh_self_intersections",None)):
            raise ImportError("CGAL 自交检测不可用")
    except (ImportError,OSError) as exc:
        report["structure"]=dict(status="environment_blocked",reason=str(exc),partial_placements=[])
        report["equipment"]=extract_equipment(files,out,oda,False)
        if hashes()!=before:raise ValueError("原图已改变")
        save(out/"manifest.json",report)
        return report
    folder=out/"structure"
    args=[sys.executable,str(Path(__file__).with_name("s41.py")),str(src),"--out",str(folder),"--mode","observe"]
    if oda:args+=["--oda",str(oda)]
    p=subprocess.run(args,capture_output=True,text=True);(out/"structures.log").write_text(p.stdout+p.stderr)
    if p.returncode not in (0,4):raise ValueError("结构程序失败，见 structures.log")
    errors=validate_structure(folder)
    if errors:raise ValueError(str(errors))
    s=json.loads((folder/"structures.json").read_bytes());graph=json.loads((folder/"evidence-graph.json").read_bytes())
    if sorted(d["source_sha256"] for d in s["sources"])!=before or hashes()!=before:raise ValueError("结构原件不一致")
    positions={i["model_id"]:i for i in graph["installations"]}
    assets=[];local={}
    for m in s["local_models"]:
        placement=positions[m["id"]]
        if placement["status"]!="partial_xz":continue
        mesh=local_mesh(m,placement,folder);local[m["id"]]=mesh
        asset=export_mesh(out/(m["id"]+".glb"),mesh,contract("frame_section_display",[0,0,0]))
        assets.append(dict(model_id=m["id"],asset=asset,evidence=placement,source=m["source_sha256"],
                           source_ply_sha256=m["asset_sha256"],thickness_basis=m["thickness_unit_basis"],
                           transverse_installation_m=None,physical_thickness_direction=None,weld=None))
    report["structure"]=dict(observations=len(s["observations"]),local_solids=len(s["local_models"]),partial_placements=assets,
                              registered_components=s["components"],unknown_installs=[m["id"] for m in s["local_models"] if m["id"] not in local])
    if reference:
        verified=compare_reference(reference,local,before)
        # Preserve the original nodes and their display-only transverse datum.
        path=out/"verified-local-section.glb"
        path.write_bytes(reference.read_bytes())
        if fingerprint(path)!=verified["source_glb_sha256"]:raise ValueError("局部参考资产已改变")
        verified.update(file=path.name,ship_y_m=None,thickness_side=None,weld=None)
        report["reference_readback"]=verified
    hull=report["hull"]
    registered=hull if hull.get("evidence",{}).get("absolute_frame") else None
    report["equipment"]=extract_equipment(files,out,oda,synthetic,registered)
    if hashes()!=before:raise ValueError("设备读取期间原图发生改变")
    save(out/"manifest.json",report)
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("drawings",type=Path);p.add_argument("--out",type=Path,required=True)
    p.add_argument("--oda",type=Path);p.add_argument("--local-reference",type=Path)
    p.add_argument("--synthetic-common-datum",action="store_true",help="仅供已声明相同原点的合成输入")
    a=p.parse_args();run(a.drawings,a.out,a.oda,a.local_reference,a.synthetic_common_datum)
