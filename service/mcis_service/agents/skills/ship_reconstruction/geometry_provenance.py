"""Research-only face provenance for sparse loft meshes."""
from copy import deepcopy

def valid_reference(ref):
    return isinstance(ref,dict) and all(
        isinstance(ref.get(k),str) and ref[k].strip()
        for k in ('document_id','locator')
    )

def bind_face_evidence(mesh, samples, cell_reviews):
    records=[]
    if len(mesh['triangles'])!=len(mesh['face_cells']):
        raise ValueError('face mapping mismatch')
    for face_id,(face,cell) in enumerate(zip(mesh['triangles'],mesh['face_cells'])):
        i,j=cell
        review=cell_reviews.get((i,j))
        if not valid_reference(review) or review.get('review')!='accepted':
            raise ValueError('cell support evidence required')
        sources=[]
        bases=[]
        for a,b in ((i,j),(i,j+1),(i+1,j),(i+1,j+1)):
            s=samples[a][b]
            if s.get('basis') not in ('direct_sample','interpolated') or s.get('half_breadth_m') is None:
                raise ValueError('unsupported corner')
            refs=s.get('sources')
            if not isinstance(refs,list) or not refs:
                raise ValueError('missing corner evidence')
            for ref in refs:
                if not valid_reference(ref):
                    raise ValueError('invalid evidence reference')
                if ref not in sources:
                    sources.append(deepcopy(ref))
            bases.append(s['basis'])
        records.append(dict(face_id=face_id,cell=[i,j],corner_bases=bases,sources=sources,cell_review=deepcopy(review),basis='computed_surface',review='pending'))
    return dict(faces=records,research_only=True,lofting_authorized=False)
