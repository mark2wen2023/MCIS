"""重跑原9案的字节级相同DXF，独立于48组图纸识别压力样本。"""
import argparse,concurrent.futures,hashlib,json,os,subprocess,sys,tarfile,tempfile
from pathlib import Path
P=Path(__file__).resolve().parent
def main():
    a=argparse.ArgumentParser();a.add_argument('repo',type=Path);a.add_argument('rev');a.add_argument('run');arg=a.parse_args();mrk=P/'runs'/arg.run/'原9项';mrk.mkdir(parents=True,exist_ok=False)
    truth=json.loads((P/'legacy/truth.json').read_bytes());rev=subprocess.check_output(['git','-C',str(arg.repo),'rev-parse',arg.rev],text=True).strip()
    with tempfile.TemporaryFile() as f,tempfile.TemporaryDirectory() as tmp:
        subprocess.run(['git','-C',str(arg.repo),'archive',rev,'ship-reconstruction'],stdout=f,check=True);f.seek(0)
        with tarfile.open(fileobj=f) as t:t.extractall(tmp,filter='data')
        cli=Path(tmp)/'ship-reconstruction/scripts/s4_structure.py'
        def one(v):
            folder=P/'legacy/inputs'/v['id'];dest=mrk/v['id']
            for n,h in v['fingerprints'].items():assert hashlib.sha256((folder/n).read_bytes()).hexdigest()==h
            proc=subprocess.run([sys.executable,str(cli),str(folder),'--out',str(dest)],capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'})
            path=dest/'structures.json';data=json.loads(path.read_bytes()) if path.is_file() else {};rows=data.get('components',[]);w=v['expected_geometry'];ply=list(dest.glob('*.ply'))
            passed=len(ply)==int(w) and data.get('engineering_approved') is False and (all(r['geometry_status']=='research_geometry_verified' for r in rows) and bool(rows))==w and proc.returncode==(0 if w else 4)
            if w:passed=passed and abs(rows[0]['dimension_m']-.18)<1e-7 and 'hull_attachment' in rows[0].get('unknowns',[])
            return dict(id=v['id'],case=v['name'],expected=w,verified_asset_count=len(ply),exit=proc.returncode,issues=[r['issues'] for r in rows],passed=passed)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:records=list(pool.map(one,truth))
    (mrk/'results.json').write_text(json.dumps(dict(commit=rev,cases=records),ensure_ascii=False,indent=2)+'\n');print(sum(x['passed'] for x in records),'/',len(records))
if __name__=='__main__':main()
