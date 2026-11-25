"""Export research mesh as GLB with a separate face evidence manifest."""
import json
import math
import struct
from .mesh_validation import validate_mesh
from .geometry_provenance import valid_reference

def _normal(vertices, face):
    a,b,c=(vertices[i] for i in face)
    u=[b[k]-a[k] for k in range(3)]
    v=[c[k]-a[k] for k in range(3)]
    return [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]

def export_glb(result, *, local_origin_m=None, max_vertex_error_m=None, max_area_relative_error=None, max_edge_relative_error=None):
    """Optional explicit research precision budgets; no signed engineering tolerances."""
    for limit in (max_vertex_error_m,max_area_relative_error,max_edge_relative_error):
        if limit is not None and (isinstance(limit,bool) or not isinstance(limit,(int,float)) or not math.isfinite(limit) or limit<0):
            raise ValueError('invalid precision budget')
    mesh=result['mesh']
    vertices=mesh['vertices_m']
    faces=mesh['triangles']
    evidence=result['provenance']['faces']
    if result.get('research_only') is not True or result.get('lofting_authorized') is not False:
        raise ValueError('research-only result required')
    if not vertices or not faces or len(evidence)!=len(faces):
        raise ValueError('nonempty mesh and complete face manifest required')
    if any(not isinstance(e,dict) or type(e.get('face_id')) is not int or e['face_id']!=i for i,e in enumerate(evidence)):
        raise ValueError('face evidence order mismatch')
    for entry in evidence:
        if 'cell_review' in entry:
            review=entry['cell_review']
            if not valid_reference(review) or review.get('review')!='accepted':
                raise ValueError('face cell evidence review must be accepted')
        refs=entry.get('sources')
        if not isinstance(refs,list) or not refs or not all(valid_reference(ref) for ref in refs):
            raise ValueError('face requires nonempty valid evidence sources')
    q=validate_mesh(vertices,faces)
    if any(q[k] for k in ('invalid_faces','degenerate_faces','duplicate_faces','nonmanifold_edges','inconsistent_winding_edges')):
        raise ValueError('invalid mesh')
    # MCIS x-forward,y-transverse,z-up to glTF y-up via proper rotation.
    if local_origin_m is not None:
        if not isinstance(local_origin_m,(tuple,list)) or len(local_origin_m)!=3 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in local_origin_m):
            raise ValueError('invalid local origin')
        local_origin_m=list(local_origin_m)
        local=[[v-o for v,o in zip(p,local_origin_m)] for p in vertices]
    else:
        local=vertices
    original=[[x,z,-y] for x,y,z in local]
    positions=original
    try:
        raw=struct.pack('<'+'f'*(3*len(positions)),*(v for p in positions for v in p))
    except (OverflowError, struct.error) as exc:
        raise ValueError('coordinates not representable as float32') from exc
    positions=[list(p) for p in struct.iter_unpack('<fff',raw)]
    quantized=validate_mesh(positions,faces)
    if any(quantized[k] for k in ('invalid_faces','degenerate_faces','duplicate_faces','nonmanifold_edges','inconsistent_winding_edges')):
        raise ValueError('float32 serialization introduced invalid geometry')
    if len({tuple(p) for p in positions}) < len({tuple(p) for p in original}):
        raise ValueError('float32 serialization merged distinct vertices')
    vertex_error=max(math.dist(a,b) for a,b in zip(original,positions))
    # Compare decoded coordinates after the complete inverse frame transformation.
    # Local quantization alone omits loss during subtraction/addition.
    world_vertex_error=vertex_error
    if local_origin_m is not None:
        recovered=[[x+local_origin_m[0],-z+local_origin_m[1],y+local_origin_m[2]] for x,y,z in positions]
        if any(not math.isfinite(v) for p in recovered for v in p):
            raise ValueError('nonfinite world roundtrip')
        world_vertex_error=max(math.dist(a,b) for a,b in zip(vertices,recovered))
        restored=validate_mesh(recovered,faces)
        if any(restored[k] for k in ('invalid_faces','degenerate_faces','duplicate_faces','nonmanifold_edges','inconsistent_winding_edges')):
            raise ValueError('world roundtrip introduced invalid geometry')
        if len({tuple(p) for p in recovered}) < len({tuple(p) for p in vertices}):
            raise ValueError('world roundtrip merged distinct vertices')
    area_error=0.0
    edge_error=0.0
    for face in faces:
        n0=_normal(original,face)
        n1=_normal(positions,face)
        a0,a1=math.hypot(*n0),math.hypot(*n1)
        if not math.isfinite(a0) or a0<=0 or not math.isfinite(a1):
            raise ValueError('invalid face normal')
        if math.fsum((x/a0)*(y/a1) for x,y in zip(n0,n1))<=0:
            raise ValueError('float32 serialization reversed face normal')
        area_error=max(area_error,abs(a1/a0-1))
        for i,j in zip(face,(*face[1:],face[0])):
            d0=math.dist(original[i],original[j])
            d1=math.dist(positions[i],positions[j])
            edge_error=max(edge_error,abs(d1/d0-1))
    for value,limit in ((max(vertex_error,world_vertex_error),max_vertex_error_m),(area_error,max_area_relative_error),(edge_error,max_edge_relative_error)):
        if limit is not None and value>limit:
            raise ValueError('float32 precision budget exceeded')
    indices=struct.pack('<'+'I'*(3*len(faces)),*(i for f in faces for i in f))
    binary=raw+indices
    doc={'asset':{'version':'2.0','extras':{'research_only':True,'lofting_authorized':False}},
         'scene':0,'scenes':[{'nodes':[0]}],'nodes':[{'mesh':0}],
         'meshes':[{'primitives':[{'attributes':{'POSITION':0},'indices':1,'mode':4}]}],
         'buffers':[{'byteLength':len(binary)}],
         'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':len(raw),'target':34962},{'buffer':0,'byteOffset':len(raw),'byteLength':len(indices),'target':34963}],
         'accessors':[{'bufferView':0,'componentType':5126,'count':len(vertices),'type':'VEC3','min':[min(p[i] for p in positions) for i in range(3)],'max':[max(p[i] for p in positions) for i in range(3)]},{'bufferView':1,'componentType':5125,'count':3*len(faces),'type':'SCALAR'}]}
    if local_origin_m is not None:
        doc['asset']['extras']['mcis_origin_m']=local_origin_m
    j=json.dumps(doc,separators=(',',':'),allow_nan=False).encode()
    j+=b' '*((-len(j))%4)
    glb=struct.pack('<4sII',b'glTF',2,12+8+len(j)+8+len(binary))+struct.pack('<I4s',len(j),b'JSON')+j+struct.pack('<I4s',len(binary),b'BIN\x00')+binary
    sidecar={'faces':evidence,'axis_mapping':'(x,y,z)->(x,z,-y)','research_only':True,'lofting_authorized':False}
    if local_origin_m is not None:
        sidecar['mcis_origin_m']=local_origin_m
    if local_origin_m is not None or any(v is not None for v in (max_vertex_error_m,max_area_relative_error,max_edge_relative_error)):
        sidecar['precision']={'max_vertex_error_m':max(vertex_error,world_vertex_error),'max_local_vertex_error_m':vertex_error,'max_world_vertex_error_m':world_vertex_error,'max_area_relative_error':area_error,'max_edge_relative_error':edge_error}
    return glb,sidecar
