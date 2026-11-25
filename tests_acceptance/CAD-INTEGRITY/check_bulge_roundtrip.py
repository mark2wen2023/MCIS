"""Offline conformance test on a generated classic POLYLINE with signed arcs."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

import ezdxf
from ezdxf.lldxf.tagger import ascii_tags_loader
from ezdxf.lldxf.tags import group_tags


def check(folder):
    source = folder / "fixture.dxf"
    dwg = folder / "fixture.dwg"
    output = folder / "candidate.dxf"
    document = ezdxf.new("R2000")
    block = document.blocks.new("ARC_SAMPLE")
    document.modelspace().add_blockref("ARC_SAMPLE", (0, 0))
    curve = block.add_polyline2d([(0, 0), (2, 1), (4, 0), (5, 1)])
    expected = {}
    for vertex, (flag, bulge) in zip(curve.vertices, [(0, 0.25), (1, -0.5), (0, 0.0), (0, 0.0)]):
        vertex.dxf.flags = flag
        vertex.dxf.bulge = bulge
        expected[vertex.dxf.handle] = (flag, bulge)
    document.saveas(source)
    subprocess.run(["dxf2dwg", "--as", "r2000", "-o", dwg, source], check=True, capture_output=True)
    raw = subprocess.check_output(["dwgread", "-O", "JSON", dwg], stderr=subprocess.DEVNULL)
    vertices = {
        format(e["handle"][-1], "X"): (e.get("flag", 0), e.get("bulge", 0))
        for e in json.loads(raw)["OBJECTS"] if e.get("entity") == "VERTEX_2D"
    }
    if vertices != expected:
        raise ValueError("合成 DWG 未复现输入顶点，无法评价输出转换器")
    subprocess.run(["dwg2dxf", "-o", output, dwg], check=True, capture_output=True)
    written = {handle: [] for handle in expected}
    with output.open("r", encoding="ascii", errors="strict") as stream:
        for tags in group_tags(ascii_tags_loader(stream)):
            if tags[0].value != "VERTEX":
                continue
            handle = tags.get_first_value(5)
            if handle in written:
                flag = int(tags.get_first_value(70, 0))
                bulge = float(tags.get_first_value(42, 0))
                written[handle].append((flag, bulge))
    diffs = []
    for handle, wanted in expected.items():
        values = written[handle]
        if not values or any(pair != wanted for pair in values):
            diffs.append({"synthetic_handle": handle, "expected": wanted, "actual": values})
    return {
        "fixture": "synthetic_classic_polyline",
        "checked_vertices": len(expected),
        "written_occurrences": {h: len(v) for h, v in written.items()},
        "differences": diffs,
        "all_handles_written_once": all(len(v) == 1 for v in written.values()),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bulge-only", action="store_true", help="仅检查凸度和标志；仍报告句柄次数")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        result = check(Path(tmp))
    print(json.dumps(result, indent=2))
    failed = bool(result["differences"]) or (not args.bulge_only and not result["all_handles_written_once"])
    raise SystemExit(4 if failed else 0)
