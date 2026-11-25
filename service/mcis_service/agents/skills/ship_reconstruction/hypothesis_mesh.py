"""Aligned one-sided research meshes and pointwise breadth differences."""
from copy import deepcopy
from .hull_hypotheses import compare_hypotheses


def build_hypothesis_meshes(stations, heights, cells, scenarios, support, *, frame_id, symmetry_confirmed, reference):
    if reference not in scenarios:
        raise ValueError('unknown reference scenario')
    comparison = compare_hypotheses(stations, heights, cells, scenarios, support,
                                    frame_id=frame_id, symmetry_confirmed=symmetry_confirmed)
    keys, indices, triangles, face_cells = [], {}, [], []
    for i, j in comparison['common_cells']:
        corners = [(i,j),(i,j+1),(i+1,j),(i+1,j+1)]
        for key in corners:
            if key not in indices:
                indices[key] = len(keys)
                keys.append(key)
        a,b,c,d = [indices[k] for k in corners]
        triangles.extend([[a,b,c],[b,d,c]])
        face_cells.extend([[i,j],[i,j]])
    models = {}
    for name, scenario in scenarios.items():
        vertices, evidence = [], []
        for i,j in keys:
            selected = scenario['choices'][i][j]
            candidate = next(c for c in cells[i][j]['candidates'] if c['id'] == selected)
            vertices.append([stations[i], candidate['value_m'], heights[j]])
            evidence.append(dict(grid_index=[i,j], candidate=deepcopy(candidate),
                                 original=deepcopy(cells[i][j]['original'])))
        models[name] = dict(vertices_m=vertices, vertex_evidence=evidence)
    base = models[reference]['vertices_m']
    for model in models.values():
        delta = [p[1]-q[1] for p,q in zip(model['vertices_m'],base)]
        model['signed_half_breadth_delta_m'] = delta
        model['max_abs_delta_m'] = max(map(abs,delta),default=None)
    ranges = [max(m['vertices_m'][k][1] for m in models.values())-
              min(m['vertices_m'][k][1] for m in models.values()) for k in range(len(keys))]
    return dict(frame_id=frame_id, reference=reference, vertex_grid_indices=[list(k) for k in keys],
                triangles=triangles, face_cells=face_cells, models=models, vertex_range_m=ranges,
                comparison=comparison, surface='one_sided_piecewise_linear_mesh',
                distance_metric='signed_half_breadth_at_same_x_z',
                probability_certified=False, research_only=True, lofting_authorized=False)
