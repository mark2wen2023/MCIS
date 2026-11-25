"""Signed half-breadth deviation on a shared, supported x-z mesh.

Statistics integrate piecewise-linear differences over projected x-z area,
not actual shell area. No probability or production authorization is implied.
"""
import math
from .hypothesis_mesh import build_hypothesis_meshes


def deviation_field(stations, heights, cells, scenarios, support, *, frame_id,
                    symmetry_confirmed, reference, color_limit_m):
    if type(color_limit_m) not in (int, float) or not math.isfinite(color_limit_m) or color_limit_m <= 0:
        raise ValueError('positive finite color limit required')
    result = build_hypothesis_meshes(stations, heights, cells, scenarios, support,
        frame_id=frame_id, symmetry_confirmed=symmetry_confirmed, reference=reference)
    base = result['models'][reference]['vertices_m']
    faces = result['triangles']
    areas = []
    for a,b,c in faces:
        p,q,r = (base[k] for k in (a,b,c))
        area = abs((q[0]-p[0])*(r[2]-p[2])-(q[2]-p[2])*(r[0]-p[0]))/2
        if not math.isfinite(area) or area <= 0:
            raise ValueError('invalid projected triangle area')
        areas.append(area)
    area = math.fsum(areas)
    def rgb(d):
        t = min(1, abs(d)/color_limit_m)
        end = (190, 55, 45) if d > 0 else (35, 90, 180)
        return [round(240+(v-240)*t) for v in end]
    for model in result['models'].values():
        delta = model['signed_half_breadth_delta_m']
        if not all(math.isfinite(d) for d in delta):
            raise ValueError('nonfinite difference')
        model['vertex_rgb'] = [rgb(d) for d in delta]
        model['saturated_vertex_count'] = sum(abs(d)>color_limit_m for d in delta)
        # Exact first and second moments of a linear field on each triangle.
        means, squares = [], []
        for face,w in zip(faces,areas):
            a,b,c = (delta[k] for k in face)
            means.append(w*(a+b+c)/3)
            squares.append(w*(a*a+b*b+c*c+a*b+b*c+c*a)/6)
        model['projected_mean_delta_m'] = math.fsum(means)/area if area else None
        model['projected_rmse_m'] = math.sqrt(max(0,math.fsum(squares)/area)) if area else None
    result['projected_area_m2'] = area
    result['color_scale'] = dict(limit_m=color_limit_m, negative_rgb=[35,90,180],
        zero_rgb=[240,240,240], positive_rgb=[190,55,45], clipped=True)
    result['statistics_basis'] = 'piecewise_linear_field_on_common_projected_xz_area'
    return result
