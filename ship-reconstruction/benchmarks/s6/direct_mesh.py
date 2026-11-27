"""Compare S3's actual in-memory mesh with GLB files read by the exchange consumer."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
from replay import CHAT, UPSTREAM, git, save

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('original','upstream','cli-results','output'):
        p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    assert git(a.original,'rev-parse','HEAD')==CHAT and git(a.upstream,'rev-parse','HEAD')==UPSTREAM
    sys.path.insert(0,str((a.original/'ship-reconstruction/scripts').resolve()))
    from s3_s21 import reconstruct
    from s3_run import verify_handoff
    from geometry import hydro, quality, read_exchange
    summaries=[]
    for name in ('A','B'):
        run=a.cli_results/('original-'+name+'-full');raw=run/'extract/geometry.json'
        c=out/('upstream-check-'+name)
        result=subprocess.run([sys.executable,a.upstream/'ship-reconstruction/scripts/s2.py','geometry_data_validate',raw,'--out',c],capture_output=True,text=True)
        assert result.returncode==0
        verified=json.loads((c/'geometry_data_validate.json').read_bytes())
        source=a.upstream/'ship-reconstruction/examples/s21'/name/'input.dxf'
        g=json.loads(raw.read_bytes());verify_handoff(g,verified,hashlib.sha256(source.read_bytes()).hexdigest())
        direct,report=reconstruct(g,upstream_check=lambda _:verified)
        meshes={'direct_mesh':direct}
        for v in ('original','patched'):
            meshes[v+'_GLB']=read_exchange(a.cli_results/(v+'-'+name+'-full')/'research.glb')
        for route,m in meshes.items():
            h=hydro(m,[1.])[0];error=float(np.linalg.norm(m.vertices-direct.vertices,axis=1).max())
            if route=='original_GLB':assert error>1. and abs(h['volume_m3']-30.)<1e-12
            else:assert error==0. and abs(h['volume_m3']-18.)<1e-12 and abs(h['waterplane_m2']-18.)<1e-12
            summaries.append(dict(case=name,frame='vessel' if report['absolute_frame'] else 'local_only',route=route,bounds_m=m.bounds.tolist(),direct_vertex_error_m=error,closed=quality(m)['closed_verified'],wet_m3=h['volume_m3'],waterplane_m2=h['waterplane_m2'],center_m=h['center_of_buoyancy_m']))
    save(out/'direct-mesh-results.json',summaries)
if __name__=='__main__':main()
