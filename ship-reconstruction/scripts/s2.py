#!/usr/bin/env python3
"""由离线 CAD 直接生成供后续曲面重建读取的几何观测。"""
import argparse
from collections import Counter,defaultdict
import json
from pathlib import Path
import re
import tempfile
import time

import ezdxf
import numpy as np

from cad_input import convert
from core.drawing_parser import fingerprint
from s2lib import alignment,cad,curves,tables

TOOLS={"drawing_inventory":"inventory","offset_table_extract":"tables","hull_curve_extract":"curves",
       "drawing_alignment":"alignment","geometry_data_validate":"validation"}


def one_value(items,kind):
    values={v["value_m"] for v in items if v["kind"]==kind}
    return next(iter(values)) if len(values)==1 else None


def table_unit(doc,table,dims):
    # Header insertion units alone cannot establish printed offset units.
    for c in table["cells"]:
        c["value_basis"]="original_text" if c["value"] is not None else "unknown"
    half=[c for c in table["cells"] if re.search(r"半宽|halfbreadth",cad.norm(c["group"] or "")) and c["value"] is not None]
    if table["unit_status"]!="unknown" or not half:return
    beam=one_value(dims,"beam")
    if beam is None or beam<=0:return
    peak=max(c["value"] for c in half)
    possible=[u for u in ("mm","m") if abs(2*tables.metre(peak,u)-beam)<=max(.001,abs(beam)*1e-5)]
    # The comparison applies to half-breadths. Height columns without their
    # own declaration retain a separately marked same-table hypothesis.
    if len(possible)!=1:return
    unit=possible[0]
    table["unit_candidate"]={"unit":unit,"basis":"half_breadth_max_vs_declared_beam",
        "handles":[c["instances"] for c in half if c["value"]==peak],"dimensions":[d for d in dims if d["kind"]=="beam"]}
    for c in table["cells"]:
        if c in half or re.search(r"半宽|halfbreadth",cad.norm(c["group"] or "")):
            c.update(unit=unit,unit_basis="cross_checked_half_breadth",value_m=tables.metre(c["value"],unit),
                     level_m=tables.axis_value(c["field_label"],"field",unit,None))
        else:c["unit_candidate"]=unit


def sheet_regions(data,record):
    # Closed borders can be four independent lines. Use coincident endpoints
    # and right angles; never infer an authoritative boundary from text boxes.
    by=defaultdict(list)
    for s in data["segments"]:
        a,b=(tuple(round(v,4) for v in s[k][:2]) for k in ("a","b"))
        if a!=b:
            by[s["layout"],a].append((b,s["instance"]))
            by[s["layout"],b].append((a,s["instance"]))
    rectangles=defaultdict(list);seen=set()
    for (layout,a),neighbors in by.items():
        if len(neighbors)>16:continue
        for i,(b,h) in enumerate(neighbors):
            u=np.subtract(b,a);l=np.linalg.norm(u)
            for c,k in neighbors[i+1:]:
                v=np.subtract(c,a);w=np.linalg.norm(v)
                if abs(u@v)>1e-6*l*w:continue
                expected=np.array(b)+v
                for d,h2 in by[layout,b]:
                    if max(abs(d-expected))>.001:continue
                    other=next((h3 for pt,h3 in by[layout,c] if pt==d),None)
                    signature=tuple(sorted([h,k,h2,other or ""]))
                    if not other or signature in seen:continue
                    seen.add(signature)
                    rectangles[layout].append((np.array(a),u,v,l,w,signature))
    for item in record["regions"]:
        t=item["anchor"];loc=np.array(t["p"][:2]);found=[]
        for a,u,v,l,w,e in rectangles[item["layout"]]:
            if min(l,w)<18*t["height"]:continue
            p=loc-a
            if 0<=p@u<=l*l and 0<=p@v<=w*w:
                found.append((l*w,e,[a.tolist(),(a+u).tolist(),(a+u+v).tolist(),(a+v).tolist()]))
        if found:
            _,e,poly=min(found,key=lambda x:x[0]);item.update(border_handles=e,bounds_wcs=poly,bounds_status="enclosing_border_candidate")
        else:item["bounds_status"]="anchor_only"


def links(docs):
    result=[]
    for i,a in enumerate(docs):
        for b in docs[i+1:]:
            if a["source_sha256"]==b["source_sha256"]:continue
            shared=[dict(kind=x["kind"],value_m=x["value_m"],handles=[x["handles"],y["handles"]])
                    for x in a.get("dimensions",[]) for y in b.get("dimensions",[]) if x["kind"]==y["kind"] and abs(x["value_m"]-y["value_m"])<1e-7]
            references=[(x,y) for x in a.get("document_ids",[]) for y in b.get("document_ids",[]) if x["id"]==y["id"] and "ref" in (x["role"],y["role"]) and x["role"]!=y["role"]]
            if shared or references:result.append(dict(sources=[a["source_sha256"],b["source_sha256"]],shared_dimensions=shared,explicit_refs=references,status="referenced" if references else "candidate"))
    return result


