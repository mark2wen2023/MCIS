"""Research half-hull from reviewed waterlines; no extrapolation or closure."""
from bisect import bisect_right
from copy import deepcopy
import math
from .adaptive_waterline import adaptive_waterline, _finite, _reference, _line


def fuse_waterlines(lines, *, frame_id, band_reviews, line_tolerance_m,
                    mesh_tolerance_m, max_stations):
    """Bind adjacent bands to source digests. Linear-in-height is a hypothesis.
    The mesh bound concerns same-(x,z) half-breadth versus the bilinear model,
    not geometric fidelity to a real hull. Missing bands are not bridged.
    """
    if not isinstance(lines, list) or len(lines) < 2 or not isinstance(band_reviews, dict):
        raise ValueError('waterlines and band review map required')
    if not _finite(mesh_tolerance_m) or mesh_tolerance_m <= 0 or type(max_stations) is not int or max_stations < 2:
        raise ValueError('invalid mesh budget')
    fits = [adaptive_waterline(frame_id=frame_id, tolerance_m=line_tolerance_m,
                               max_knots=max_stations, **line) for line in lines]
    if not all(f['tolerance_met'] for f in fits):
        raise ValueError('waterline tolerance not met')
    zs = [f['height_m'] for f in fits]
    if any(b <= a or not math.isfinite(b-a) for a,b in zip(zs,zs[1:])):
        raise ValueError('waterline heights must increase')
    knots = [f['knots'] for f in fits]
    axes = [[p['x_m'] for p in k] for k in knots]
    if any((a[0],a[-1]) != (axes[0][0],axes[0][-1]) for a in axes):
        raise ValueError('common longitudinal extent required; no extrapolation')
    for i,r in band_reviews.items():
        if type(i) is not int or not 0 <= i < len(zs)-1 or not _reference(r) or r.get('review') != 'accepted' or r.get('frame_id') != frame_id or r.get('model') != 'linear_in_height' or r.get('reference_sha256s') != [fits[i]['reference_sha256'],fits[i+1]['reference_sha256']]:
            raise ValueError('invalid or stale band review')
    if not band_reviews:
        raise ValueError('no supported research band')
    def width(j,x):
        k = min(bisect_right(axes[j],x)-1,len(axes[j])-2)
        return _line(knots[j][k],knots[j][k+1],x)
    base = sorted(set(x for a in axes for x in a))
    if len(base)>max_stations:
        raise ValueError('common station budget exceeded')
    def error(a,b):
        return max(abs((width(j+1,b)-width(j+1,a))-(width(j,b)-width(j,a)))/4 for j in band_reviews)
    # On each shared interval both boundary polylines are affine in x.
    # The exact-arithmetic maximum bilinear-vs-triangle error is |cross term|/4.
    xs = [base[0]]
    for a,b in zip(base,base[1:]):
        pending = [(a,b)]
        while pending:
            l,r = pending.pop()
            e = error(l,r)
            if not math.isfinite(e):
                raise ValueError('nonfinite mesh error')
            if e <= mesh_tolerance_m:
                xs.append(r)
            else:
                m = l+(r-l)/2
                if not l<m<r or len(xs)+len(pending)+2>max_stations:
                    raise ValueError('mesh tolerance cannot meet station budget')
                pending.extend([(m,r),(l,m)])
            if len(xs)>max_stations:
                raise ValueError('station budget exceeded')
    vertices, faces, provenance, indices = [], [], [], {}
    for j in sorted(band_reviews):
        for i,(a,b) in enumerate(zip(xs,xs[1:])):
            ids=[]
            for k,h in ((i,j),(i,j+1),(i+1,j),(i+1,j+1)):
                if (k,h) not in indices:
                    indices[k,h]=len(vertices)
                    vertices.append([xs[k],width(h,xs[k]),zs[h]])
                ids.append(indices[k,h])
            p,q,r,s=ids
            faces.extend([[p,q,r],[q,s,r]])
            for _ in range(2):
                provenance.append(dict(face_id=len(provenance),band=j,interval_m=[a,b],
                    basis='computed_bilinear_band',band_review=deepcopy(band_reviews[j]),
                    reference_sha256s=[fits[j]['reference_sha256'],fits[j+1]['reference_sha256']]))
    return dict(stations_m=xs,heights_m=zs,base_station_count=len(base),waterlines=fits,
                mesh=dict(vertices_m=vertices,triangles=faces),face_evidence=provenance,
                unsupported_bands=[i for i in range(len(zs)-1) if i not in band_reviews],
                max_reference_residual_m=max(f['max_reference_residual_m'] for f in fits),
                max_mesh_model_residual_m=max(error(a,b) for a,b in zip(xs,xs[1:])),
                physical_hull_accuracy_certified=False,closed_hull=False,
                research_only=True,lofting_authorized=False)
