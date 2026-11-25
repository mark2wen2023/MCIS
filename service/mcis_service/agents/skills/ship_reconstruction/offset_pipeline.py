"""Compose reviewed CAD table extraction primitives; no loft authorization."""
from .table_extraction import cluster_rows
from .column_matching import match_columns
from .offset_semantics import normalize_row
from .offset_validation import validate_offsets

def extract_offsets(cells, *, row_specs, anchors, stations_m, unit,
                    document_id, row_tolerance, column_tolerance):
    """row_specs: reviewed top-to-bottom list of {height_m, locator}.
    Cells must contain only body half-breadth text, in one reviewed planar frame.
    """
    issues=[]
    rows=[]
    try:
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
