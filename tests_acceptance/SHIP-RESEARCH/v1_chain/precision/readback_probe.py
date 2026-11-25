"""生成本地合成读回证据。用法：设置 MCIS_SOURCE_TREE 并传入新目录。"""
import json
from pathlib import Path
import sys

from test_precision_contracts import bind_asset, export_glb, narrow, read_metrics, triangle, verify_asset, with_extras, world_points


def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def collect(output):
    output.mkdir(parents=True, exist_ok=True)
    limits = dict(max_vertex_error_m=1e-8, max_area_relative_error=.01, max_edge_relative_error=.01)
    origin = [32768., -523., 71.]
    points = [[origin[0]+x,origin[1]+y,origin[2]+z] for x,y,z in [[0,0,0],[.001,0,.25],[0,-2,.5]]]
    source = triangle(points)
    glb, side = export_glb(source, local_origin_m=origin, **limits)
    manifest = bind_asset(glb, side, algorithm_version="SYNTHETIC-V1")
    decoded = world_points(glb, origin)
    measured = read_metrics(points, decoded)
    summary = {"synthetic":True,"linear_units":"m","limits":limits,
               "source_points":points,"decoded_world":decoded.tolist(),"decoded_world_metrics":measured,
               "export_local_metrics":side["precision"],
               "verified":verify_asset(glb,side,manifest,expected_algorithm_version="SYNTHETIC-V1")}
    (output/"example.glb").write_bytes(glb)
    for name,value in [("source",source),("sidecar",side),("manifest",manifest),("roundtrip",summary)]:
        save(output/(name+".json"),value)
    observations = []
    for ox,x in [(16384.,1e-13),(2.**54,1.)]:
        source = triangle([[x,0,0],[x,1,0],[x,0,1]])
        origin = [ox,0,0]
        glb, side = export_glb(source, local_origin_m=origin, max_vertex_error_m=0)
        world = world_points(glb, origin)
        observations.append({"case":"global-restoration","source":source["mesh"]["vertices_m"],"origin":origin,
                             "limit":0.,"sidecar_metrics":side["precision"],"actual_world":world.tolist(),
                             "readback_metrics":read_metrics(source["mesh"]["vertices_m"],world),
                             "gate":side["lofting_authorized"]})
    for stored,supplied in [(None,None), ("unknown","unknown"),([1,0,0],[True,0,0])]:
        glb,side = export_glb(narrow())
        changed = with_extras(glb,lambda ex:ex.update(mcis_origin_m=stored))
        side["mcis_origin_m"] = supplied
        manifest = bind_asset(changed,side,algorithm_version="SYNTHETIC-V1")
        checked = verify_asset(changed,side,manifest,expected_algorithm_version="SYNTHETIC-V1")
        observations.append({"case":"origin-type","glb_origin":stored,"sidecar_origin":supplied,"result":checked})
    save(output/"open-observations.json",observations)
    rejects = []
    for field in ("max_area_relative_error","max_edge_relative_error","max_vertex_error_m"):
        try:
            export_glb(narrow(),**{field:0.})
        except ValueError as exc:
            rejects.append({"test":field,"limit":0.,"error":str(exc),"source":narrow()["mesh"]})
        else:
            raise AssertionError(field)
    save(output/"rejections.json", rejects)


if __name__ == "__main__":
    collect(Path(sys.argv[1]))
