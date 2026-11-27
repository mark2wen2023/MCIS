"""从指定源码版本运行同一套合成故障，留下运行目录供外部重新计算指纹。"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
from unittest.mock import patch

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("skill", type=Path)
p.add_argument("output", type=Path)
args = p.parse_args()
sys.path.insert(0, str(args.skill.resolve() / "scripts"))
import s6

args.output.mkdir(parents=True, exist_ok=False)
summary = {}
for fault in ("stage_hull", "stage_structure", "stage_equipment", "asset_write", "input_change", "seal_write", "recovery"):
    case = args.output / fault
    src = case / "input"
    src.mkdir(parents=True)
    source = src / "synthetic.dxf"
    shutil.copyfile(args.skill / "examples/s21/A/input.dxf", source)
    out = case / "run"

    def fail_stage(*args, **kwargs):
        raise RuntimeError("controlled stage failure")

    def fail_asset(path, *args, **kwargs):
        path.write_bytes(b"injected incomplete asset")
        raise OSError("controlled write failure")

    original_hull = s6.hull_stage
    def change_input(*args, **kwargs):
        result = original_hull(*args, **kwargs)
        with source.open("ab") as f:
            f.write(b"\n")
        return result

    original_save = s6.save
    def interrupt(path, value):
        if path.name == "manifest.tmp" and (out / "strict-quality.json").exists():
            raise OSError("controlled final manifest failure")
        return original_save(path, value)

    injections = {"stage_hull": ("hull_stage", fail_stage), "stage_structure": ("structure_stage", fail_stage),
                  "stage_equipment": ("extract_equipment", fail_stage), "asset_write": ("export_mesh", fail_asset),
                  "input_change": ("hull_stage", change_input), "seal_write": ("save", interrupt)}
    row = {}
    try:
        if fault == "recovery":
            prior = args.output / "seal_write/run"
            s6.run(src, out, recover_from=prior)
        else:
            with patch.object(s6, *injections[fault]):
                s6.run(src, out)
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
    manifest = out / "manifest.json"
    if manifest.exists():
        raw = manifest.read_bytes()
        report = json.loads(raw)
        row.update(manifest_sha256=hashlib.sha256(raw).hexdigest(), sealed=report.get("sealed"),
                   states={s: report[s]["status"] for s in ("hull", "structure", "equipment")})
        declared = {item["path"]: item["sha256"] for item in report.get("files", [])}
        disk = {f.relative_to(out).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
                for f in out.rglob("*") if f.is_file() and f != manifest}
        row.update(files=len(disk), declared=len(declared), exact_inventory=bool(declared) and declared == disk)
    summary[fault] = row
(args.output / "summary.json").write_text(json.dumps(summary, indent=2))
