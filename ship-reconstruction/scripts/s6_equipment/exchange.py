"""Explicit S3 exchange frame bridge; no registration inferred."""
import hashlib,json,tempfile
from pathlib import Path
import numpy as np
import trimesh as t
from .assembly import assemble
SHIP_TO_GLTF=np.array([[1,0,0,0],[0,0,1,0],[0,-1,0,0],[0,0,0,1]],float)
def bridge(hull,equipment,config,out,*,frame,registration):
    if frame!='s3_gltf_y_up' or registration!='synthetic_common_datum':raise ValueError('registration not established')
    hull=Path(hull);out=Path(out)
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)/'hull.glb';m=t.load_scene(hull,process=False).to_geometry();m.apply_transform(SHIP_TO_GLTF.T);m.export(p)
        cfg=assemble(p,equipment,config,out)
        cfg['input_sha256']['hull']=hashlib.sha256(hull.read_bytes()).hexdigest()
        cfg['hull_input_frame']=frame;cfg['assembly_basis']=registration;cfg['output_frame']='ship_axes_z_up_not_standard_gltf_y_up'
        (out/'articulation.json').write_text(json.dumps(cfg,indent=2))
        return cfg
