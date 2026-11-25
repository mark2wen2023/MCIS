"""Independent, offline DXF-to-GLB experiment. Use only the synthetic drawing convention below."""
import argparse
import csv
import hashlib
import json
import platform
import re
import sys
from pathlib import Path

import ezdxf
from jsonschema import Draft202012Validator
import numpy as np
import trimesh


PIN = "fd40255e956ef579ba7ed7c8aa41b722388ad1a4"
SCENARIOS = ("full", "one_cell_changed", "sparse", "unseen_profile", "pending", "duplicate", "empty_row")
LAYERS = ("BODY", "GRID", "ROW_Z_MM", "STATION_MM", "LEGEND")


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return json.loads(path.read_text(encoding="utf-8"))


def reference_width_mm(i, j):
    # Synthetic oracle for drawing generation and the independent final readback only.
    return 100 + 65 * (4 - abs(2 - i)) + (25 + 6 * i) * j


def make_drawing(path, case):
    ezdxf.options.write_fixed_meta_data_for_testing = True
    drawing = ezdxf.new("R2010")
    drawing.units = 4
    model = drawing.modelspace()
    for layer in LAYERS:
        drawing.layers.new(layer)
    def label(layer, value, x, y):
        model.add_text(str(value), dxfattribs={"layer": layer, "height": 1.0, "insert": (x, y)})
    stations_mm, levels_mm = ([0, 2300, 4250], [200, 900, 1700]) if case == "unseen_profile" else ([0,1500,3000,4500,6000],[0,500,1000,1500])
    cols, rows = len(stations_mm), len(levels_mm)
    for i in range(cols+1):
        model.add_line((i*20, 0), (i*20, rows*10), dxfattribs={"layer": "GRID"})
    for j in range(rows+1):
        model.add_line((0, j*10), (cols*20, j*10), dxfattribs={"layer": "GRID"})
    for i, station in enumerate(stations_mm):
        label("STATION_MM", station, 10+i*20, rows*10+6)
    for j, level in enumerate(levels_mm):
        y=10*rows-5-j*10
        label("ROW_Z_MM", level, -8, y)
        for i in range(cols):
            if (case == "sparse" and (i,j) == (2,1)) or (case == "empty_row" and j == 1):
                continue
            value = reference_width_mm(i,j) + (125 if case == "one_cell_changed" and (i,j) == (2,1) else 0)
            if case == "unseen_profile":
                value = 330 + 19*i*i + 75*j*j
            label("BODY", value, 10+i*20, y)
            if case == "duplicate" and (i,j) == (2,1):
                label("BODY", value+400, 10.1+i*20, y)
    label("LEGEND", "OFFSET TABLE", 0, 60)
    label("LEGEND", "OBS=mm; X=forward; Z=up; ORIGIN_M=32768,0,2", 0, 66)
    label("LEGEND", "SYNTHETIC TEST REVIEW="+("pending" if case=="pending" else "accepted"), 0, 72)
    drawing.saveas(path)


