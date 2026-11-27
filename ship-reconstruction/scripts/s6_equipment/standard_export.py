"""Convert every local basis, preserving graph and joint semantics."""
import copy,json,hashlib
from pathlib import Path
import numpy as np
import trimesh as t
from .exchange import SHIP_TO_GLTF as R
from .runtime import Runtime

def convert(scene,cfg):
    if cfg['axes']!='x_forward_y_port_z_up' or cfg['units']!='m': raise ValueError('input frame')
    Runtime(scene,cfg)
    out=t.Scene(base_frame=scene.graph.base_frame)
    for name,mesh in scene.geometry.items():
        out.geometry[name]=mesh.copy();out.geometry[name].apply_transform(R)
    for parent,child,data in scene.graph.to_edgelist():
        d=copy.deepcopy(data);d['matrix']=R@np.asarray(d['matrix'])@R.T
        out.graph.update(frame_from=parent,frame_to=child,**d)
    c=copy.deepcopy(cfg)
    for j in c['joints']:
        for k in ('axis_local','pivot_parent_m'):j[k]=(R[:3,:3]@j[k]).tolist()
    c.update(axes='x_forward_y_up_z_starboard',output_frame='s3_gltf_y_up',engineering_approved=False)
    Runtime(out,c)
    return out,c

def export(source,config,dest):
    source,config,dest=map(Path,(source,config,dest));s,c=convert(t.load_scene(source),json.loads(config.read_text()))
    dest.mkdir(exist_ok=False);p=dest/'ship.glb';p.write_bytes(s.export(file_type='glb'))
    Runtime(t.load_scene(p),c)
    c['model_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    (dest/'articulation.json').write_text(json.dumps(c,indent=2));return c
