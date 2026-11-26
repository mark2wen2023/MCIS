"""Conservative evidence readiness gate; no geometry inference."""
import math
REQUIRED = ('overall_length', 'moulded_breadth', 'moulded_depth', 'station_spacing')
KINDS = ('lines', 'general_arrangement', 'basic_structure', 'typical_section')

def assess(documents, observations):
    ids = {d['id'] for d in documents if d['status'] in ('parsed', 'partial')}
    kinds = {d['kind'] for d in documents if d['id'] in ids}
    missing = [k for k in KINDS if k not in kinds]
    pending, conflicts = [], []
    for key in REQUIRED:
        rows = [o for o in observations if o['parameter'] == key and o['basis'] in ('direct','calculated') and o['review'] == 'accepted' and o['unit'] in ('m','mm') and isinstance(o['value'], (int,float)) and not isinstance(o['value'],bool) and math.isfinite(o['value']) and o['value'] > 0 and o['sources'] and all(s['document_id'] in ids and s['locator'] for s in o['sources'])]
        values = [o['value'] / (1000 if o['unit']=='mm' else 1) for o in rows]
        if not values:
            pending.append(key)
        elif max(values)-min(values)>1e-6:
            conflicts.append(key)
    return {'missing_drawing_kinds': missing, 'pending_parameters': pending, 'conflicts': conflicts, 'principal_data_ready': not (missing or pending or conflicts), 'lofting_authorized': False, 'remaining_gates': ['reviewed_coordinate_frame','reviewed_offset_table','independent_geometry_review']}
