"""在离线环境一次复验全套独立基准。各分母单列，保留失败样本。"""
import argparse,json,os,subprocess,sys
from pathlib import Path
P=Path(__file__).resolve().parent
def main():
    p=argparse.ArgumentParser();p.add_argument('repo',type=Path);p.add_argument('commit');p.add_argument('run');a=p.parse_args()
    dest=P/'runs'/a.run
    if dest.exists():raise FileExistsError('输出已存在，请另取名称')
    repo=str(a.repo.resolve())
    cmds=[['run.py',repo,a.commit,a.run],['legacy.py',repo,a.commit,a.run],['arrays.py','run',repo,a.commit,str(P/'extra-array'),str(dest/'阵列补充')],['panel_controls.py','run',repo,a.commit,str(P/'extra-panels'),str(dest/'局部板件控制')],['extra_audit.py',a.run],['asset_controls.py',repo,a.commit,a.run]]
    errors=[]
    for cmd in cmds:
        q=subprocess.run([sys.executable,str(P/cmd[0]),*cmd[1:]],env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        if q.returncode:errors.append({'entry':cmd[0],'returncode':q.returncode})
    if errors:
        print(json.dumps({'runner_errors':errors},ensure_ascii=False));return 2
    d=lambda name:json.loads((dest/name).read_bytes())
    direct=d('summary.json');groups={'预登记压力':(direct['direct_pass'],direct['cases'])}
    for name,seq,key in [('既有结构',d('原9项/results.json')['cases'],'passed'),('阵列',d('阵列补充/results.json'),'passed'),('局部板件',d('局部板件控制/results.json'),'passed'),('工程语义',d('补充工程复核.json'),'passed'),('交接原件',d('成品独立回读/原始交接.json'),'valid'),('成品对照',d('成品独立回读/成品控制.json'),'correct')]:
        groups[name]=(sum(r[key] for r in seq),len(seq))
    print(json.dumps(groups,ensure_ascii=False));return 0 if all(a==b for a,b in groups.values()) else 1
if __name__=='__main__':raise SystemExit(main())
