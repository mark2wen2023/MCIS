"""运行冻结提交的正式接口并保存成功、失败、拒绝的全部结果。"""
import argparse,csv,hashlib,json,os,platform,subprocess,sys,tarfile,tempfile,time
from collections import Counter
from pathlib import Path
from score import s2
P=Path(__file__).resolve().parent
def write(p,o):p.write_text(json.dumps(o,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def fingerprints():
    expected=json.loads((P/'freeze.json').read_bytes())
    for name,h in expected.items():
        if hashlib.sha256((P/name).read_bytes()).hexdigest()!=h:raise ValueError(name)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('repository',type=Path);parser.add_argument('rev');parser.add_argument('new_run');args=parser.parse_args()
    fingerprints();dest=P/'runs'/args.new_run;dest.mkdir(parents=True,exist_ok=False)
    rev=subprocess.check_output(['git','-C',str(args.repository),'rev-parse',args.rev],text=True).strip()
    with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryFile() as pipe:
        subprocess.run(['git','-C',str(args.repository),'archive',rev,'ship-reconstruction'],stdout=pipe,check=True);pipe.seek(0)
        with tarfile.open(fileobj=pipe) as a:a.extractall(temp,filter='data')
        cases=json.loads((P/'casebook/source-truth.json').read_bytes());summ=[]
        for c in cases:
            d=dest/c['case'];d.mkdir();cli=Path(temp)/'ship-reconstruction/scripts/s2.py'
            cmd=[sys.executable,str(cli),'run',str(P/'casebook/inputs'/c['case']),'--out',str(d/'out')]
            t=time.perf_counter();proc=subprocess.run(cmd,capture_output=True,text=True,timeout=180,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'})
            w=time.perf_counter()-t;(d/'stderr-local.log').write_text(proc.stderr);(d/'stdout-local.log').write_text(proc.stdout)
            result=d/'out/geometry.json';doc=json.loads(result.read_bytes()) if result.is_file() else {}
            checks=s2(c,doc);scores=Counter(x['category'] for x in checks if x['passed']);denom=Counter(x['category'] for x in checks)
            write(d/'checks.json',checks)
            rec=dict(case=c['case'],commit=rev,exit_code=proc.returncode,wall_s=w,output=result.is_file(),all_checks_pass=bool(checks) and all(q['passed'] for q in checks),metrics={k:[scores[k],v] for k,v in denom.items()})
            write(d/'receipt.json',rec);summ.append(rec)
    fingerprints();write(dest/'summary.json',dict(commit=rev,workload='3 independently generated cases, registered before target code',platform=platform.platform(),python=sys.version.split()[0],results=summ))
    print(json.dumps(summ,ensure_ascii=False))
if __name__=='__main__':main()
