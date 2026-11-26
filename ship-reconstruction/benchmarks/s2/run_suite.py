"""用归档提交、只读原件运行全部工况；缺结果、异常退出与未实现输出均保留。"""
import argparse,concurrent.futures,csv,hashlib,json,os,platform,subprocess,sys,tarfile,tempfile,time
from pathlib import Path
from score import results
P=Path(__file__).resolve().parent
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def js(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def main():
 par=argparse.ArgumentParser();par.add_argument('repo',type=Path);par.add_argument('rev');par.add_argument('run');a=par.parse_args();repo=a.repo.resolve();dat=P/'fixture';dest=P/'runs'/a.run;dest.mkdir(parents=True,exist_ok=False)
 rev=subprocess.check_output(['git','-C',str(repo),'rev-parse',a.rev],text=True).strip();impl=dest/'code';impl.mkdir()
 with tempfile.TemporaryFile() as f:
  subprocess.run(['git','-C',str(repo),'archive',rev,'ship-reconstruction'],stdout=f,check=True);f.seek(0)
  with tarfile.open(fileobj=f) as t:t.extractall(impl,filter='data')
 cli=impl/'ship-reconstruction/scripts/s2.py';assert cli.is_file()
 frozen=json.loads((P/'s2-freeze.json').read_bytes());truth=json.loads((dat/'truth.json').read_bytes())
 def verify():
  for n,h in frozen.items():assert sha(P/n)==h,n
 verify()
 def one(case):
  root=dest/case['id'];root.mkdir();out=root/'out';cmd=[sys.executable,str(cli),'run',str(dat/'inputs'/case['id']),'--out',str(out)]
  start=time.perf_counter()
  try:
   p=subprocess.run(cmd,capture_output=True,text=True,timeout=90,cwd=root,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'});rc=p.returncode;stdout,stderr=p.stdout,p.stderr
  except subprocess.TimeoutExpired:rc=124;stdout='';stderr='timeout'
  elapsed=time.perf_counter()-start;(root/'stdout.log').write_text(stdout);(root/'stderr.log').write_text(stderr);g=out/'geometry.json'
  try:j=json.loads(g.read_bytes()) if g.is_file() else None;checks=results(case,j)
  except Exception as e:checks=[dict(measure='scorer_contract',expected='supported JSON',observed=repr(e),pass_check=False,source=case['id'],detail='')]
  js(root/'checks.json',checks);row={'id':case['id'],'scenario':case['scenario'],'exit':rc,'wall_seconds':round(elapsed,5),'geometry_present':g.is_file(),'checks':len(checks),'passes':sum(x['pass_check'] for x in checks),'preregistered_outcome':all(x['pass_check'] for x in checks),'failed_metrics':','.join(sorted({x['measure'] for x in checks if not x['pass_check']}))};js(root/'receipt.json',row);return row
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(one,truth))
 verify();js(dest/'summary.json',{'commit':rev,'protocol_sha256':sha(P/'s2-freeze.json'),'cli_sha256':sha(cli),'python':sys.version.split()[0],'env':platform.platform(),'cases':rows})
 with (dest/'逐案结果.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
 print(len(rows),sum(r['geometry_present'] for r in rows),sum(r['preregistered_outcome'] for r in rows))
if __name__=='__main__':main()
