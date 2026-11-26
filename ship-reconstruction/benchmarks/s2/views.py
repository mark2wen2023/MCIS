"""同一张 CAD 图纸上三个独立视图区的追加验证，单独冻结，保持主盲测原样。"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import ezdxf
import numpy as np

P=Path(__file__).resolve().parent
def freeze(dest):
    dest.mkdir(parents=True,exist_ok=False)
    inputs=dest/'input'
    inputs.mkdir()
    d=ezdxf.new('R2013')
    ms=d.modelspace()
    truth=[]
    for index,view in enumerate(('profile','plan','body')):
        b=d.blocks.new('DETAIL_'+view)
        title={'profile':'LINES PLAN / PROFILE VIEW','plan':'WATERLINE PLAN','body':'BODY PLAN'}[view]
        b.add_text(title,dxfattribs={'height':1,'insert':(0,35)})
        origin=np.array([110*index,48*index])
        control={}
        for i,(u,v) in enumerate([(0,0),(4,0),(0,3),(7,4),(2,6)]):
            physical={'profile':[u,0,v],'plan':[u,v,0],'body':[7,u,v]}[view]
            paper=np.array([2*u+0.4*v,u+1.2*v])
            e=b.add_text(f'CONTROL P{i} X={physical[0]} Y={physical[1]} Z={physical[2]} m',dxfattribs={'height':1,'insert':paper.tolist()})
            control[e.dxf.handle]={'ship':physical,'paper':(paper+origin).tolist()}
        b.add_line((0,0),(16,8))
        ins=ms.add_blockref(b.name,origin.tolist())
        truth.append(dict(view=view,instance=ins.dxf.handle,controls=control))
    path=inputs/'views.dxf'
    d.saveas(path)
    assert not ezdxf.readfile(path).audit().errors
    truthfile=dest/'truth.json'
    truthfile.write_text(json.dumps(truth,indent=2)+'\n')
    (dest/'freeze.json').write_text(json.dumps({str(x.relative_to(dest)):hashlib.sha256(x.read_bytes()).hexdigest() for x in (path,truthfile)},indent=2)+'\n')

def run(case,cli,out):
    out.mkdir(parents=True,exist_ok=False)
    ref=json.loads((case/'freeze.json').read_bytes())
    for name,h in ref.items():
        assert hashlib.sha256((case/name).read_bytes()).hexdigest()==h
    subprocess.run([sys.executable,str(cli),'run',str(case/'input'),'--out',str(out/'geometry')],check=True,capture_output=True)
    data=json.loads((out/'geometry/geometry.json').read_bytes())
    observed={r['block_instance']:r for a in data['alignment'] for r in a['frames'] if r['status']=='verified'}
    results=[]
    for gt in json.loads((case/'truth.json').read_bytes()):
        actual=observed.get(gt['instance'])
        by_handle=gt['controls']
        if actual:
            ev={f"{gt['instance']}/{h}" for h in by_handle}
            error=max(float(np.linalg.norm(np.array(actual['paper_to_ship_m'])@[*p['paper'],1.]-p['ship'])) for p in by_handle.values())
            ok=ev==set(actual['controls']) and error<1e-7
        else:
            error=None;ok=False
        results.append(dict(view=gt['view'],qualified=bool(actual),max_m=error,passed=ok))
    (out/'result.json').write_text(json.dumps(results,indent=2)+'\n')
    print(results)
if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='cmd',required=True);f=sub.add_parser('freeze');f.add_argument('case',type=Path)
    r=sub.add_parser('run');r.add_argument('case',type=Path);r.add_argument('cli',type=Path);r.add_argument('out',type=Path)
    a=p.parse_args();freeze(a.case) if a.cmd=='freeze' else run(a.case,a.cli,a.out)
