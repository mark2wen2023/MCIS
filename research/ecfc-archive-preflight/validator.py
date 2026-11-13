"""Isolated archive preflight experiment; no restore or production integration."""
import json
MAX_BYTES=2*1024*1024
MAX_DEPTH=48
MAX_NODES=100000

def decode(raw):
    if type(raw) is not bytes or len(raw)>MAX_BYTES:
        raise ValueError('bounded bytes required')
    def pairs(items):
        result={}
        for k,v in items:
            if k in result: raise ValueError('duplicate member')
            result[k]=v
        return result
    def constant(_): raise ValueError('nonfinite number')
    try:
        value=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=constant)
        stack=[(value,0)];count=0
        while stack:
            obj,depth=stack.pop();count+=1
            if depth>MAX_DEPTH or count>MAX_NODES: raise ValueError('resource limit')
            if type(obj) is float:
                import math
                if not math.isfinite(obj):raise ValueError('nonfinite number')
            if isinstance(obj,str):obj.encode('utf-8')
            if isinstance(obj,dict):
                for key in obj:key.encode('utf-8')
                stack.extend((x,depth+1) for x in obj.values())
            elif isinstance(obj,list):stack.extend((x,depth+1) for x in obj)
        return value
    except (UnicodeError,RecursionError,OverflowError) as e:
        raise ValueError('invalid encoding or nesting') from e

def validate_envelope(raw, case_id, api, validate_plan):
    data=decode(raw)
    if type(data) is not dict or set(data)!={'profile','sourceCaseId','current','history','receipts'}:
        raise ValueError('invalid envelope')
    if data['profile']!='ecfc-preflight-experiment-v0' or data['sourceCaseId']!=case_id:
        raise ValueError('profile/case mismatch')
    def event(item):
        if type(item) is not dict or type(item.get('revision')) is not int:raise ValueError('invalid event')
        api.validate_event(item,case_id,item['revision'])
    validate_plan(data['current'],data['history'],data['receipts'],lambda d:api.validate_document(d,case_id),event)
    return data
