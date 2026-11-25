"""Compose reviewed CAD table extraction primitives; no loft authorization."""
import math
from .table_extraction import cluster_rows
from .column_matching import match_columns
from .offset_semantics import normalize_row
from .offset_validation import validate_offsets

def _reviewed_groups(cells, specs, tolerance):
    def finite(v):
        return type(v) in (int,float) and math.isfinite(v)
    if not finite(tolerance) or tolerance<=0:
        raise ValueError('positive finite row tolerance required')
    anchors=[s['cad_y'] for s in specs]
    if not anchors or not all(finite(y) for y in anchors) or any(a-b<=2*tolerance for a,b in zip(anchors,anchors[1:])):
        raise ValueError('unordered or overlapping reviewed row windows')
    groups=[[] for _ in anchors]
    for cell in cells:
        if not finite(cell.get('x')) or not finite(cell.get('y')) or not isinstance(cell.get('text'),str) or not cell.get('handle'):
            raise ValueError('invalid cell anchor or evidence')
        matches=[i for i,y in enumerate(anchors) if abs(cell['y']-y)<=tolerance]
        if len(matches)!=1:
            raise ValueError('text outside reviewed row windows')
        groups[matches[0]].append(cell)
    return groups

def extract_offsets(cells, *, row_specs, anchors, stations_m, unit,
                    document_id, row_tolerance, column_tolerance):
    """row_specs: reviewed top-to-bottom list of {height_m, locator}.
    Include cad_y in every row spec for explicit reviewed CAD row anchors;
    empty rows then remain null. Without cad_y, legacy clustering is retained.
    Cells must contain only body half-breadth text, in one reviewed planar frame.
    """
    issues=[]
    rows=[]
    try:
        if not row_specs:
            raise ValueError('missing reviewed row specs')
        heights=[s['height_m'] for s in row_specs]
        if any(type(z) not in (int,float) or not math.isfinite(z) for z in heights) or len(set(heights))!=len(heights):
            raise ValueError('invalid or duplicate reviewed heights')
        explicit=['cad_y' in s for s in row_specs]
        if any(explicit):
            if not all(explicit):
                raise ValueError('mixed reviewed row mapping')
            grouped=_reviewed_groups(cells,row_specs,row_tolerance)
        else:
            grouped=cluster_rows(cells,row_tolerance)
            if len(grouped)!=len(row_specs) or not grouped:
                raise ValueError('row count differs from reviewed mapping')
        if len(anchors)!=len(stations_m) or not anchors:
            raise ValueError('column mapping mismatch')
        for i,(group,spec) in enumerate(zip(grouped,row_specs)):
            matched=match_columns(group,anchors,column_tolerance)
            if matched['issues']:
                issues.extend(dict(issue,row=i) for issue in matched['issues'])
                continue
            rows.extend(normalize_row(matched['cells'],stations_m,spec['height_m'],
                                      unit,document_id,spec['locator']))
    except (ValueError,KeyError,TypeError,OverflowError) as exc:
        issues.append({'code':'invalid_mapping_or_input','detail':str(exc)})
    diagnostics=validate_offsets(rows)
    ready=bool(rows) and not issues and not any(diagnostics[k] for k in
        ('missing_rows','conflicting_rows','invalid_rows'))
    return {'rows':rows,'issues':issues,'diagnostics':diagnostics,
            'candidate_complete':ready,'lofting_authorized':False}
