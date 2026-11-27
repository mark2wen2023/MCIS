"""Move drawing origins in CAD, then verify five repeated GLB exchange round trips."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import ezdxf
import numpy as np
import trimesh
from replay import CHAT, UPSTREAM, cli, git, save, sha

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('original','patched','upstream','output'):
        p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    if git(a.original,'rev-parse','HEAD')!=CHAT or git(a.patched,'rev-parse','HEAD^')!=CHAT or git(a.upstream,'rev-parse','HEAD')!=UPSTREAM:
        raise ValueError('wrong checkout')
    src=a.upstream/'ship-reconstruction/examples/s21/A/input.dxf'
    sys.path.insert(0,str((a.patched/'ship-reconstruction/scripts').resolve()))
    from geometry import exchange,read_exchange,hydro
    truth=np.asarray([[0.,-1.5,0.],[6.,1.5,2.]])
    rows=[]
    for i,offset in enumerate([(0.,0.),(211.25,-94.5),(-837.5,412.75)]):
        target=out/f'drawing-{i}.dxf'
        d=ezdxf.readfile(src)
        for e in d.modelspace():e.translate(*offset,0.)
        d.saveas(target)
        for flavor,repo in [('original',a.original),('patched',a.patched)]:
            folder=out/f'{flavor}-{i}'
            code=cli([sys.executable,repo/'ship-reconstruction/scripts/s3_run.py',a.upstream,target,folder],folder.with_suffix('.log'))
            report=json.loads((folder/'report.json').read_bytes())
            assert code==0 and report['status']=='research_mesh' and report['source_sha256']==sha(target)
            native=folder/'research.glb'
            m=trimesh.load_scene(native,process=False).to_geometry() if flavor=='original' else read_exchange(native)
            np.testing.assert_allclose(m.bounds,truth,rtol=0,atol=1e-12)
            h=hydro(m,[1.])[0];assert abs(h['volume_m3']-18.)<1e-12
            rec=dict(version=flavor,paper_offset=offset,admission=report['mesh_report']['admission'],engineering_approved=report['engineering_approved'],correct_frame_readback_m=m.bounds.tolist(),wet_volume_m3=h['volume_m3'])
            if flavor=='patched':
                v=m.vertices.copy();worst=0.
                for repeat in range(1,6):
                    f=folder/f'cycle-{repeat}.glb';exchange(m).export(f);m=read_exchange(f)
                    err=float(np.linalg.norm(m.vertices-v,axis=1).max());worst=max(worst,err)
                    np.testing.assert_allclose(m.bounds,truth,rtol=0,atol=1e-12)
                assert worst==0
                rec.update(roundtrips=5,maximum_incremental_drift_m=worst)
            rows.append(rec)
    save(out/'paper-origin-results.json',rows)
if __name__=='__main__':main()
