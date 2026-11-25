"""Connect parsed CAD entities to reviewed offset extraction; fail closed."""
from .table_region import select_region
from .offset_pipeline import extract_offsets

def extract_from_drawing(parsed, *, region, mapping):
    doc=parsed['document']
    if doc['status'] not in ('partial','parsed'):
        return {'rows':[], 'issues':[{'code':'drawing_not_parsed'}], 'candidate_complete':False,'lofting_authorized':False}
    selected=select_region(parsed['entities'],**region)
    if selected['issues']:
        return {'rows':[], 'issues':selected['issues'], 'candidate_complete':False,'lofting_authorized':False}
    result=extract_offsets(selected['cells'],document_id=doc['id'],**mapping)
    result['drawing_issues']=list(parsed.get('issues',[]))
    result['review']='pending'
    result['lofting_authorized']=False
    return result
