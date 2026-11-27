"""复验结构清单、源图引用和实际 PLY；完整测量仍须回到原图。"""
import argparse
import json
from pathlib import Path
from jsonschema import Draft202012Validator
import numpy as np
import trimesh
from geometry import quality
from core.drawing_parser import fingerprint
from s4lib.panels import solid,METRE

SCHEMA=Path(__file__).resolve().parents[1]/"schemas/structures.schema.json"


def validate(path):
    data=json.loads(path.read_bytes(),parse_constant=lambda s: (_ for _ in ()).throw(ValueError("非有限数值")))
    problems=[f"{e.json_path}: {e.message}" for e in Draft202012Validator(json.loads(SCHEMA.read_bytes())).iter_errors(data)]
    if problems:return problems
    sources={v["source_sha256"] for v in data["sources"]}
    obs={(r["source_sha256"],r["instance"]):r for r in data["observations"]}
    if len(obs)!=len(data["observations"]):problems.append("重复的源图观察")
    if any(s not in sources for s,h in obs):problems.append("未登记的源图")
    ids=set()
    for r in [*data["components"],*data["local_models"]]:
        if r.get("geometry_status")=="blocked":
            if r.get("asset"):problems.append("受阻构件携带了成品")
            continue
        asset=r["asset"]
        if asset in ids or Path(asset).name!=asset or Path(asset).suffix!=".ply":
            problems.append("成品路径重复或未经支持");continue
        ids.add(asset)
        if "coordinate_frame" in r:
            o=obs.get((r["source_sha256"],r["instance"]))
            if not o or o["modeling_status"]!="local_research_candidate" or r["thickness_raw"] not in o["dimensions"] or not any(v["handles"]==r["leader"] and r["contour"] in v.get("local_cell_candidates",[]) for v in o["leaders"]):
                problems.append("缺少板件对应的引线、边界或厚度")
            if r["thickness_raw"]["unit"] is None and r["thickness_unit_basis"]=="printed":
                problems.append("未标注单位被升级为明示单位")
        target=path.parent/asset
        if not target.is_file() or target.is_symlink():problems.append("成品缺失或为链接");continue
        if fingerprint(target)!=r.get("asset_sha256"):
            problems.append("实体文件摘要不匹配")
        mesh=trimesh.load_mesh(target,process=False)
        if "coordinate_frame" in r:
            dim=r["thickness_raw"];unit=dim["unit"]
            if unit is None:
                witnesses=[obs.get((r["source_sha256"],h)) for h in r["unit_evidence_handles"]]
                units={d["unit"] for w in witnesses if w for d in w["dimensions"] if d["kind"]=="thickness" and d["unit"]}
                unit=next(iter(units)) if len(units)==1 and all(witnesses) else None
            if not unit or not np.isclose(r["modeled_thickness_m"],dim["value"]*METRE[unit],rtol=1e-12,atol=0):
                problems.append("厚度缺乏原数值与单位证据");continue
            origin,expected=solid(r["contour"]["contour_wcs"],r["modeled_thickness_m"],r["scale"]["m_per_drawing_unit"])
            if not np.array_equal(origin,r["paper_origin_wcs"]) or not np.array_equal(expected.vertices,mesh.vertices) or not np.array_equal(expected.faces,mesh.faces):
                problems.append("成品不符合原图轮廓、位置或挤出尺寸")
        elif not np.allclose(mesh.bounds,r["bounds_m"],rtol=0,atol=1e-10):
            problems.append("成品船轴位置与记录不符")
        actual=quality(mesh)
        if not actual["closed_verified"] or not r["quality"]["closed_verified"] or not np.isclose(actual["signed_volume_m3"],r["quality"]["signed_volume_m3"],rtol=1e-9,atol=1e-15):
            problems.append("实体回读质量与记录不符")
    return problems


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("input",type=Path);a=parser.parse_args()
    try:issues=validate(a.input)
    except (ValueError,TypeError,KeyError,OSError,RuntimeError) as exc:issues=[str(exc)]
    print(json.dumps(dict(valid=not issues,issues=issues),ensure_ascii=False))
    raise SystemExit(4 if issues else 0)
