"""在三份只读基准以外构造删证实验，仅检验缺少坐标见证时的保守行为。"""
import argparse,hashlib,json,os,shutil,subprocess,sys,tarfile,tempfile
from pathlib import Path
import ezdxf
P=Path(__file__).resolve().parent
def write(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def make(target):
    target.mkdir(parents=True,exist_ok=False);m=[]
    for case in 'ABC':
        folder=target/case;folder.mkdir();source=P/'casebook/inputs'/case/'lines.dxf';doc=ezdxf.readfile(source);removed=[]
        for b in doc.blocks:
            for ent in list(b.query('TEXT')):
                if ent.dxf.text.startswith('CONTROL '):
                    removed.append(ent.dxf.handle);b.delete_entity(ent)
        out=folder/'lines.dxf';doc.saveas(out);audit=ezdxf.readfile(out).audit()
        if audit.errors or audit.fixes:raise ValueError(case)
        m.append(dict(case=case,original_sha256=sha(source),ablated_sha256=sha(out),removed_control_handles=removed,expected_verified_frames=0,expected_asserted_3d=0))
    write(target/'manifest.json',m)
def run(repo,rev,fixtures,result):
    result.mkdir(parents=True,exist_ok=False);rows=[];full=subprocess.check_output(['git','-C',str(repo),'rev-parse',rev],text=True).strip()
    with tempfile.TemporaryDirectory() as temp,tempfile.TemporaryFile() as f:
        subprocess.run(['git','-C',str(repo),'archive',full,'ship-reconstruction'],stdout=f,check=True);f.seek(0)
        with tarfile.open(fileobj=f) as t:t.extractall(temp,filter='data')
        for ref in json.loads((fixtures/'manifest.json').read_bytes()):
            case=ref['case'];p=fixtures/case/'lines.dxf'
            if sha(p)!=ref['ablated_sha256']:raise ValueError(case)
            out=result/case;cmd=[sys.executable,str(Path(temp)/'ship-reconstruction/scripts/s2.py'),'run',str(p),'--out',str(out)]
            ret=subprocess.run(cmd,capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
            j=json.loads((out/'geometry.json').read_bytes());verified=sum(fr.get('status')=='verified' for d in j.get('alignment',[]) for fr in d['frames']);promoted=sum(bool(c.get('ship_coordinates')) for c in j.get('curves',[]))
            rows.append(dict(case=case,commit=full,exit=ret.returncode,removed_controls=len(ref['removed_control_handles']),verified_frames=verified,curves_with_confirmed_xyz=promoted,curve_count=len(j['curves']),correct_abstention=ret.returncode==0 and verified==0 and promoted==0))
    write(result/'summary.json',rows);print(rows)
if __name__=='__main__':
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='cmd',required=True);mk=sub.add_parser('make');mk.add_argument('folder',type=Path)
    r=sub.add_parser('run');r.add_argument('repo',type=Path);r.add_argument('rev');r.add_argument('folder',type=Path);r.add_argument('output',type=Path)
    a=ap.parse_args();make(a.folder) if a.cmd=='make' else run(a.repo,a.rev,a.folder,a.output)
