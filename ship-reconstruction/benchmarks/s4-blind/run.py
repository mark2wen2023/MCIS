"""从固定 Git 提交隔离运行结构观察入口，对所有 DXF 执行同一评分。"""
import argparse,concurrent.futures,csv,hashlib,json,os,platform,subprocess,sys,tarfile,tempfile,time
from collections import Counter
from pathlib import Path
from score import chk
P=Path(__file__).resolve().parent
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def verify():
    d=json.loads((P/'freeze.json').read_bytes())
    for n,v in d.items():
        if hashlib.sha256((P/n).read_bytes()).hexdigest()!=v:raise ValueError(n)
def table(p,rows):
    if not rows:return
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
def main():
    a=argparse.ArgumentParser();a.add_argument('repo',type=Path);a.add_argument('revision');a.add_argument('run');args=a.parse_args()
    new=P/'runs'/args.run;new.mkdir(parents=True,exist_ok=True)
    if any(z.name not in ('原9项','阵列补充','局部板件控制') for z in new.iterdir()):raise FileExistsError('已有压力工况输出，使用新目录')
    verify()
    rev=subprocess.check_output(['git','-C',str(args.repo),'rev-parse',args.revision],text=True).strip()
    truth=json.loads((P/'frozen/truth.json').read_bytes());environment={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','VECLIB_MAXIMUM_THREADS':'1'}
    with tempfile.TemporaryDirectory() as tmp,tempfile.TemporaryFile() as stream:
        subprocess.run(['git','-C',str(args.repo),'archive',rev,'ship-reconstruction'],stdout=stream,check=True);stream.seek(0)
        with tarfile.open(fileobj=stream) as t:t.extractall(tmp,filter='data')
        cli=Path(tmp)/'ship-reconstruction/scripts/s4_structure.py'
        def one(c):
            case=c['case'];folder=P/'frozen/inputs'/case;r=new/case;r.mkdir();out=r/'out';clock=time.perf_counter()
            try:
                proc=subprocess.run([sys.executable,str(cli),str(folder),'--out',str(out)],capture_output=True,text=True,env=environment,timeout=120)
                rc=proc.returncode;stdout=proc.stdout;stderr=proc.stderr
            except subprocess.TimeoutExpired: rc=124;stdout='';stderr='timeout'
            for name,txt in [('stdout.log',stdout),('stderr.log',stderr)]:
                (r/name).write_text(txt.replace(tmp,'<frozen-code>').replace(str(P),'benchmarks/s4-blind'))
            g=out/'structures.json';data=json.loads(g.read_bytes()) if g.is_file() else {}
            try:
                checks=chk(c,data,folder)
            except Exception as e:
                checks=[dict(metric='scorer_exception',source=case,passed=False,actual=str(e))]
            t=time.perf_counter()-clock;fails=sorted({a['metric'] for a in checks if not a['passed']})
            receipt=dict(case=case,description=c['scenario'],code_exit=rc,elapsed_s=t,output=g.is_file(),observation_count=len(data.get('observations',[])),dedicated_full_pass=bool(checks) and all(v['passed'] for v in checks),failed_metrics=','.join(fails),passed=sum(v['passed'] for v in checks),checks=len(checks))
            save(r/'checks.json',checks);save(r/'receipt.json',receipt)
            return receipt,checks
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:items=list(pool.map(one,truth))
    verify();cases=[r for r,checks in items];den=Counter();num=Counter()
    for _,checks in items:
        for c in checks:den[c['metric']]+=1;num[c['metric']]+=c['passed']
    metrics=[dict(metric=k,passes=num[k],expected=n) for k,n in den.items()]
    summary=dict(commit=rev,python=platform.python_version(),platform=platform.platform(),protocol_sha256=hashlib.sha256((P/'freeze.json').read_bytes()).hexdigest(),cases=len(items),files=sum(len(c['files']) for c in truth),direct_pass=sum(c['dedicated_full_pass'] for c in cases),json_written=sum(c['output'] for c in cases),rc_counts=dict(Counter(c['code_exit'] for c in cases)),metrics=metrics)
    save(new/'summary.json',summary);table(new/'逐案.csv',cases);table(new/'逐指标.csv',metrics);print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
