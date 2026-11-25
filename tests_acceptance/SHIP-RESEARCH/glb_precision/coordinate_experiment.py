"""在冻结源码上测量位置存储误差；调用已有 GLB 导出器，场景均为合成。"""
import argparse
import csv
from decimal import Decimal, getcontext
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import trimesh

COMMIT = "4293d24f99ad1dc16fac5e6660bea467f01d6145"
MODES = ("global", "local_from_f64", "late_recentre", "local_from_decimal")
FACES = [[0, 1, 2], [1, 3, 2]]
D = Decimal
getcontext().prec = 75


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def error(actual, reference):
    squared = (sum((x - y) ** 2 for x, y in zip(a, b)) for a, b in zip(actual, reference))
    return float(max(squared).sqrt())


def decimals(values):
    return [[D.from_float(float(v)) for v in point] for point in values]


def shift(points, origin):
    return [[v + o for v, o in zip(p, origin)] for p in points]


def areas(vertices):
    points = np.asarray(vertices, dtype=np.float64)[FACES]
    return (np.linalg.norm(np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0]), axis=1) / 2).tolist()


def face_evidence(i):
    return {"face_id": i, "cell": [0, 0], "corner_bases": ["direct_sample"] * 4,
            "sources": [{"document_id": "SYNTHETIC", "locator": "four-vertices"}],
            "cell_review": {"document_id": "SYNTHETIC", "locator": "unit-square-test", "review": "accepted"},
            "basis": "computed_surface", "review": "pending"}