def check(g):
    problems=[];counts=Counter()
    inventory={r["source_sha256"]:r for r in g["inventory"]}
    for part in ("tables","curves","alignment"):
        if any(r["source_sha256"] not in inventory for r in g[part]):problems.append("unlinked_source")
    for t in g["tables"]:
        keys=set()
        for c in t["cells"]:
            counts[c["status"]]+=1
            if c["status"] in ("blank_unknown","conflict","merged_unknown","non_numeric","boundary_ambiguous") and (c["value"] is not None or c["value_m"] is not None):problems.append("unapproved_value")
            if not c["row_header"]["instance"] or not c["field_header"]["instance"]:problems.append("missing_cell_locator")
            if c["value"] is not None and (not c["instances"] or any(float(cad.norm(s))!=c["value"] for s in c["raw_texts"])):problems.append("unsupported_numeric_value")
            key=(c["row_header"]["instance"],c["field_header"]["instance"])
            if key in keys:problems.append("duplicate_cell_address")
            keys.add(key)
    for doc in g["alignment"]:
        for f in doc["frames"]:
            if f["status"]=="verified" and (not f.get("leave_one_out_errors_m") or max(f["leave_one_out_errors_m"])>1e-5):problems.append("unverified_registration")
    return dict(valid=not problems,issues=sorted(set(problems)),cell_status_counts=dict(counts),engineering_approved=False,
                eligible_for_automatic_full_loft=False)


def process(path,dest,oda):
    sources=[path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in (".dwg",".dxf"))
    if not sources:raise ValueError("未找到 DWG/DXF")
    g=dict(schema_version="2.0",inventory=[],tables=[],curves=[],alignment=[],issues=[])
    with tempfile.TemporaryDirectory() as tmp:
        for source in sources:
            sha=fingerprint(source)
            try:
                dx,adapter=convert(source,Path(tmp),oda);doc=ezdxf.readfile(dx);data=cad.read(doc)
                inv=cad.inventory(data)
                dims=alignment.dimensions(data["texts"]);spacing=one_value(dims,"station_spacing")
                found=tables.extract(data,inv,spacing)
                for t in found:table_unit(doc,t,dims)
                if found and "offset_table" not in inv["classes"]:inv["classes"].append("offset_table")
                for t in found:
                    c=t["cells"][0]
                    inv["regions"].append(dict(kind="offset_table",layout=t["layout"],basis="grid_and_headers",anchor=c["field_header"],bounds_status="verified_cells"))
                # Borders require located source text. A native table uses a cell address.
                regions=inv["regions"];inv["regions"]=[r for r in regions if "height" in r["anchor"]]
                sheet_regions(data,inv);inv["regions"]=regions
                refs=[]
                for txt in data["texts"]:
                    m=re.fullmatch(r"(drawing(?:id|no)|图号|ref|参见图|引用图)[:=：]([\w.-]+)",txt["n"])
                    if m:refs.append(dict(role="ref" if m[1] in ("ref","参见图","引用图") else "id",id=m[2],handle=txt["instance"]))
                inv.update(source_sha256=sha,file=source.name,dxf_sha256=fingerprint(dx),conversion=adapter,dimensions=dims,
                    document_ids=refs,insertion_units_code=doc.units)
                excluded={h for t in found for c in t["cells"] for h in [*c["instances"],c["row_header"]["instance"],c["field_header"]["instance"]]}
                frames=alignment.datum_controls(data)
                derived,axes=alignment.measured_frames(data,spacing,excluded) if "lines" in inv["classes"] or found else ([],[])
                frames.extend(derived)
                cr=curves.extract(data,inv,found,frames)
                if fingerprint(source)!=sha:raise ValueError("输入在读取过程中改变")
                g["inventory"].append(inv)
                g["tables"].extend(dict(**t,source_sha256=sha) for t in found)
                g["curves"].extend(dict(**c,source_sha256=sha) for c in cr)
                g["alignment"].append(dict(source_sha256=sha,frames=frames,axis_candidates=axes,status="verified" if any(f["status"]=="verified" for f in frames) else "candidate" if frames else "unknown"))
            except (ValueError,OSError,RuntimeError,KeyError,IndexError,AttributeError,ezdxf.DXFError) as exc:
                g["issues"].append(dict(file=source.name,source_sha256=sha,code=type(exc).__name__,detail=str(exc)))
    g["relationships"]=links(g["inventory"]);g["validation"]=check(g)
    return g


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("tool",choices=["run",*TOOLS]);p.add_argument("input",type=Path)
    p.add_argument("--out",type=Path,required=True);p.add_argument("--oda")
    a=p.parse_args();src=a.input.resolve(strict=True);out=a.out.resolve()
    if out.exists() or (src.is_dir() and out.is_relative_to(src)):p.error("请使用输入目录之外的新目录")
    out.mkdir(parents=True);start=time.perf_counter()
    if a.tool=="geometry_data_validate" and src.suffix.lower()==".json":
        data=json.loads(src.read_bytes());result=check(data);rc=0 if result["valid"] else 4
    else:
        g=process(src,out,a.oda);g["elapsed_s"]=time.perf_counter()-start
        result=g if a.tool=="run" else g[TOOLS[a.tool]]
        rc=4 if g["issues"] or not g["validation"]["valid"] else 0
    file=out/("geometry.json" if a.tool=="run" else a.tool+".json")
    file.write_text(json.dumps(result,ensure_ascii=False,allow_nan=False,separators=(",",":"))+"\n")
    print(json.dumps(dict(output=str(file),exit=rc,seconds=time.perf_counter()-start),ensure_ascii=False))
    return rc


if __name__=="__main__":raise SystemExit(main())
