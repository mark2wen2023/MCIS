"""Use the frozen geometry functions on a fictional box with analytic displacement."""
import csv
from pathlib import Path
import sys
import numpy as np
import trimesh
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from geometry import hydro, read_exchange
from coordinate_contract import contract, export_mesh

def trial(out):
    mesh=trimesh.creation.box(extents=[6,3,2])
    mesh.apply_translation([9,-2,1])
    path=out/'hydro-box.glb'
    export_mesh(path,mesh,contract('vessel',[7.,-3.,.75]),mode='research_demo')
    back=read_exchange(path)
    drafts=[.25,.5,1.,1.5,1.75]
    original=hydro(mesh,drafts)
    replay=hydro(back,drafts)
    with (out/'synthetic-hydro.csv').open('w',newline='') as stream:
        writer=csv.writer(stream)
        writer.writerow(['draft_m','analytic_m3','direct_m3','glb_m3','analytic_waterplane_m2','glb_waterplane_m2','buoyancy_center_error_m'])
        for d,a,b in zip(drafts,original,replay):
            center=np.linalg.norm(np.asarray(b['center_of_buoyancy_m'])-[9,-2,d/2])
            assert max(abs(a['volume_m3']-18*d),abs(b['volume_m3']-18*d),abs(b['waterplane_m2']-18),center)<1e-8
            writer.writerow([d,18*d,a['volume_m3'],b['volume_m3'],18,b['waterplane_m2'],center])
if __name__=='__main__':
    trial(Path(sys.argv[1]))
