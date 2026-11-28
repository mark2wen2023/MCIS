"""Build a fictional assembly and an independent analytic world-coordinate oracle."""
import csv
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from s6_equipment.runtime import rotation_samples

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')

def build(out, encoding="local"):
    if encoding not in ("local","baked"):
        raise ValueError("origin encoding")
    out.mkdir(parents=True, exist_ok=True)
    scene = trimesh.Scene()
    offset = np.array([8.5, -3.25, 5.125])
    parent = Rotation.from_euler('zyx', [42, -23, 16], degrees=True)
    survey = np.array([13.25, -7.75, 4.5])
    # Ship XYZ to exchange axes before baking the survey origin.
    shift = survey[[0,2,1]] * [1,1,-1]
    effective = offset + (shift if encoding=="baked" else 0.)
    mat = np.eye(4)
    mat[:3, :3], mat[:3, 3] = parent.as_matrix(), effective
    scene.graph.update(frame_from='world', frame_to='mount', matrix=mat)
    scene.add_geometry(trimesh.creation.box([2, .35, .8]), node_name='fixed', parent_node_name='mount')
    items = [dict(id='fixed', title='Synthetic frame', group='structure')]
    joints, cases, expected = [], [], []
    directions = [[1,2,3], [-1,-2,-3], [0,1,0]]
    for k, direction in enumerate(directions):
        axis = np.array(direction) / np.linalg.norm(direction)
        pivot = np.array([1.2*k-.8, .6-.25*k, .3*k+.15])
        arm = np.array([.37, .29, -.41])
        node = 'joint'+str(k)
        probe = 'probe'+str(k)
        scene.graph.update(frame_from='mount',frame_to=node,matrix=trimesh.transformations.translation_matrix(pivot))
        scene.add_geometry(trimesh.creation.box([.22,.18,.44]), node_name=probe, parent_node_name=node,
                           transform=trimesh.transformations.translation_matrix(arm))
        items.append(dict(id=probe,title=probe,group='equipment'))
        joints.append(dict(id=node,node=node,parent='mount',axis_local=axis.tolist(),pivot_parent_m=pivot.tolist(),
                           type='revolute',limits_deg=[-25.,25.],control_enabled=True))
        for deg in [-18.5,0.,13.75,25.]:
            # Rodrigues directly on the witness arm, independent of quaternion sampling.
            rad = np.deg2rad(deg)
            vector = arm*np.cos(rad)+np.cross(axis,arm)*np.sin(rad)+axis*np.dot(axis,arm)*(1-np.cos(rad))
            point = effective+parent.apply(pivot+vector)
            cases.append(dict(node=probe,angle=deg,x=point[0],y=point[1],z=point[2]))
            expected.append([probe,deg,*point])
    tracks = rotation_samples(scene,dict(joints=joints))
    for item in items:
        item.update(source='synthetic',grade='synthetic',installation='demo',parameters='fictional')
    for key,mode in [('assembly','demo'),('patches','strict'),('brackets','unregistered_local_demo')]:
        model=scene if key=='assembly' else trimesh.Scene()
        if key!='assembly':
            model.add_geometry(trimesh.creation.box(),node_name='fixed')
        from coordinate_contract import contract
        origin=survey.tolist() if encoding=="local" and key=="assembly" else [0,0,0]
        extras=dict(coordinates=contract("vessel",origin),mode=mode,engineering_approved=False,
                    formal_calculation_authorized=False)
        data=trimesh.exchange.gltf.export_glb(model,tree_postprocessor=lambda j:j["asset"].update(extras=extras))
        (out/(key+'.glb')).write_bytes(data)
        write_json(out/(key+'.json'),dict(mode=mode,sha256=hashlib.sha256(data).hexdigest(),
                   items=items if key=='assembly' else items[:1],tracks=tracks if key=='assembly' else []))
    write_json(out/'oracle.json', dict(cases=cases, fixed='fixed',parent_translation=offset.tolist(),tolerance_m=.00002))
    write_json(out/'joints.json',joints)
    with (out/'analytic.csv').open('w', newline='') as f:
        w=csv.writer(f);w.writerow(['node','angle_deg','gltf_x','gltf_y','gltf_z']);w.writerows(expected)
if __name__=='__main__':
    build(Path(sys.argv[1]),sys.argv[2] if len(sys.argv)>2 else 'local')
