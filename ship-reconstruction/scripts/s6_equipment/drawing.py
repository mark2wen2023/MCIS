"""Explicit synthetic equipment annotation contract; no inference from proximity."""
import hashlib,json,re,sys
from pathlib import Path
import ezdxf
import numpy as np
import trimesh as t
from trimesh.transformations import translation_matrix
from .devices import propeller,rudder,radar
SPECS={'Propeller':(propeller,('diameter','blade_count','hub_diameter','hub_length'),[1,0,0]),'Rudder':(rudder,('chord','span','thickness','axis_fraction'),[0,0,1]),'Radar':(radar,('length','width','height'),[0,0,1])}
def run(src,out):
    src=Path(src);out=Path(out);out.mkdir(exist_ok=False)
    sha=hashlib.sha256(src.read_bytes()).hexdigest(); doc=ezdxf.readfile(src); m=doc.modelspace(); rows=[]; rejected=[]; joints=[]; scene=t.Scene(base_frame='Ship_Root')
    notes=[e for e in m.query('TEXT') if e.dxf.text.startswith('EQUIPMENT ')]
    frame=[e for e in m.query('TEXT') if e.dxf.text=='FRAME X FORWARD Y PORT Z UP; METRES; INSERT IS PIVOT']
    ids=[e.dxf.text.split()[1] for e in notes if len(e.dxf.text.split())>1]
    for e in notes:
        try:
            _,id,kind,*tokens=e.dxf.text.split(); fn,keys,axis=SPECS[kind]
            if ids.count(id)!=1 or not re.fullmatch('[A-Za-z0-9_-]+',id):raise ValueError('duplicate or invalid ID')
            if doc.units!=6 or len(frame)!=1:raise ValueError('unverified coordinate frame')
            pairs=[v.split('=') for v in tokens]; p=dict(pairs)
            if len(p)!=len(pairs) or set(p)!=set(keys):raise ValueError('missing or ambiguous parameters')
            p={k:int(v) if k=='blade_count' else float(v) for k,v in p.items()}; pivot=list(e.dxf.insert)
            if not np.isfinite(pivot).all():raise ValueError('invalid pivot')
            mesh=fn(**p); node=id+'_joint';scene.graph.update(frame_from='Ship_Root',frame_to=node,matrix=translation_matrix(pivot));scene.add_geometry(mesh,node_name=id+'_mesh',geom_name=id,parent_node_name=node)
            joints.append(dict(id=id,node=node,parent='Ship_Root',axis_local=axis,pivot_parent_m=pivot,type='revolute' if kind=='Rudder' else 'continuous',limits_deg=None,control='angle_deg' if kind=='Rudder' else 'rpm',control_enabled=kind!='Rudder',parameters=p,geometry_basis='simplified_parametric_template',evidence=dict(source_sha256=sha,annotation=e.dxf.handle,frame=frame[0].dxf.handle,raw=e.dxf.text,axis_basis='synthetic_contract_default'),engineering_approved=False))
        except (ValueError,KeyError,TypeError) as exc:rejected.append(dict(handle=e.dxf.handle,raw=e.dxf.text,reason=str(exc)))
    if hashlib.sha256(src.read_bytes()).hexdigest()!=sha:raise ValueError('source changed')
    if joints:(out/'equipment.glb').write_bytes(scene.export(file_type='glb'))
    result=dict(schema_version='0.1',axes='x_forward_y_port_z_up',units='m',joints=joints,rejected=rejected,engineering_approved=False)
    (out/'articulation.json').write_text(json.dumps(result,indent=2,allow_nan=False));return result
if __name__=='__main__':run(*sys.argv[1:])
