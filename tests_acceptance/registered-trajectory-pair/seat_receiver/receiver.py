"""Disabled-by-default local synthetic acceptance consumer, NOT an authorization interface.
Only run_handoff(consumer) from fixed 1095e67 may deliver the record in integration.
No data, pins or labels are accepted from a model/UI. No output persistence.
"""
import hashlib,importlib,importlib.util,json,sys
from pathlib import Path
from types import ModuleType
CASE='SYN-XREPO-001'
TIMES=('2026-02-01T12:01:40.000Z','2026-02-01T12:02:04.250Z')
SHAS=('a8f9109a33b8c80a6c41219473186e69c16fd59ee64ff325a5559c190028bb1c',
      '07e043fc227770b6aaa6f1b15a6118e46b85a52e5638ac1b514e9269c6b159ca')
class ReviewError(ValueError):pass
def require(ok,code):
    if not ok:raise ReviewError(code)
def consumer(record, *, dependencies):
    """Explicit test callback; record provenance is supplied ONLY by trusted host call path.
    Comparing a record does not prove authorization. This function cannot attest who called it.
    """
    require(type(record) is dict and set(record)=={'scope','caseId','frames','accessCount','identityProviderVerified','readCredential','reportSaved','modelCalled'},'ENVELOPE')
    require(record['scope']=='synthetic-test-host-only' and record['caseId']==CASE,'SCOPE')
    require(type(record['accessCount']) is int and record['accessCount']==4,'ACCESS_ASSERTION')
    require(all(record[k] is False for k in ('identityProviderVerified','readCredential','reportSaved','modelCalled')),'FLAGS')
    require(type(record['frames']) is list and len(record['frames'])==2,'TWO_FRAMES')
    project,host,docs=dependencies
    pins=None;items=[];summaries=[]
    for frame,utc in zip(record['frames'],TIMES):
        require(type(frame) is dict and set(frame)=={'caseId','alignedUtc','vessels','authenticityVerified','collisionDetermined'},'FRAME_FIELDS')
        require(frame['caseId']==CASE and frame['alignedUtc']==utc,'EXACT_TIME_CASE')
        require(frame['authenticityVerified'] is False and frame['collisionDetermined'] is False,'FRAME_FLAGS')
        require(type(frame['vessels']) is list and len(frame['vessels'])==2,'TWO_VESSELS')
        current=[v['original'] for v in frame['vessels']]
        for pin,sha in zip(current,SHAS):
            require(type(pin) is dict and set(pin)=={'caseId','evidenceId','requestDigest','sourceSha256'},'PIN_FIELDS')
            require(pin['caseId']==CASE and pin['sourceSha256']==sha,'PIN_RAW')
            require(isinstance(pin['evidenceId'],str) and bool(pin['evidenceId']),'EVIDENCE_ID')
            require(isinstance(pin['requestDigest'],str) and len(pin['requestDigest'])==64 and all(c in '0123456789abcdef' for c in pin['requestDigest']),'DIGEST')
        require(current[0]['evidenceId']!=current[1]['evidenceId'] and current[0]['requestDigest']!=current[1]['requestDigest'],'DISTINCT_ORIGINALS')
        require(pins is None or current==pins,'PIN_CHANGED')
        pins=current
        for i,(row,doc,pin) in enumerate(zip(frame['vessels'],docs,pins)):
            expected=project._point_from_committed_original({'document':doc,'pin':pin},project._stamp(utc))
            require(row==expected,'FIXED_ORIGINAL_PROJECTION')
            # Internal pins stay in host. The note exposes only synthetic time/status/locator.
            summary={'alignedUtc':utc,'vessel':('A','B')[i],'status':row['status'],
                     'locator':row['locator'],'displayTime':row['time'],
                     'timeReview':'pending','timeRelation':'undetermined',
                     'clockBasisInHandoff':'absent','label':'insufficient'}
            summaries.append(summary)
            items.append({'itemId':str(len(items)+1),'sourceText':json.dumps(summary,sort_keys=True)})
    reviews=[dict(itemId=x['itemId'],label='insufficient',quote=x['sourceText'],
                  rationale='Fixed original projection checked; pending human review.',
                  uncertainty='Clock basis and human calibration approval are absent from handoff.') for x in items]
    host._validate({'reviews':reviews},{'items':items})
    return {'scope':'synthetic-test-only','status':'proposed_note_pending_human_review',
            'summaries':summaries,'reviews':reviews,'saved':False,'factActivated':False,
            'humanSignature':None,'authorizationVerifiedByConsumer':False}