def run(source, case_dir, schema):
    from mcis_service.agents.skills.ship_reconstruction import (
        drawing_parser, drawing_pipeline, table_detection, table_geometry, offset_cell_semantics,
        coordinate_frame, sparse_section, reconstruction_pipeline, glb_export, asset_integrity)
    def record(name, value): return save(case_dir / name, value)
    issue = {"status":"blocked", "stage":None, "issues":[]}
    parsed = record("01-parsed.json", drawing_parser.parse_drawing(source))
    doc_id = parsed["document"]["id"]
    assert parsed["document"]["status"]=="partial" and doc_id==hashlib.sha256(source.read_bytes()).hexdigest()
    entities = parsed["entities"]
    groups = {name:[e for e in entities if e["layer"]==name and e["layout"]=="Model"] for name in LAYERS}
    grid = table_geometry.detect_grid([{"start":s["start"][:2],"end":s["end"][:2],"handle":e["handle"]}
                   for e in groups["GRID"] for s in e["segments_wcs"]], .01)
    assert grid["candidate_complete"] and len(table_detection.detect_titles(entities))==1
    # This review bridge knows only the fixture's layer and annotation convention.
    x_headers = sorted(groups["STATION_MM"], key=lambda e:e["anchor_wcs"][0])
    z_headers = sorted(groups["ROW_Z_MM"], key=lambda e:-e["anchor_wcs"][1])
    frame_e = next(e for e in groups["LEGEND"] if e["text"].startswith("OBS="))
    frame_match = re.fullmatch(r"OBS=(mm); X=(forward); Z=(up); ORIGIN_M=(-?\d+),0,(-?\d+)",frame_e["text"])
    assert frame_match and parsed["units"]==4
    unit, xdir, zdir, x0, z0 = frame_match.groups()
    state = next(e for e in groups["LEGEND"] if e["text"].startswith("SYNTHETIC TEST REVIEW="))
    xs,ys = grid["x_boundaries"], grid["y_boundaries"]
    region = dict(layout="Model",bounds=[xs[0],ys[0],xs[-1],ys[-1]],plane_z=0,tolerance=.01)
    mapping = dict(row_specs=[dict(height_m=float(e["text"])/1000,locator="row entity "+e["handle"]) for e in z_headers],
                   stations_m=[float(e["text"])/1000 for e in x_headers],anchors=[e["anchor_wcs"][0] for e in x_headers],
                   unit=unit,row_tolerance=.2,column_tolerance=.5)
    record("02-mapping.json",dict(region=region,mapping=mapping,headers=x_headers,grid=grid,frame_annotation=frame_e,review=state))
    extraction = record("03-offsets.json", drawing_pipeline.extract_from_drawing(parsed,region=region,mapping=mapping))
    if extraction["issues"] or any(extraction["diagnostics"][k] for k in ("invalid_rows","conflicting_rows")):
        return {**issue, "stage":"extraction","issues":extraction["issues"]}
    draft = dict(version="0.1",frame=dict(origin_description=frame_e["text"], x_positive=xdir,
                 z_positive=zdir,review="pending"),rows=extraction["rows"])
    schema.validate(draft)
    rows = record("03a-offset-contract.json",draft)["rows"]
    if state["text"]!="SYNTHETIC TEST REVIEW=accepted":
        return {**issue,"stage":"semantic_review","issues":["no synthetic review approval"]}
    frame = dict(unit="m", x_direction=xdir, z_direction=zdir, x_origin_m=float(x0), z_origin_m=float(z0),
                 review="accepted",source=dict(document_id=doc_id,locator="entity "+frame_e["handle"]))
    reviewed=[]
    for r in rows:
        width=r["half_breadth_m"]
        semantic="unknown" if width is None else ("confirmed_zero" if width==0 else "measured")
        cell=offset_cell_semantics.classify_cell(width,semantic=semantic,evidence=r["source"])
        cell["review"]="pending" if width is None else "accepted"
        # Unknown cells carry only axis positions. Transform axes using the two
        # independent affine mappings; do not substitute a dummy half breadth.
        if width is None:
            x=frame["x_origin_m"]+r["station_x_m"]
            z=frame["z_origin_m"]+r["height_z_m"]
        else:
            point=coordinate_frame.normalize_offset(r["station_x_m"],r["height_z_m"],width,frame=frame)
            x,z=point["station_x_m"],point["height_z_m"]
            assert point["half_breadth_m"]==width
        reviewed.append(dict(**cell,station_m=x,height_m=z))
    reviewed=record("04-reviewed-and-transformed.json",dict(frame=frame,cells=reviewed,review_evidence=state))["cells"]
    stations=sorted({r["station_m"] for r in reviewed})
    levels=sorted({r["height_m"] for r in reviewed})
    heights=sorted(set(levels)|{(a+b)/2 for a,b in zip(levels,levels[1:])})
    samples=[sparse_section.sample_sparse_section(sorted((r for r in reviewed if r["station_m"]==x),
                    key=lambda r:r["height_m"]),heights)["samples"] for x in stations]
    samples=record("05-sections.json",dict(stations=stations,heights=heights,samples=samples))["samples"]
    approvals={(i,j):dict(review="accepted",document_id=doc_id,locator="entity "+state["handle"]+f" / cell {i},{j}")
               for i in range(len(stations)-1) for j in range(len(heights)-1)
               if all(samples[a][b]["half_breadth_m"] is not None for a in [i,i+1] for b in [j,j+1])}
    mesh=record("06-mesh-and-provenance.json",reconstruction_pipeline.reconstruct_sparse(stations,heights,samples,approvals))
    glb,side=glb_export.export_glb(mesh,local_origin_m=[float(x0),0,float(z0)],max_vertex_error_m=1e-6,
                                   max_area_relative_error=1e-5,max_edge_relative_error=1e-5)
    glbfile=case_dir/"research.glb"
    glbfile.write_bytes(glb)
    side=record("07-evidence.json",side)
    manifest=record("08-binding.json",asset_integrity.bind_asset(glbfile.read_bytes(),side,algorithm_version=PIN))
    check=asset_integrity.verify_asset(glbfile.read_bytes(),side,manifest,expected_algorithm_version=PIN)
    assert check["matches"] and check["lofting_authorized"] is False
    loaded=trimesh.load(glbfile,force="mesh",process=False)
    vertex=np.asarray(loaded.vertices)
    world=np.column_stack((vertex[:,0],-vertex[:,2],vertex[:,1]))+np.asarray(side["mcis_origin_m"])
    assert np.array_equal(loaded.faces,mesh["mesh"]["triangles"])
    err=float(np.linalg.norm(world-np.array(mesh["mesh"]["vertices_m"]),axis=1).max())
    assert err<1e-6 and len(side["faces"])==len(loaded.faces)
    handles={e["handle"] for e in groups["BODY"]}
    for face in side["faces"]:
        assert all(ref["document_id"]==doc_id and ref["locator"].split("entity ")[-1] in handles for ref in face["sources"])
    record("09-independent-readback.json",dict(world_vertices_m=world.tolist(),faces=loaded.faces.tolist(),max_error_m=err,
            verified=check,open_boundary_edges=len(mesh["quality"]["boundary_edges"])))
    return dict(status="written",stage="verified",cells=len(reviewed),nulls=sum(r["value"] is None for r in reviewed),
                stations=len(stations),vertices=len(world),faces=len(loaded.faces),skipped_cells=mesh["mesh"]["skipped_cells"],
                maximum_readback_error_m=err,sha256=manifest["glb_sha256"],approved_for_engineering=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_tree",type=Path)
    parser.add_argument("fresh_output",type=Path)
    args=parser.parse_args()
    sys.path.insert(0,str(args.source_tree.resolve()/"service"))
    schema_path=args.source_tree/"contracts/schemas/ship-offset-table.schema.json"
    schema=Draft202012Validator(json.loads(schema_path.read_text()))
    out=args.fresh_output
    out.mkdir(parents=True,exist_ok=False)
    module_dir=args.source_tree/"service/mcis_service/agents/skills/ship_reconstruction"
    digest=hashlib.sha256()
    for path in sorted(module_dir.glob("*.py")):
        digest.update(path.name.encode()+b"\0"+path.read_bytes()+b"\0")
    if digest.hexdigest()!="5085404221bbf96102fdde95ace654ba7c0a7d95a2392a56253388b8538e4d31":
        raise ValueError("被测模块与冻结版本不一致")
    results={}
    for case in SCENARIOS:
        case_dir=out/case
        case_dir.mkdir()
        dxf=case_dir/"fictional.dxf"
        make_drawing(dxf,case)
        results[case]=run(dxf,case_dir,schema)
        save(case_dir/"outcome.json",results[case])
    for case in ("full","one_cell_changed","sparse"):
        r=results[case]
        assert r["status"]=="written"
        data=json.loads((out/case/"09-independent-readback.json").read_text())
        for x,y,z in data["world_vertices_m"]:
            i=int(round((x-32768)/1.5)); level=(z-2)/.5
            # Independent formula at input levels, with a triangular response
            # at intermediate samples when one observed ordinate changes.
            j=int(np.floor(level))
            expected=reference_width_mm(i,j)+(level-j)*(25+6*i)
            if case=="one_cell_changed" and i==2:
                expected+=125*max(0,1-abs(level-1))
            assert abs(y-expected/1000)<1e-6
    assert results["full"]["faces"]==results["one_cell_changed"]["faces"]==48
    assert results["sparse"]["faces"]==32 and results["sparse"]["nulls"]==1
    assert results["full"]["sha256"]!=results["one_cell_changed"]["sha256"]
    other = results["unseen_profile"]
    assert other["status"]=="written" and (other["stations"],other["cells"],other["faces"])==(3,9,16)
    other_points=json.loads((out/"unseen_profile/09-independent-readback.json").read_text())["world_vertices_m"]
    for x,y,z in other_points:
        i=int(np.argmin(np.abs(np.array([0,2.3,4.25])-(x-32768))))
        original_widths=[(330+19*i*i+75*j*j)/1000 for j in range(3)]
        assert abs(y-np.interp(z-2,[.2,.9,1.7],original_widths))<1e-6
    assert results["pending"]["stage"]=="semantic_review"
    assert all(results[k]["stage"]=="extraction" for k in ("duplicate","empty_row"))
    save(out/"summary.json",dict(commit=PIN,python=sys.version,os=platform.platform(),ezdxf=ezdxf.__version__,
             numpy=np.__version__,trimesh=trimesh.__version__,cases=results))
    with (out/"summary.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["case","status","stage","cells","nulls","faces","maximum_readback_error_m"],extrasaction="ignore")
        w.writeheader()
        for k,r in results.items(): w.writerow(dict(case=k,**r))
    print({k:r["status"] for k,r in results.items()})

if __name__=="__main__": main()
