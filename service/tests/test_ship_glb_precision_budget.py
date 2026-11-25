import json
import struct
import pytest
from mcis_service.agents.skills.ship_reconstruction.glb_export import export_glb
from mcis_service.agents.skills.ship_reconstruction.asset_integrity import bind_asset

def payload(origin=0):
    return dict(research_only=True,lofting_authorized=False,
        mesh=dict(vertices_m=[[origin,0,0],[origin+.001,0,0],[origin,1,0],[origin+.001,1,0]],triangles=[[0,1,2],[1,3,2]]),
        provenance=dict(faces=[dict(face_id=i,sources=[dict(document_id='synthetic',locator='face')],cell_review=dict(review='accepted',document_id='synthetic',locator='cell')) for i in range(2)]))

def test_area_budget():
    with pytest.raises(ValueError,match='precision budget'):
        export_glb(payload(16384),max_area_relative_error=.01)

def test_edge_budget():
    with pytest.raises(ValueError,match='precision budget'):
        export_glb(payload(16384),max_edge_relative_error=.01)

def test_local_origin():
    glb,evidence=export_glb(payload(32768),local_origin_m=[32768,0,0],max_area_relative_error=.01,max_vertex_error_m=1e-6,max_edge_relative_error=.01)
    n=struct.unpack_from('<I',glb,12)[0]
    doc=json.loads(glb[20:20+n])
    assert doc['asset']['extras']['mcis_origin_m']==evidence['mcis_origin_m']==[32768,0,0]
    assert evidence['precision']['max_edge_relative_error']<1e-6
    assert not bind_asset(glb,evidence,algorithm_version='synthetic')['lofting_authorized']
    evidence['mcis_origin_m']=[0,0,0]
    with pytest.raises(ValueError,match='origin'):
        bind_asset(glb,evidence,algorithm_version='synthetic')

@pytest.mark.parametrize('kind',['bool_id','null_face','pending_cell'])
def test_invalid_face(kind):
    r=payload()
    if kind=='bool_id':
        r['provenance']['faces'][0]['face_id']=False
    elif kind=='null_face':
        r['provenance']['faces'][0]=None
    else:
        r['provenance']['faces'][0]['cell_review']['review']='pending'
    with pytest.raises(ValueError):
        export_glb(r)

def test_conflicting_authorization():
    glb,evidence=export_glb(payload())
    n=struct.unpack_from('<I',glb,12)[0]
    doc=json.loads(glb[20:20+n])
    doc['asset']['extras']['lofting_authorized']=True
    raw=json.dumps(doc,separators=(',',':')).encode()
    raw+=b' '*(-len(raw)%4)
    body=struct.pack('<I4s',len(raw),b'JSON')+raw+glb[20+n:]
    changed=struct.pack('<4sII',b'glTF',2,12+len(body))+body
    with pytest.raises(ValueError,match='authorization'):
        bind_asset(changed,evidence,algorithm_version='synthetic')

def test_distinct_vertices_normal_flip():
    r=payload()
    base=2**23
    r['mesh']=dict(vertices_m=[[base,base,0],[base+1.49,base+.49,0],[base+2.49,base+.51,0]],triangles=[[0,1,2]])
    r['provenance']['faces']=r['provenance']['faces'][:1]
    with pytest.raises(ValueError,match='reversed face normal'):
        export_glb(r)
