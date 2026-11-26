"""Adapt reviewed SI offset observations to the research sparse-section input."""
import math
from copy import deepcopy
from .sparse_section import sample_sparse_section


def _finite(v):
    return type(v) in (int,float) and math.isfinite(v)


def _reference(v):
    return isinstance(v,dict) and all(isinstance(v.get(k),str) and v[k].strip() for k in ('document_id','locator'))


def prepare_offset_samples(extraction, *, stations_m, heights_m, reviews, frame_id):
    """Input axes are already in a single reviewed SI frame. No rescaling.

    Reviews bind each numeric value to its coordinate, frame and source. A
    missing table cell must be explicitly represented as a null observation.
    Review labels are caller supplied, not authenticated signatures.
    """
    if not isinstance(frame_id,str) or not frame_id.strip():
        raise ValueError('research frame identifier required')
    if not isinstance(extraction,dict) or extraction.get('issues') != [] or extraction.get('lofting_authorized') is not False:
        raise ValueError('unresolved extraction issues or invalid authorization')
    for axis in (stations_m,heights_m):
        if len(axis)<2 or not all(_finite(v) for v in axis) or any(b<=a for a,b in zip(axis,axis[1:])):
            raise ValueError('invalid reviewed SI axes')
    if not isinstance(reviews,dict):
        raise ValueError('review map required')
    expected={(x,z) for x in stations_m for z in heights_m}
    rows={}
    for row in extraction['rows']:
        x,z,y=(row[k] for k in ('station_x_m','height_z_m','half_breadth_m'))
        if not _finite(x) or not _finite(z) or (x,z) not in expected or (x,z) in rows:
            raise ValueError('unexpected or duplicate offset coordinate')
        if not _reference(row.get('source')) or (y is not None and (not _finite(y) or y<0)):
            raise ValueError('invalid offset observation')
        rows[x,z]=row
    if set(rows)!=expected:
        raise ValueError('grid is missing explicit observations; preserve null cells')
    if any(not isinstance(k,tuple) or len(k)!=2 or not all(_finite(v) for v in k) or k not in expected or rows[k]['half_breadth_m'] is None for k in reviews):
        raise ValueError('review does not correspond to a numeric observation')
    grid=[]
    for x in stations_m:
        section=[]
        for z in heights_m:
            row=rows[x,z]; y=row['half_breadth_m']; src=deepcopy(row['source'])
            if y is None:
                section.append(dict(height_m=z,value=None,semantic='unknown',evidence=src,review='pending'))
                continue
            review=reviews.get((x,z))
            if not isinstance(review,dict) or review.get('review')!='accepted' or review.get('frame_id')!=frame_id or not _finite(review.get('value_m')) or review['value_m']!=y or review.get('source')!=src or not _reference(review.get('review_source')):
                raise ValueError('numeric offset requires matching accepted research review')
            section.append(dict(height_m=z,value=y,semantic='confirmed_zero' if y==0 else 'measured',evidence=src,review='accepted'))
        grid.append(sample_sparse_section(section,heights_m)['samples'])
    return dict(stations_m=list(stations_m),heights_m=list(heights_m),samples=grid,
                observations=deepcopy(extraction['rows']),review_records=[dict(station_x_m=x,height_z_m=z,record=deepcopy(reviews[x,z])) for x,z in sorted(reviews)],
                drawing_issues=deepcopy(extraction.get('drawing_issues',[])),frame_id=frame_id,
                research_only=True,lofting_authorized=False)
