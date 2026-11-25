import json
import struct
import pytest
from mcis_service.agents.skills.ship_reconstruction.glb_export import export_glb
from mcis_service.agents.skills.ship_reconstruction.asset_integrity import bind_asset

def triangle(x):
    return dict(research_only=True,lofting_authorized=False,mesh=dict(vertices_m=[[x,0,0],[x,1,0],[x,0,1]],triangles=[[0,1,2]]),provenance=dict(faces=[dict(face_id=0,sources=[dict(document_id='synthetic',locator='face')])]))

@pytest.mark.parametrize('x,origin',[(1e-13,16384.),(1.,2.**54)])
def test_world_budget(x,origin):
    with pytest.raises(ValueError,match='precision|roundtrip'):
        export_glb(triangle(x),local_origin_m=[origin,0,0],max_vertex_error_m=0)

@pytest.mark.parametrize('a,b',[(None,None),('unknown','unknown'),([1,0,0],[True,0,0])])
def test_origin_type(a,b):
    glb,side=export_glb(triangle(0))
    n=struct.unpack_from('<I',glb,12)[0]
    doc=json.loads(glb[20:20+n])
    doc['asset']['extras']['mcis_origin_m']=a
    raw=json.dumps(doc,separators=(',',':')).encode()
    raw+=b' '*(-len(raw)%4)
    body=struct.pack('<I4s',len(raw),b'JSON')+raw+glb[20+n:]
    changed=struct.pack('<4sII',b'glTF',2,12+len(body))+body
    side['mcis_origin_m']=b
    with pytest.raises(ValueError,match='origin'):
        bind_asset(changed,side,algorithm_version='synthetic')
