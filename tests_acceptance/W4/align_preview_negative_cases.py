"""Independent pending input mutation matrix; final DTO fixture set after freeze.
Not an executed test nor production code. Path canary supplied by test temp dir.
"""
from copy import deepcopy


def forbidden_payloads(valid, canary):
    """Yield name/payload; caller must assert 422 AND zero core invocations."""
    for key, value in [('path',canary),('path',None),('manualAnchors',{'text':'a','path':canary}),
                       ('manualAnchors',None),('caseId','OTHER-CASE'),('caseEpochUtc','1900-01-01T00:00:00Z'),
                       ('command','version'),('unexpected',None)]:
        body=deepcopy(valid); body[key]=value
        yield f'top_{key}_{value is None}',body
    for value in [canary,None,'../canary.csv','file://'+canary]:
        body=deepcopy(valid);body['sources'][0]['path']=value
        yield f'source_path_{value}',body
    for node in ['source','mapping','column']:
        for key in ['path','unexpected']:
            body=deepcopy(valid)
            target=body['sources'][0]
            if node in ['mapping','column']:target=target['csvMapping']
            if node=='column':target=target['columns'][0]
            target[key]=None
            yield f'{node}_{key}_null',body
