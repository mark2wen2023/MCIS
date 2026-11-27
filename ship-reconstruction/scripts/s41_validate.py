"""读回结构实体，校验证据图；可选从原件重算全部几何关系。"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from jsonschema import Draft202012Validator
from s4lib.evidence_graph import digest
from s4_validate import validate as validate_solids


def load(path):
    def pairs(items):
        mapping=dict(items)
        if len(mapping)!=len(items):raise ValueError("JSON出现重复字段")
        return mapping
    return json.loads(path.read_bytes(),object_pairs_hook=pairs,
                      parse_constant=lambda v: (_ for _ in ()).throw(ValueError("非有限数值")))


def check(folder,source=None,oda=None,hull=None):
    graph=load(folder/"evidence-graph.json")
    schema=load(Path(__file__).resolve().parents[1]/"schemas/structure-evidence-4.1.schema.json")
    errors=[e.json_path+" "+e.message for e in Draft202012Validator(schema).iter_errors(graph)]
    if errors:return errors
    structures=load(folder/"structures.json")
    issues=validate_solids(folder/"structures.json")
    if graph["version"]!="4.1" or graph["engineering_approved"] is not False:issues.append("版本或研究权限无效")
    if digest(structures)!=graph["structures_content_sha256"]:issues.append("结构旁件指纹不一致")
    nodes={n["id"]:n for n in graph["nodes"]}
    if len(nodes)!=len(graph["nodes"]):issues.append("节点标识重复")
    annotations={(r["source_sha256"],r["instance"]):r for r in structures["observations"]}
    sources={s["source_sha256"] for s in structures["sources"]}
    observed={}
    for n in nodes.values():
        a=n["attributes"]
        if n["kind"]=="cad" and (a["source_sha256"] not in sources or not a["instance"]):
            issues.append("原图证据来源不匹配")
        if n["kind"]=="annotation":
            key=a["source_sha256"],a["instance"]
            observed[key]=a
            row=annotations.get(key)
            if not row or any(a[k]!=row[k] for k in ("layout","text","anchor_wcs")):issues.append("注记证据不匹配")
    if set(annotations)!=set(observed):issues.append("缺少原图注记")
    for e in graph["edges"]:
        if e["from"] not in nodes or e["to"] not in nodes or not e["evidence"] or any(nodes.get(i,{}).get("kind")!="cad" for i in e["evidence"]):issues.append("关系证据断裂")
        if e["basis"] not in ("direct","derived","candidate"):issues.append("关系类别无效")
    local={m["id"] for m in structures["local_models"]}
    registered={m["id"] for m in structures["components"] if m["geometry_status"]=="research_geometry_verified"}
    if {i["model_id"] for i in graph["installations"]}!=local|registered:issues.append("安装记录与模型不一致")
    for i in graph["installations"]:
        if i["node"] not in nodes:issues.append("安装节点缺失");continue
        if i["model_id"] in local:
            expected={k:v for k,v in i.items() if k not in ("node","model_id")}
            if (expected!=nodes[i["node"]]["attributes"] or i.get("status") not in ("local_only","partial_xz")
                    or i.get("ship_y_m") is not None or i.get("signed_thickness_direction") is not None):
                issues.append("局部模型安装权限越界")
    if source is not None and not issues:
        with tempfile.TemporaryDirectory() as tmp:
            new=Path(tmp)/"replay"
            args=[sys.executable,str(Path(__file__).with_name("s41.py")),str(source),"--out",str(new),"--mode","observe"]
            if oda:args+=["--oda",str(oda)]
            if hull:args+=["--hull-glb",str(hull)]
            p=subprocess.run(args,capture_output=True,text=True)
            if p.returncode not in (0,4) or not (new/"evidence-graph.json").is_file():
                issues.append("原件重算失败 "+p.stderr[-500:])
            else:
                again=load(new/"evidence-graph.json")
                # DWG converters may timestamp their intermediate DXF. The original
                # drawing hash is part of every CAD evidence node.
                for g in (again,graph):g.pop("structures_content_sha256")
                if digest(again)!=digest(graph):issues.append("与原图重算关系、数值或证据不一致")
    return sorted(set(issues))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("folder",type=Path)
    p.add_argument("--source",type=Path);p.add_argument("--oda",type=Path);p.add_argument("--hull-glb",type=Path)
    a=p.parse_args()
    try:issues=check(a.folder,a.source,a.oda,a.hull_glb)
    except (KeyError,TypeError,OSError,ValueError,RuntimeError,IndexError) as exc:issues=[str(exc)]
    print(json.dumps(dict(valid=not issues,issues=issues,source_replayed=bool(a.source) and not issues),ensure_ascii=False))
    raise SystemExit(4 if issues else 0)
