"""Research-only fixed component assembly. Explicit synthetic registration only."""
import copy, hashlib, json, re
from pathlib import Path
import numpy as np
import trimesh as t
from .runtime import Runtime

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def attach(scene, cfg, entries):
    if cfg['axes'] != 'x_forward_y_up_z_starboard' or cfg['units'] != 'm': raise ValueError('frame')
    Runtime(scene,cfg)
    s=scene.copy(); c=copy.deepcopy(cfg); records=[]
    for e in entries:
        key=e['id']; p=Path(e['asset']); node='structure_'+key
        if not re.fullmatch(r'[A-Za-z0-9_-]+',key) or node in s.graph.nodes: raise ValueError('component id')
        if e['registration']!='synthetic_common_datum' or e['frame']!='x_forward_y_up_z_starboard': raise ValueError('unresolved registration')
        if digest(p)!=e['sha256']: raise ValueError('asset digest')
        m=np.asarray(e['transform'],float)
        if m.shape!=(4,4) or not np.isfinite(m).all() or not np.allclose(m[3],[0,0,0,1]) or not np.allclose(m[:3,:3].T@m[:3,:3],np.eye(3)) or not np.isclose(np.linalg.det(m[:3,:3]),1): raise ValueError('rigid transform')
        mesh=t.load_scene(p,process=False).to_geometry()
        if not len(mesh.faces) or not np.isfinite(mesh.vertices).all(): raise ValueError('geometry')
        s.add_geometry(mesh,node_name=node,geom_name=node,parent_node_name='Ship_Root',transform=m)
        records.append(dict(id=key,node=node,parent='Ship_Root',asset_sha256=e['sha256'],registration=e['registration'],transform=m.tolist(),engineering_approved=False))
    c['structures']=records;c['engineering_approved']=False
    Runtime(s,c)
    return s,c

def export(model,config,entries,dest):
    model,config,dest=map(Path,(model,config,dest));cfg=json.loads(config.read_text())
    if cfg.get('model_sha256')!=digest(model): raise ValueError('model digest')
    s,c=attach(t.load_scene(model),cfg,entries)
    dest.mkdir(exist_ok=False);p=dest/'ship.glb';p.write_bytes(s.export(file_type='glb'))
    q=t.load_scene(p);Runtime(q,c)
    for r in c['structures']:
        m,_=q.graph.get(r['node'],r['parent']);np.testing.assert_allclose(m,r['transform'],atol=1e-6)
    c['model_sha256']=digest(p);(dest/'articulation.json').write_text(json.dumps(c,indent=2));return c
