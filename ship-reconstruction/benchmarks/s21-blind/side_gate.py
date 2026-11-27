"""虚构观测缺少跨图见证时，正常交接应通过，擅自填写舷侧采用值应被退回。"""
from pathlib import Path
from copy import deepcopy
import argparse,json,sys,subprocess,tempfile,tarfile
def main():
    p=argparse.ArgumentParser();p.add_argument('repo',type=Path);p.add_argument('rev');p.add_argument('geometry',type=Path);p.add_argument('out',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    doc=json.loads(a.geometry.read_bytes());res=[]
    with tempfile.TemporaryFile() as f,tempfile.TemporaryDirectory() as tmp:
        subprocess.run(['git','-C',str(a.repo),'archive',a.rev,'ship-reconstruction'],stdout=f,check=True);f.seek(0)
        with tarfile.open(fileobj=f) as t:t.extractall(tmp,filter='data')
        for sc in ['original','unsupported_positive','unsupported_negative']:
            j=deepcopy(doc)
            if sc!='original':
                j['curves'][0]['registration_decision']=dict(status='cross_checked_sign',y_sign=1 if sc=='unsupported_positive' else -1,tolerance_m=.0001,witnesses=[])
            src=a.out/(sc+'.json');src.write_text(json.dumps(j,ensure_ascii=False))
            dest=a.out/sc;proc=subprocess.run([sys.executable,str(Path(tmp)/'ship-reconstruction/scripts/s2.py'),'geometry_data_validate',str(src),'--out',str(dest)],capture_output=True)
            result=json.loads((dest/'geometry_data_validate.json').read_bytes())
            ok=result['valid'] if sc=='original' else not result['valid'] and 'unsupported_signed_registration' in result['issues']
            res.append(dict(case=sc,exit=proc.returncode,issues=result['issues'],passed=bool(ok) and proc.returncode==(0 if sc=='original' else 4)))
    (a.out/'outcomes.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n')
    print(res)
if __name__=='__main__':main()
