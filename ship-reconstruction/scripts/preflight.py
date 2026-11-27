"""校验 CAD、空间查询、网格拓扑、CGAL 自交和点到曲面距离的实际执行能力。"""
import importlib
import importlib.metadata
import json
import platform
import sys


def probe():
    result = {"platform": platform.platform(), "machine": platform.machine(), "python": platform.python_version(), "packages": {}, "errors": []}
    for name in ("numpy","ezdxf","jsonschema","rtree","scipy","shapely","trimesh","libigl"):
        try:
            importlib.import_module("igl" if name == "libigl" else name)
            result["packages"][name] = importlib.metadata.version(name)
        except (ImportError, OSError, importlib.metadata.PackageNotFoundError) as exc:
            result["errors"].append(f"{name}: {exc}")
    try:
        import numpy as np
        import igl
        from igl.copyleft import cgal
        from rtree import index
        from shapely import constrained_delaunay_triangles
        vertices = np.array([[0,0,0],[2,0,0],[0,2,0],[.5,.5,-1],[.5,.5,1],[1,.5,0]], dtype=float)
        faces = np.array([[0,1,2],[3,4,5]], dtype=np.int64)
        pairs = cgal.remesh_self_intersections(vertices, faces, detect_only=True)[2]
        manifold = igl.is_vertex_manifold(faces)
        squared = igl.point_mesh_squared_distance(vertices[:1], vertices, faces)[0]
        tree = index.Index()
        tree.insert(1, (0,0,1,1))
        if len(pairs) != 1 or not manifold.all() or squared[0] != 0 or list(tree.intersection((0,0,0,0))) != [1]:
            raise RuntimeError("几何对照样本输出异常")
        result["intersection_control_pairs"] = len(pairs)
    except (ImportError, OSError, RuntimeError, AttributeError) as exc:
        result["errors"].append(str(exc))
    result["status"] = "environment_blocked" if result["errors"] else "ready"
    return result


if __name__ == "__main__":
    r = probe()
    print(json.dumps(r, ensure_ascii=False, indent=2))
    sys.exit(0 if r["status"] == "ready" else 4)
