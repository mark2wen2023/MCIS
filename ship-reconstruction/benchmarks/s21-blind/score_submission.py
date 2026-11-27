"""对给定 S3 黑箱交付的留出采样与静水力输出评分，或导出不含真值的查询点。"""
import argparse,copy,json,sys
from pathlib import Path
from score import s3
P=Path(__file__).resolve().parent

def main():
    arg=argparse.ArgumentParser();arg.add_argument('command',choices=['queries','score','selfcheck']);arg.add_argument('destination',type=Path);arg.add_argument('--predictions',type=Path)
    a=arg.parse_args()
    if a.destination.exists():raise FileExistsError(a.destination)
    truth=json.loads((P/'casebook/geometry-truth.json').read_bytes())
    if a.command=='queries':
        obj=[dict(case=t['case'],holdout=[{k:r[k] for k in ('id','x_m','z_m','side')} for r in t['holdout']],areas=[{k:r[k] for k in ('id','x_m','draft_m')} for r in t['areas']],hydro=[{'draft_m':r['draft_m']} for r in t['hydro']]) for t in truth]
    elif a.command=='score':
        obj=[]
        if a.predictions is None:arg.error('需要 --predictions')
        pred=json.loads(a.predictions.read_bytes())
        for t in truth:
            matches=[v for v in pred if v.get('case')==t['case']]
            obj.append(dict(case=t['case'],result=s3(truth,matches[0]) if len(matches)==1 else dict(complete=False,passed=False)))
    else:
        obj=[]
        for t in truth:
            a1=s3(truth,t);wrong=copy.deepcopy(t)
            for p in wrong['holdout']:p['y_m']+=.2*t['nominal_beam_m']
            b=s3(truth,wrong)
            short=copy.deepcopy(t);short['holdout'].pop()
            c=s3(truth,short)
            result=a1['passed'] and not b['passed'] and not c['complete']
            obj.append(dict(case=t['case'],test_of_scoring_only=True,correct_oracle_accept=a1['passed'],biased_oracle_reject=not b['passed'],incomplete_reject=not c['complete'],all_as_expected=result))
            if not result:raise AssertionError(t['case'])
    a.destination.write_text(json.dumps(obj,ensure_ascii=False,allow_nan=False,indent=2)+'\n')
if __name__=='__main__':main()
