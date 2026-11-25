"""Orchestrate a reviewed research drawing into a bounded GLB asset."""
from copy import deepcopy
import hashlib
import math
from .drawing_pipeline import extract_from_drawing
from .offset_bridge import prepare_offset_samples
from .reconstruction_pipeline import reconstruct_sparse
from .glb_export import export_glb
from .asset_integrity import bind_asset, verify_asset, canonical
from .geometry_provenance import valid_reference

def run_research(parsed, *, region, mapping, frame_id, offset_reviews,
                 cell_reviews, research_review, precision, algorithm_version,
                 local_origin_m=None):
    doc=parsed['document']
    if not valid_reference(research_review) or research_review.get('review')!='accepted' or research_review.get('frame_id')!=frame_id or research_review.get('drawing_sha256')!=doc.get('sha256') or research_review.get('acknowledged_issues')!=parsed.get('issues',[]):
        raise ValueError('matching research drawing review required')
    digest=doc.get('sha256')
    if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('invalid drawing digest')
    limits=('max_vertex_error_m','max_area_relative_error','max_edge_relative_error')
    if not isinstance(precision,dict) or set(precision)!=set(limits) or any(precision[k] is None for k in limits):
        raise ValueError('all three research precision budgets required')
    if any('cad_y' not in s for s in mapping['row_specs']):
        raise ValueError('explicit reviewed CAD row anchors required')
    mapping_digest=hashlib.sha256(canonical({'region':region,'mapping':mapping})).hexdigest()
    if research_review.get('mapping_sha256')!=mapping_digest:
        raise ValueError('research review does not match table mapping')
    extraction=extract_from_drawing(parsed,region=region,mapping=mapping)
    stations=sorted(mapping['stations_m'])
    heights=sorted(s['height_m'] for s in mapping['row_specs'])
    prepared=prepare_offset_samples(extraction,stations_m=stations,heights_m=heights,
        reviews=offset_reviews,frame_id=frame_id)
    if not isinstance(cell_reviews,dict):
        raise ValueError('cell review map required')
    for key,review in cell_reviews.items():
        if not isinstance(key,tuple) or len(key)!=2 or any(type(k) is not int for k in key):
            raise ValueError('invalid cell review index')
        i,j=key
        if not (0<=i<len(stations)-1 and 0<=j<len(heights)-1) or not isinstance(review,dict):
            raise ValueError('invalid cell review')
        if review.get('review')=='accepted':
            bounds=[stations[i],heights[j],stations[i+1],heights[j+1]]
            supplied_bounds=review.get('bounds_m')
            if not isinstance(supplied_bounds,list) or len(supplied_bounds)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) for v in supplied_bounds):
                raise ValueError('invalid cell review bounds')
            if review.get('frame_id')!=frame_id or review.get('drawing_sha256')!=digest or review.get('mapping_sha256')!=mapping_digest or supplied_bounds!=bounds:
                raise ValueError('cell review scope mismatch')
    result=reconstruct_sparse(stations,heights,prepared['samples'],cell_reviews)
    if not result['mesh']['triangles']:
        raise ValueError('no supported geometry to export')
    glb,side=export_glb(result,local_origin_m=local_origin_m,**precision)
    side['research_review']=deepcopy(research_review)
    side['frame_id']=frame_id
    side['drawing_sha256']=digest
    side['mapping_sha256']=mapping_digest
    side['offset_audit']=prepared
    side['precision_budget']=deepcopy(precision)
    manifest=bind_asset(glb,side,algorithm_version=algorithm_version)
    if not verify_asset(glb,side,manifest,expected_algorithm_version=algorithm_version)['matches']:
        raise ValueError('asset integrity check failed')
    return dict(glb=glb,evidence=side,manifest=manifest,geometry=result,
                research_only=True,lofting_authorized=False)
