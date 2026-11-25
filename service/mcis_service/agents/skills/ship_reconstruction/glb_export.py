"""Export research mesh as GLB with a separate face evidence manifest."""
import json
import struct
from .mesh_validation import validate_mesh

def export_glb(result):
    mesh=result['mesh']
    vertices=mesh['vertices_m']
    faces=mesh['triangles']
    evidence=result['provenance']['faces']
    if result.get('research_only') is not True or result.get('lofting_authorized') is not False:
        raise ValueError('research-only result required')
    if not vertices or not faces or len(evidence)!=len(faces):
        raise ValueError('nonempty mesh and complete face manifest required')
    if any(e.get('face_id')!=i for i,e in enumerate(evidence)):
        raise ValueError('face evidence order mismatch')
    q=validate_mesh(vertices,faces)
    if any(q[k] for k in ('invalid_faces','degenerate_faces','duplicate_faces','nonmanifold_edges','inconsistent_winding_edges')):
        raise ValueError('invalid mesh')
    # MCIS x-forward,y-transverse,z-up to glTF y-up via proper rotation.
    positions=[[x,z,-y] for x,y,z in vertices]
    try:
        raw=struct.pack('<'+'f'*(3*len(positions)),*(v for p in positions for v in p))
    except (OverflowError, struct.error) as exc:
        raise ValueError('coordinates not representable as float32') from exc
    positions=[list(p) for p in struct.iter_unpack('<fff',raw)]
    quantized=validate_mesh(positions,faces)
    if any(quantized[k] for k in ('invalid_faces','degenerate_faces','duplicate_faces','nonmanifold_edges','inconsistent_winding_edges')):
        raise ValueError('float32 serialization introduced invalid geometry')
    if len({tuple(p) for p in positions}) < len({(x,z,-y) for x,y,z in vertices}):
        raise ValueError('float32 serialization merged distinct vertices')
    indices=struct.pack('<'+'I'*(3*len(faces)),*(i for f in faces for i in f))
    binary=raw+indices
    doc={'asset':{'version':'2.0','extras':{'research_only':True,'lofting_authorized':False}},
         'scene':0,'scenes':[{'nodes':[0]}],'nodes':[{'mesh':0}],
         'meshes':[{'primitives':[{'attributes':{'POSITION':0},'indices':1,'mode':4}]}],
         'buffers':[{'byteLength':len(binary)}],
         'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':len(raw),'target':34962},{'buffer':0,'byteOffset':len(raw),'byteLength':len(indices),'target':34963}],
         'accessors':[{'bufferView':0,'componentType':5126,'count':len(vertices),'type':'VEC3','min':[min(p[i] for p in positions) for i in range(3)],'max':[max(p[i] for p in positions) for i in range(3)]},{'bufferView':1,'componentType':5125,'count':3*len(faces),'type':'SCALAR'}]}
    j=json.dumps(doc,separators=(',',':'),allow_nan=False).encode()
    j+=b' '*((-len(j))%4)
    glb=struct.pack('<4sII',b'glTF',2,12+8+len(j)+8+len(binary))+struct.pack('<I4s',len(j),b'JSON')+j+struct.pack('<I4s',len(binary),b'BIN\x00')+binary
    return glb,{'faces':evidence,'axis_mapping':'(x,y,z)->(x,z,-y)','research_only':True,'lofting_authorized':False}
