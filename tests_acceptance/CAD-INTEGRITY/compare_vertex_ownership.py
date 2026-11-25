"""在新目录生成可公开的合成几何；入参 writer 是同版本控制与实验写出器。"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import ezdxf


def records(path):
    lines = path.read_bytes().splitlines()
    if len(lines) % 2:
        raise ValueError("DXF 组码行数不是偶数")
    row = {}
    for code, value in zip(lines[::2], lines[1::2]):
        code = int(code)
        if code == 0 and row:
            yield row
            row = {}
        row.setdefault(code, []).append(value.decode("ascii").strip())
    if row:
        yield row


def summarize(path, expected, sentinel):
    counts = Counter()
    tags_by_handle = {h: [] for h in expected}
    boundary_counts = Counter()
    neighbor_count = 0
    for row in records(path):
        kind = row.get(0, [""])[0]
        handle = row.get(5, [""])[0]
        if kind == "ENDBLK":
            boundary_counts[handle] += 1
        if kind == "LINE" and handle == sentinel:
            neighbor_count += 1
        if kind == "VERTEX":
            counts[handle] += 1
            if handle in expected:
                tags_by_handle[handle].append([
                    *(float(row[k][0]) for k in (10, 20, 30)),
                    int(row.get(70, [0])[0]), float(row.get(42, [0])[0]),
                ])
    return {
        "vertices_seen": dict(counts),
        "every_expected_vertex_exactly_once": counts == Counter(expected.keys()),
        "every_observed_expected_vertex_has_right_fields": all(
            values and all(entry == expected[h] for entry in values)
            for h, values in tags_by_handle.items()
        ),
        "sentinel_line_count": neighbor_count if sentinel else None,
        "repeated_endblk_handles": {h: n for h, n in boundary_counts.items() if n > 1},
    }


def set_vertex_owner(data, owner):
    lines = data.splitlines(keepends=True)
    kind = None
    changed = 0
    for i in range(0, len(lines), 2):
        code = int(lines[i])
        value = lines[i+1].strip()
        if code == 0:
            kind = value
        elif kind == b"VERTEX" and code == 330:
            lines[i+1] = lines[i+1].replace(value, owner.encode("ascii"))
            changed += 1
    return b"".join(lines), changed


def handle(row, key):
    value = row.get(key)
    return format(value[-1], "X") if value and value[-1] else None


def graph(objects, target, parent, expected):
    objects_by_handle = {}
    collisions = {}
    for obj in objects:
        key = handle(obj, "handle")
        if key in objects_by_handle:
            prev = objects_by_handle[key]
            kinds = collisions.setdefault(key, [prev.get("entity",prev.get("object"))])
            kinds.append(obj.get("entity", obj.get("object")))
            if key in {target, parent, *expected}:
                raise ValueError("DWG 中受测对象句柄不唯一")
        objects_by_handle[key] = obj
    block = objects_by_handle[target]
    curve = objects_by_handle[parent]
    first, last = (objects_by_handle[handle(curve, k)]["index"]
                   for k in ("first_vertex", "last_vertex"))
    children = [r for r in objects if first <= r["index"] <= last]
    if [handle(r,"handle") for r in children] != list(expected):
        raise ValueError("试件的 DWG 顶点索引与输入顺序不符")
    for r in children:
        h = handle(r, "handle")
        if r.get("entity") != "VERTEX_2D" or [*r["point"], r["flag"], r["bulge"]] != expected[h]:
            raise ValueError("试件生成时已经改变源顶点字段")
    return {
        "other_source_handle_collisions": collisions,
        "dwg_vertex_objects": sum(r.get("entity") == "VERTEX_2D" for r in objects),
        "block_first": handle(block, "first_entity"), "block_last": handle(block, "last_entity"),
        "curve": parent, "curve_next": handle(curve, "next_entity"),
        "first_vertex": handle(curve, "first_vertex"), "last_vertex": handle(curve, "last_vertex"),
        "curve_seqend": handle(curve, "seqend"),
        "vertex_owner_in_decoded_dwg": {handle(v,"handle"):handle(v,"ownerhandle") for v in children},
        "model_space_header_count": sum(r.get("object") == "BLOCK_HEADER" and
                                       r.get("name","").lower() == "*model_space" for r in objects),
    }


def case(folder, space, signed, neighbor, insert, writers):
    folder.mkdir()
    doc = ezdxf.new("R2000")
    layout = doc.blocks.new("ARC_SAMPLE") if space == "block" else doc.modelspace()
    if insert:
        doc.modelspace().add_blockref("ARC_SAMPLE", (0, 0))
    coords = [(0, 0), (2, 1), (4, 0), (5, 1)] if signed else [(0, 0), (2, 1)]
    pipe = layout.add_polyline2d(coords)
    expected = {}
    for i, v in enumerate(pipe.vertices):
        flag, bulge = ([(0, 0.25), (1, -0.5), (0, 0), (0, 0)][i]
                       if signed else (0, 0))
        v.dxf.flags, v.dxf.bulge = flag, bulge
        expected[v.dxf.handle] = [*v.dxf.location, flag, bulge]
    line = layout.add_line((1, 0), (2, 3)) if neighbor else None
    sentinel = line.dxf.handle if line else None
    original = folder/"generated.dxf"
    doc.saveas(original)
    raw = original.read_bytes()
    changed, number = set_vertex_owner(raw, pipe.dxf.handle)
    if number != len(expected) or raw == changed:
        raise ValueError("试件未产生预期的 330 单变量")
    result = {}
    for name, data in [("block_owner", raw), ("curve_owner", changed)]:
        source, dwg = folder/(name+".dxf"), folder/(name+".dwg")
        source.write_bytes(data)
        sr = summarize(source, expected, sentinel)
        if not sr["every_expected_vertex_exactly_once"] or not sr["every_observed_expected_vertex_has_right_fields"]:
            raise ValueError("源 DXF 不满足本试验的序列或几何要求")
        subprocess.run(["dxf2dwg", "--as", "r2000", "-o", dwg, source], check=True,capture_output=True)
        objects = json.loads(subprocess.check_output(
            ["dwgread", "-O", "JSON", dwg], stderr=subprocess.DEVNULL))["OBJECTS"]
        outputs = {}
        for wname, writer in writers.items():
            dst = folder/(name+"."+wname+".dxf")
            subprocess.run([writer, dwg, dst, "control", "1"], check=True, capture_output=True)
            outputs[wname] = summarize(dst, expected, sentinel)
        result[name] = {
            "source_dxf_sha256": hashlib.sha256(data).hexdigest(), "source_dxf": sr,
            "dwg_graph": graph(objects, layout.block_record_handle, pipe.dxf.handle, expected),
            "writers": outputs,
        }
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("new_folder",type=Path)
    p.add_argument("baseline",type=Path,help="上一轮修复已生效的写出器")
    p.add_argument("guarded",type=Path,help="本轮隔离修正版")
    args = p.parse_args()
    args.new_folder.mkdir(exist_ok=False)
    writers = {"baseline": args.baseline.resolve(), "guarded": args.guarded.resolve()}
    scenarios = [
        ("minimal", "block", False, False, False),
        ("with_neighbor", "block", False, True, False),
        ("signed_with_insert", "block", True, False, True),
        ("model_space", "model", False, False, False),
        ("model_signed_neighbor", "model", True, True, False),
    ]
    results = {name: case(args.new_folder/name, space, signed, neighbor, insert, writers)
               for name,space,signed,neighbor,insert in scenarios}
    (args.new_folder/"results.json").write_text(json.dumps(results,indent=2)+"\n")
    for pair in results.values():
        for variant, ctrl in pair.items():
            base, fixed = (ctrl["writers"][k] for k in ("baseline","guarded"))
            if base["every_expected_vertex_exactly_once"] != (variant == "curve_owner"):
                raise ValueError("基线不符合用例")
            if not fixed["every_expected_vertex_exactly_once"] or not fixed["every_observed_expected_vertex_has_right_fields"]:
                raise ValueError("防护修正失败")
            if fixed["sentinel_line_count"] not in (None,1):
                raise ValueError("相邻独立线段丢失或重复")


if __name__ == "__main__":
    main()
