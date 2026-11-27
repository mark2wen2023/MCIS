"""Analytic port/starboard-asymmetric hull to test the GLB exchange layer."""
import argparse
from pathlib import Path
import sys
import numpy as np
import trimesh
from replay import CHAT, git, save

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--patched',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    assert git(a.patched,'rev-parse','HEAD^')==CHAT
    sys.path.insert(0,str((a.patched/'ship-reconstruction/scripts').resolve()))
    from geometry import exchange,read_exchange,hydro,quality
    plan=[(0.,-1.),(4.,-1.),(6.,0.),(4.,2.),(0.,2.)]
    vertices=np.array([(x,y,h) for h in [0.,2.] for x,y in plan])
    faces=[]
    for i in range(1,len(plan)-1):
        faces.extend([(0,i+1,i),(5,5+i,6+i)])
    for i in range(len(plan)):
        j=(i+1)%len(plan);faces.extend([(i,j,j+5),(i,j+5,i+5)])
    hull=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    expected_center=np.array([38./15.,7./15.,.5])
    assert hull.is_volume and abs(hull.volume-30.)<1e-12
    rows=[]
    for i,offset in enumerate([[0.,0.,0.],[17.125,-6.25,3.75],[-41.5,15.25,-7.25]]):
        ship=hull.copy();ship.apply_translation(offset)
        glb=out/f'asymmetric-{i}.glb';exchange(ship).export(glb)
        raw=trimesh.load_scene(glb,process=False).to_geometry()
        # Explicit Y-up glTF transform, evaluated independently of exchange().
        expected=np.column_stack((ship.vertices[:,0],ship.vertices[:,2],-ship.vertices[:,1]))
        np.testing.assert_allclose(raw.vertices,expected,atol=0,rtol=0)
        world=read_exchange(glb)
        np.testing.assert_allclose(world.vertices,ship.vertices,atol=0,rtol=0)
        local=world.copy();local.apply_translation(-np.asarray(offset))
        q=quality(local);h=hydro(local,[1.])[0]
        err=float(np.linalg.norm(np.asarray(h['center_of_buoyancy_m'])-expected_center))
        assert q['closed_verified'] and abs(h['volume_m3']-15.)<1e-10 and abs(h['waterplane_m2']-15.)<1e-10 and err<1e-10
        rows.append(dict(origin_m=offset,port_extreme_m=2.,starboard_extreme_m=-1.,full_m3=float(local.volume),wet_m3=h['volume_m3'],waterplane_m2=h['waterplane_m2'],center_m=h['center_of_buoyancy_m'],center_error_m=err,asymmetric_sign_preserved=True,independent_gltf_transform_verified=True,production_s3_modeler_used=False))
    save(out/'asymmetric-hull-results.json',rows)
if __name__=='__main__':main()
