"""从已配准的原图水线生成局部半宽片体。仅在同一组相邻约束的公共覆盖区内求值。"""
import re
import numpy as np
from cad_input import fingerprint
from geometry import build_shell, read_curves
from accuracy_gate import assess


def surfaces(entries, regions):
    by_sha = {item["sha256"]: item for item in entries if "cad" in item}
    seen = set()
    for region in regions:
        name = region["id"]
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", name) or name in seen:
            raise ValueError("区域名称无效或重复")
        seen.add(name)
        curves = []
        try:
            if not region["frame_evidence"].strip():
                raise ValueError("配准依据缺失")
            used = set()
            for spec in region["curves"]:
                key = spec["source_sha256"], spec["handle"]
                if key in used or key[0] not in by_sha:
                    raise ValueError("图纸指纹不匹配或存在重复证据")
                used.add(key)
                curve, = read_curves(by_sha[key[0]]["cad"], [spec])
                curve["handle"] = ":".join(key)
                curves.append(curve)
            guides = [c for c in curves if c["use"] == "constraint"]
            waterlines = [c for c in guides if c["kind"] == "waterline"]
            if len(waterlines) < 2 or any(c["kind"] not in ("waterline","section") for c in guides):
                raise ValueError("至少需要两条已配准的水线")
            zs = sorted(float(c["points_m"][0][2]) for c in waterlines)
            if np.any(np.diff(zs) < 1e-5):
                raise ValueError("同一水线层存在多个候选")
            stations = region["stations_m"]
            if not isinstance(stations, list) or any(type(x) not in (int, float) for x in stations):
                raise ValueError("站位必须是米制数值数组")
            xs = np.asarray(stations, dtype=float)
            if len(xs)<2 or not np.isfinite(xs).all() or np.any(np.diff(xs)<=0):
                raise ValueError("需要严格递增的有限站位")
            # A cell can join two contour crossings only if the curve between
            # them is a single branch. Reject folded projections before meshing.
            sections = [c["points_m"][0][0] for c in guides if c["kind"]=="section"]
            xs = np.unique(np.r_[xs,[x for x in sections if xs[0]<=x<=xs[-1]]])
            for curve in waterlines:
                p = np.asarray(curve["points_m"])
                active=(np.maximum(p[:-1,0],p[1:,0])>=xs[0]) & (np.minimum(p[:-1,0],p[1:,0])<=xs[-1])
                steps = np.diff(p[:,0])[active]
                if not (np.all(steps >= -1e-8) or np.all(steps <= 1e-8)):
                    raise ValueError("水线纵向投影折返，需分段复核："+curve["handle"])
                if np.any((np.abs(steps)<1e-10) & (np.abs(np.diff(p[:,1])[active])>1e-6)):
                    raise ValueError("同站多值水线："+curve["handle"])
            rows = [dict(x_m=x,z_m=z,breadth_m=None) for x in xs for z in zs]
            mesh, faces, detail = build_shell(rows, guides, False, False)
            yield name, (mesh, faces, detail, curves), None
        except (ValueError, KeyError, TypeError) as exc:
            yield name, None, str(exc)


def deliver(entries, profile, out, report, write_asset, save):
    from shapely import STRtree, Polygon, Point
    report.update(domain="registered_halfbreadth_patches",regions=[],formal_calculation_authorized=False)
    for name, patch, error in surfaces(entries,profile["regions"]):
        if error:
            report["regions"].append(dict(id=name,status="blocked",reason=error))
            continue
        mesh, faces, detail, curves = patch
        try:
            actual = write_asset(out,name,name+".glb",mesh,report)
            qa = report["assets"][name]["quality"]
            if (qa["self_intersection_pairs"]!=0 or not qa["vertex_manifold"] or
                    any(qa["topology"][k] for k in ("degenerate_faces","duplicate_faces","nonmanifold_edges","inconsistent_winding_edges"))):
                raise ValueError("片体读回质量未通过")
        except (ValueError, ImportError, OSError) as exc:
            report["assets"].pop(name,None)
            failed=out/(name+".glb")
            if failed.exists():
                diagnostic=out/"diagnostics"
                diagnostic.mkdir(exist_ok=True)
                failed.rename(diagnostic/failed.name)
            report["regions"].append(dict(id=name,status="blocked",reason=str(exc)))
            continue
        tri=actual.triangles
        tree=STRtree([Polygon(t[:,[0,2]]) for t in tri])
        residual=[]
        for c in curves:
            if c["use"]!="holdout":continue
            points=c["points_m"]
            for i,(x,y,z) in enumerate(points):
                q=Point(x,z)
                indices=tree.query(q,predicate="intersects")
                error=None
                if len(indices):
                    a,b,d=tri[int(indices[0])]
                    normal=np.cross(b-a,d-a)
                    error=float(a[1]-(normal[0]*(x-a[0])+normal[2]*(z-a[2]))/normal[1]-y)
                residual.append(dict(source=c["handle"],sample=i,xyz_m=[x,y,z],dy_m=error))
        accuracy=assess(residual, profile.get("accuracy_policy"))
        path=out/(name+"-evidence.json")
        save(path,dict(asset=report["assets"][name]["sha256"],profile=report["profile_sha256"],
                       faces=faces,construction=detail,holdout=residual,accuracy=accuracy))
        report["regions"].append(dict(id=name,status="partial_surface",evidence=path.name,
                                      evidence_sha256=fingerprint(path),faces=len(faces),accuracy=accuracy,
                                      curves=[c["handle"] for c in curves]))
    report["status"]="partial_surface" if report["assets"] else "needs_evidence"
