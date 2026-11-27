"""Research assembly in explicit common ship-axis metre coordinates."""
import json, math, hashlib
from pathlib import Path
import numpy as np
import trimesh as t
from trimesh.transformations import rotation_matrix, translation_matrix

def assemble(hull, equipment, config, out):
    out=Path(out); cfg=json.loads(Path(config).read_text())
    if cfg['axes']!='x_forward_y_port_z_up' or cfg['units']!='m': raise ValueError('frame')
    s=t.load(equipment,force='scene'); h=t.load(hull,force='scene')
    if 'Hull_fixed' in s.graph.nodes: raise ValueError('collision')
    # Bake only the fixed hull, preserving equipment hierarchy.
    s.add_geometry(h.to_geometry(),node_name='Hull_fixed',geom_name='Hull_fixed',parent_node_name='Ship_Root')
    for j in cfg['joints']:
        if s.graph.transforms.parents[j['node']]!=j['parent']: raise ValueError('parent mismatch')
        m,_=s.graph.get(j['node'],j['parent'])
        if not np.allclose(m,translation_matrix(j['pivot_parent_m'])): raise ValueError('pivot mismatch')
    out.mkdir(exist_ok=False); (out/'ship.glb').write_bytes(s.export(file_type='glb'))
    cfg['assembly_basis']='caller_declared_common_frame_research_only';cfg['engineering_approved']=False
    cfg['input_sha256']={k:hashlib.sha256(Path(p).read_bytes()).hexdigest() for k,p in [('hull',hull),('equipment',equipment),('config',config)]}
    (out/'articulation.json').write_text(json.dumps(cfg,indent=2));return cfg

def command(scene,j,value,seconds=0):
    if not j.get('control_enabled',False):raise ValueError('disabled joint')
    if not math.isfinite(value) or not math.isfinite(seconds) or seconds<0:raise ValueError('invalid command')
    if j['type']=='continuous': angle=value*6*seconds
    elif j['type']=='revolute' and j['limits_deg'] and j['limits_deg'][0]<=value<=j['limits_deg'][1]:angle=value
    else:raise ValueError('unsupported or out of limits')
    if not math.isfinite(angle):raise ValueError('overflow')
    scene.graph.update(frame_from=j['parent'],frame_to=j['node'],matrix=translation_matrix(j['pivot_parent_m'])@rotation_matrix(math.radians(angle%360),j['axis_local']))
