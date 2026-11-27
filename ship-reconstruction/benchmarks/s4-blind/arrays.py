"""专门比较 CAD 原生矩形阵列与仅有文字数量的构件。作为补充组独立计数。"""
import argparse,json,subprocess,sys,tarfile,tempfile,hashlib
from pathlib import Path
import ezdxf
from ezdxf.math import Vec3
import numpy as np
P=Path(__file__).resolve().parent
def wr(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
def freeze(target):
    target.mkdir(exist_ok=False);m=[]
    for ix,scenario in enumerate(['native_rectangular','rotated_rectangular','rotated_mirror','text_pitch_only']):
        folder=target/scenario;folder.mkdir();d=ezdxf.new('R2013');ms=d.modelspace();b=d.blocks.new('FAB_DETAIL')
        note=b.add_text('船底纵骨 FB 90×8'+('  6 道 @ 500 mm' if ix==3 else ''),dxfattribs={'insert':(10,7),'height':.7})
        edge=b.add_lwpolyline([(0,0),(20,0)])
        lead=b.add_leader([(5,0),(8,8),(10,8)]);lead.dxf.annotation_handle=note.dxf.handle
        attrs={'row_count':1 if ix==3 else 2,'column_count':1 if ix==3 else 3,'row_spacing':19,'column_spacing':35,'rotation':(45 if ix in [1,2] else 0),'xscale':-1 if ix==2 else 1}
        e=ms.add_blockref(b.name,(111,-20),dxfattribs=attrs)
        els=list(e.multi_insert()) if ix!=3 else [e]
        xys=[list(e.matrix44().transform(note.dxf.insert)) for e in els]
        p=folder/'source.dxf';d.saveas(p);au=ezdxf.readfile(p).audit();assert not au.errors and not au.fixes
        m.append(dict(case=scenario,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),handle=note.dxf.handle,target_handle=edge.dxf.handle,leader_handle=lead.dxf.handle,anchor_wcs=xys,expected_placed_3d=0))
    wr(target/'truth.json',m)
def run(repo,rev,inputs,dest):
    dest.mkdir(parents=True,exist_ok=False);rows=[]
    with tempfile.TemporaryFile() as st,tempfile.TemporaryDirectory() as tmp:
        subprocess.run(['git','-C',str(repo),'archive',rev,'ship-reconstruction'],stdout=st,check=True);st.seek(0)
        with tarfile.open(fileobj=st) as t:t.extractall(tmp,filter='data')
        cli=Path(tmp)/'ship-reconstruction/scripts/s4_structure.py'
        for v in json.loads((inputs/'truth.json').read_bytes()):
            orig=inputs/v['case']/'source.dxf';assert hashlib.sha256(orig.read_bytes()).hexdigest()==v['sha256'];out=dest/v['case']
            proc=subprocess.run([sys.executable,str(cli),str(orig.parent),'--out',str(out)],capture_output=True)
            j=json.loads((out/'structures.json').read_bytes());a=[r for r in j.get('observations',[]) if r['source_sha256']==v['sha256'] and r['handle']==v['handle']]
            origxy=[np.array(x[:2]) for x in v['anchor_wcs']];match=sum(any(np.linalg.norm(np.asarray(r['anchor_wcs'])[:2]-xy)<1e-5 for r in a) for xy in origxy)
            ids=len({r['instance'] for r in a});n=len(origxy);assets=len(list(out.glob('*.ply')))
            rows.append(dict(case=v['case'],required=n,output=len(a),distinct_instances=ids,anchors_matched=match,inferred_assets=assets,passed=len(a)==ids==match==n and not assets,exit=proc.returncode))
    wr(dest/'results.json',rows);print(rows)
if __name__=='__main__':
    ar=argparse.ArgumentParser();sp=ar.add_subparsers(dest='cmd',required=True);f=sp.add_parser('freeze');f.add_argument('input',type=Path)
    t=sp.add_parser('run');t.add_argument('repo',type=Path);t.add_argument('rev');t.add_argument('input',type=Path);t.add_argument('output',type=Path);a=ar.parse_args()
    freeze(a.input) if a.cmd=='freeze' else run(a.repo,a.rev,a.input,a.output)
