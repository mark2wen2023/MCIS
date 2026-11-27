"""八幅封存图的图纸、真值和生产程序通过独立文件入口进行比较。"""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument("output",type=Path);args=p.parse_args()
args.output.mkdir(parents=True,exist_ok=False)
base=root/"s41-frame-scope";manifest=json.loads((base/"frozen.json").read_bytes())
for name,expected in manifest.items():
    if hashlib.sha256((base/name).read_bytes()).hexdigest()!=expected:raise ValueError("冻结文件已改变")
res=[]
for f in sorted(base.glob("h*/truth.json")):
    q=json.loads(f.read_bytes());target=args.output/f.parent.name
    proc=subprocess.run([sys.executable,str(root.parent/"scripts/s41.py"),str(f.parent),"--mode","observe","--out",str(target)],capture_output=True,text=True)
    valid=False
    if (target/"evidence-graph.json").is_file():
        g=json.loads((target/"evidence-graph.json").read_bytes())
        by={n["attributes"]["instance"]:n["id"] for n in g["nodes"] if n["kind"]=="annotation"}
        arrays={a["annotation"]:a for a in g["arrays"]}
        a=arrays.get(by.get(q["note"]),{});r=arrays.get(by.get(q["rule"]),{})
        valid=(a.get("explicit_frames")==q["explicit"] and a.get("intervals")==q["ranges"] and r.get("rule")=="隔肋设"
               and r.get("phase") is None and r.get("inferred_frames")==[] and len(g["installations"])==q["placements"])
    res.append(dict(case=f.parent.name,passed=valid and proc.returncode==0,exit=proc.returncode,stderr=proc.stderr))
(args.output/"score.json").write_text(json.dumps(res,indent=2))
print(sum(x["passed"] for x in res),"/",len(res))
raise SystemExit(0 if all(x["passed"] for x in res) else 1)