def measure(export_glb, case, mode, output):
    origin = [D(x) for x in case["origin_m"]]
    local = [[D(x) for x in pt] for pt in case["exact_local_m"]]
    world = shift(local, origin)
    origin64 = np.asarray(origin, dtype=np.float64)
    world64 = np.asarray(world, dtype=np.float64)
    if mode == "global":
        vertices = world64
        frame = [D(0)] * 3
    elif mode == "local_from_f64":
        vertices = world64 - origin64
        frame = origin
    elif mode == "late_recentre":
        vertices = world64.astype(np.float32).astype(np.float64) - origin64
        frame = origin
    else:
        # 已知合成真值：十进制源数据先减原点，再转为浮点。
        vertices = np.asarray(local, dtype=np.float64)
        frame = origin

    stored = vertices.astype(np.float32).astype(np.float64)
    recovered64 = stored + np.asarray(frame, dtype=np.float64)
    recovered32 = (stored.astype(np.float32) + np.asarray(frame, dtype=np.float32)).astype(np.float64)
    split_recovered = shift(decimals(stored), frame)
    ideal_area = float(D(case["width_m"]) / 2)
    input_area = areas(vertices)
    q_area = areas(stored)
    case_id = f"{case['case_id']}_{mode}"
    glb_path = output / "models" / (case_id + ".glb")
    payload = {"mesh": {"vertices_m": vertices.tolist(), "triangles": FACES},
               "provenance": {"faces": [face_evidence(i) for i in range(2)]},
               "research_only": True, "lofting_authorized": False}
    row = {"case": case["case_id"], "mode": mode, "offset_x_m": float(origin[0]),
           "edge_true_m": float(case["width_m"]), "float32_spacing_at_x_m": float(np.spacing(np.float32(origin64[0]))),
           "input_world64_error_m": error(decimals(world64), world),
           "stored_edge_m": float(np.linalg.norm(stored[1] - stored[0])),
           "unique_vertices": len(set(map(tuple, stored))), "face_ref_area_m2": ideal_area,
           "input_area_m2": input_area[0], "stored_area_m2": q_area[0],
           "max_area_relative_change": max(abs(a - ideal_area) for a in q_area) / ideal_area,
           "error_split_frame_m": error(split_recovered, world),
           "error_restored_global64_m": error(decimals(recovered64), world),
           "error_restored_global32_m": error(decimals(recovered32), world),
           "export": None, "reason": "", "actual_glb": "", "glb_sha256": "",
           "second_export_identical": None, "glb_round_trip_vs_export_input_m": None, "glb_restored_vs_exact_m": None}
    decoded = None
    try:
        binary, evidence = export_glb(payload)
    except ValueError as exc:
        row.update(export="rejected", reason=str(exc))
    else:
        assert evidence["lofting_authorized"] is False
        glb_path.write_bytes(binary)
        mesh = trimesh.load(glb_path, force="mesh", process=False)
        # MCIS -> glTF (x,z,-y)，以相反旋转还原；此处读取实际文件。
        decoded = np.column_stack((mesh.vertices[:, 0], -mesh.vertices[:, 2], mesh.vertices[:, 1]))
        assert np.array_equal(mesh.faces, FACES) and np.array_equal(decoded, stored)
        second_payload = {**payload, "mesh": {"vertices_m": decoded.tolist(), "triangles": FACES}}
        second_binary, _ = export_glb(second_payload)
        identical = second_binary == binary
        assert identical, "第二次写出与首次不同"
        row.update(export="written", second_export_identical=identical, actual_glb="models/" + glb_path.name, glb_sha256=hashlib.sha256(binary).hexdigest(),
                   glb_round_trip_vs_export_input_m=float(np.linalg.norm(decoded - vertices, axis=1).max()),
                   glb_restored_vs_exact_m=error(decimals(decoded + np.asarray(frame, dtype=np.float64)), world))
    detail = {"id": case_id, "exact_global_m": [[str(v) for v in pt] for pt in world],
              "frame_origin_m": list(map(str, frame)), "export_input_m": vertices.tolist(),
              "diagnostic_stored_float32_m": stored.tolist(), "diagnostic_face_areas_m2": q_area,
              "glb_decoded_mcis_m": None if decoded is None else decoded.tolist(), "metrics": row}
    return row, detail


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source_tree", type=Path)
    ap.add_argument("new_output_dir", type=Path)
    args = ap.parse_args()
    sys.path.insert(0, str(args.source_tree.resolve() / "service"))
    from mcis_service.agents.skills.ship_reconstruction.glb_export import export_glb
    module = args.source_tree / "service/mcis_service/agents/skills/ship_reconstruction/glb_export.py"
    exporter_hash = hashlib.sha256(module.read_bytes()).hexdigest()
    if exporter_hash != "c81a86405373cd8d61d23a2bcaade175cdba33fe6d344db1ca7d5e03e9202768":
        raise SystemExit(f"导出器与本次冻结记录不匹配：{exporter_hash}")
    out = args.new_output_dir
    out.mkdir(parents=True, exist_ok=False)
    (out / "models").mkdir()
    cases = []
    for base in [0, 1, 1024, 8192, 16384, 32768, 100000, 1000000, 100000000, 10**12, 2**44]:
        for width in ("0.001", "0.01"):
            cases.append({"case_id": f"x{base}_{width.replace('.', 'p')}", "width_m": width,
                          "origin_m": [str(base), "0", "0"],
                          "exact_local_m": [["0", "0", "0"], [width, "0", "0"], ["0", "1", "0"], [width, "1", "0"]]})
    save(out / "input.json", {"study_baseline": COMMIT, "actual_exporter_sha256": exporter_hash, "units": "m", "faces": FACES, "modes": MODES,
                             "mapping": "MCIS(x,y,z) -> glTF(x,z,-y); restored_world = origin + decoded_MCIS",
                             "synthetic": True, "cases": cases})
    rows, details = [], []
    for case in cases:
        for mode in MODES:
            row, detail = measure(export_glb, case, mode, out)
            rows.append(row)
            details.append(detail)
    save(out / "observations.json", details)
    with (out / "metrics.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    study = {(r["offset_x_m"], r["edge_true_m"], r["mode"]): r for r in rows}
    assert study[32768, .001, "global"]["export"] == "rejected"
    assert study[32768, .001, "local_from_f64"]["export"] == "written"
    assert study[2**44, .001, "local_from_f64"]["export"] == "rejected"
    assert study[2**44, .001, "local_from_decimal"]["export"] == "written"
    print(f"{len(cases)} 个场景，{len(rows)} 组对照，写出 {sum(r['export']=='written' for r in rows)} 个 GLB。")


if __name__ == "__main__":
    main()
