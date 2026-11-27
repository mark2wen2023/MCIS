"""同一块有证平板只改变注字高度，核对封闭边、局部体积、邻板歧义及单位门槛。"""
import argparse,hashlib,json,subprocess,sys,tempfile,tarfile
from pathlib import Path
import ezdxf
import trimesh
P=Path(__file__).resolve().parent
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
def make(dest):
    dest.mkdir(parents=True,exist_ok=False);manifest=[]
    for i,sc in enumerate(('compact_letters','large_letters','open_edge','adjacent_cells','ambiguous_thickness')):
        folder=dest/sc;folder.mkdir();d=ezdxf.new('R2013');d.units=4;m=d.modelspace()
        a,b,c,e=(0,0),(72,0),(72,38),(0,38)
        edges=[m.add_line(u,v).dxf.handle for u,v in [(a,b),(b,c),(c,e)]+([] if sc=='open_edge' else [(e,a)])]
        if sc=='adjacent_cells':
            for u,v in [((0,0),(0,-22)),((0,-22),(72,-22)),((72,-22),(72,0))]:m.add_line(u,v)
        raw='主甲板 t = 8' if sc=='ambiguous_thickness' else '主甲板 t = 8 mm'
        h=3. if sc=='compact_letters' else 32.
        o=m.add_text(raw,dxfattribs={'height':h,'insert':(102,55)})
        l=m.add_leader([(36,0),(85,58),(99,58)]);l.dxf.annotation_handle=o.dxf.handle
        path=folder/'panel.dxf';d.saveas(path);aud=ezdxf.readfile(path).audit();assert not aud.errors and not aud.fixes
        manifest.append(dict(case=sc,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),source_edges=edges,text=o.dxf.handle,leader=l.dxf.handle,expected_local_count=int(sc in ['compact_letters','large_letters']),expected_volume_m3=0.072*.038*.008 if sc in ['compact_letters','large_letters'] else None))
    save(dest/'truth.json',manifest)
def run(repo,rev,src,dest):
    dest.mkdir(parents=True,exist_ok=False);rows=[]
    with tempfile.TemporaryFile() as ss,tempfile.TemporaryDirectory() as tmp:
        subprocess.run(['git','-C',str(repo),'archive',rev,'ship-reconstruction'],stdout=ss,check=True);ss.seek(0)
        with tarfile.open(fileobj=ss) as t:t.extractall(tmp,filter='data')
        cli=Path(tmp)/'ship-reconstruction/scripts/s4_structure.py'
        for v in json.loads((src/'truth.json').read_bytes()):
            sc=v['case'];out=dest/sc;ret=subprocess.run([sys.executable,str(cli),str(src/sc),'--out',str(out)],capture_output=True)
            g=json.loads((out/'structures.json').read_bytes());models=g.get('local_models',[]);got_vol=None;ids=[];status=[];scope=True
            if len(models)==1:
                model=models[0];mesh=trimesh.load_mesh(out/model['asset'],process=False);got_vol=abs(mesh.volume);ids=model['contour']['boundary_handles']
                scope=model.get('ship_position_m') is None and model.get('engineering_approved') is False and mesh.is_watertight and model['source_sha256']==v['source_sha256']
            variance=got_vol-v['expected_volume_m3'] if got_vol is not None and v['expected_volume_m3'] is not None else None
            ok=len(models)==v['expected_local_count'] and scope and (variance is None or (abs(variance)<1e-10 and set(ids)==set(v['source_edges'])))
            status=[l.get('local_cell_status') for obs in g['observations'] for l in obs['leaders']]
            rows.append(dict(case=sc,geometry_return=ret.returncode,expected_local=v['expected_local_count'],actual_local=len(models),volume_m3=got_vol,volume_error_m3=variance,edges=ids,extraction_status=status,passed=bool(ok)))
    save(dest/'results.json',rows);print([(r['case'],r['actual_local'],r['passed']) for r in rows])
if __name__=='__main__':
    a=argparse.ArgumentParser();cmd=a.add_subparsers(dest='what',required=True);f=cmd.add_parser('freeze');f.add_argument('src',type=Path);r=cmd.add_parser('run');r.add_argument('repo',type=Path);r.add_argument('rev');r.add_argument('src',type=Path);r.add_argument('dest',type=Path)
    v=a.parse_args();make(v.src) if v.what=='freeze' else run(v.repo,v.rev,v.src,v.dest)
