"""在冻结评分之外，单独报告冲突提示、候选身份和跨版次误合并。"""
import argparse,json,csv
from pathlib import Path
P=Path(__file__).resolve().parent
def main():
    par=argparse.ArgumentParser();par.add_argument('run');d=P/'runs'/par.parse_args().run
    tests=[]
    for n in (20,22,25,30,31,48):
        g=json.loads((d/f'S{n:02}'/'out/structures.json').read_bytes());obs=g.get('observations',[]);ids=g.get('identity_candidates',[]);conf=g.get('conflicts',[]);oc=g.get('observation_conflicts',[])
        def signal(o):
            if isinstance(o,dict):return any('conflict' in str(k).lower() and bool(v) or k in ('status','modeling_status') and ('conflict' in str(v).lower() or '矛盾' in str(v)) or signal(v) for k,v in o.items())
            if isinstance(o,list):return any(signal(x) for x in o)
            return False
        flagged=signal(obs) or signal(ids) or bool(conf) or bool(oc)
        if n==20:kind='同图同目标冲突有明确标记';good=flagged
        elif n==22:kind='重复同值未报为矛盾';good=not flagged
        elif n==25:kind='相交处的双目标保留候选';good=any(len(l.get('target_instances',[]))==2 for o in obs for l in o.get('leaders',[]))
        elif n==30:kind='同版双图同件身份有候选记录';good=bool(ids)
        elif n==31:kind='跨版异值同号件有冲突或明确版次待核';good=flagged or any('revision' in str(i).lower() or '版次' in str(i) for i in ids)
        else:kind='悬空引线没有绑定附近原构件';good=bool(obs) and all(not l.get('target_instances') for o in obs for l in o.get('leaders',[]))
        tests.append(dict(case=f'S{n:02}',supplement=kind,observed_explicit_flag=flagged,n_candidates=len(ids),passed=good))
    (d/'补充工程复核.json').write_text(json.dumps(tests,ensure_ascii=False,indent=2)+'\n');print([(r['case'],r['passed']) for r in tests])
if __name__=='__main__':main()
