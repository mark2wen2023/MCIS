"""重跑冻结图纸；将测量数据写入独立的新目录。"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from score import assess, read_mesh, table, selfcheck

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.out.resolve()
    if root.is_relative_to(HERE.parent):parser.error("输出须位于安装目录之外")
    root.mkdir(parents=True,exist_ok=False)
    frozen=json.loads((HERE/"frozen.sha256.json").read_bytes())
    for name,digest in frozen.items():
        if hashlib.sha256((HERE/name).read_bytes()).hexdigest()!=digest:
            raise ValueError("冻结基准指纹变化 "+name)
    selfcheck()
    results=[]
    for name in ("A","B"):
        dest=root/name
        start=time.monotonic()
        cmd=[sys.executable,str(HERE.parent/"scripts/reconstruct.py"),str(HERE/"inputs"/name),"--out",str(dest)]
        process=subprocess.run(cmd,check=False,capture_output=True,text=True)
        seconds=time.monotonic()-start
        record={"case":name,"exit":process.returncode,"human_interventions":0,"wall_seconds":seconds}
        report=json.loads((dest/"report.json").read_bytes())
        record.update(status=report["status"],component_traceability=None,component_denominator=0)
        if "displacement" in report["assets"]:
            mesh=read_mesh(dest/report["assets"]["displacement"]["path"])
            truth=json.loads((HERE/"truth"/(name+".json")).read_bytes())
            scored=assess(mesh,truth)
            record.update(watertight=bool(mesh.is_watertight),geometric_scores=scored["metrics"],
                          table=table(dest/"offsets.json",truth))
            (dest/"independent-measurements.json").write_text(json.dumps(scored,indent=2))
        results.append(record)
    (root/"operational-metrics.json").write_text(json.dumps(results,indent=2))
    # A bounded result and a passing geometric acceptance have separate meanings.
    return 0 if all(r.get("table",{}).get("all_match") and r.get("watertight") and
                    all(m["passed"] for m in r["geometric_scores"].values()) for r in results) else 4

if __name__=="__main__":raise SystemExit(main())
