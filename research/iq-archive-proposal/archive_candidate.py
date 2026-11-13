"""Experimental JSON preflight for a proposed IQ bundle, NOT .mcase support.

No I/O, authorization framework integration or restoration. A successful call
means only the checks in this module and validate.py passed.
"""
import base64
import binascii
import hashlib
import json
import re
from validate import validate, InvalidSnapshot

VERSION='iq-research-1'
MAX_ARCHIVE=16*1024*1024
MAX_EVIDENCE=8*1024*1024
MAX_NODES=200000
MAX_DEPTH=32

class InvalidArchive(ValueError): pass

def fail(): raise InvalidArchive('invalid, unsupported or incomplete archive')
def exact(d, keys):
    if type(d) is not dict or set(d)!=set(keys): fail()
def unique_pairs(pairs):
    result={}
    for k,v in pairs:
        if k in result: fail()
        result[k]=v
    return result

def preflight(raw, authorize):
    """Validate a non-production bundle. authorize(case_id,eid,sha) must fail closed.

    Caller must authorize destination and source *before* invoking this method;
    this callback additionally authorizes every historic evidence version. It is
    not safe to use returned contents directly to restore or disclose records.
    """
    try:
        if type(raw) is not bytes or len(raw)>MAX_ARCHIVE:fail()
        def no_float(_): fail()
        d=json.loads(raw.decode('utf-8'), object_pairs_hook=unique_pairs,
                     parse_float=no_float,parse_constant=no_float)
        stack=[(d,0)]; count=0
        while stack:
            v,depth=stack.pop();count+=1
            if count>MAX_NODES or depth>MAX_DEPTH:fail()
            if type(v) is str:v.encode('utf-8')
            elif type(v) is dict:
                for k,item in v.items():k.encode('utf-8');stack.append((item,depth+1))
            elif type(v) is list:stack.extend((x,depth+1) for x in v)
            elif v is None or type(v) in (bool,int):pass
            else:fail()
        exact(d,('version','sourceCaseId','issues','events','receipts','evidence'))
        if d['version']!=VERSION or type(d['sourceCaseId']) is not str or not 1<=len(d['sourceCaseId'])<=64:fail()
        for key in ('issues','events','receipts','evidence'):
            if type(d[key]) is not list:fail()
        versions={}; total=0
        for entry in d['evidence']:
            exact(entry,('evidenceId','sha256','descriptor','bytesBase64'))
            eid,sha,desc=entry['evidenceId'],entry['sha256'],entry['descriptor']
            if type(eid) is not str or not re.fullmatch(r'EV-[0-9]{3,}',eid):fail()
            if type(sha) is not str or not re.fullmatch(r'[a-f0-9]{64}',sha):fail()
            # This toy descriptor is deliberately only a reference key, not
            # a complete historical evidence descriptor. Unknown members fail.
            exact(desc,('evidenceId','sha256'))
            if desc['evidenceId']!=eid or desc['sha256']!=sha:fail()
            if (eid,sha) in versions or type(entry['bytesBase64']) is not str:fail()
            b64=entry['bytesBase64']
            if len(b64)>((MAX_EVIDENCE+2)//3)*4:fail()
            data=base64.b64decode(b64,validate=True);total+=len(data)
            if total>MAX_EVIDENCE or hashlib.sha256(data).hexdigest()!=sha:fail()
            # Reject alternate encodings so a version has exactly one encoding.
            if base64.b64encode(data).decode('ascii')!=b64:fail()
            versions[eid,sha]=data
        events=[]
        for row in d['events']:
            exact(row,('issueId','sequence','event'))
            events.append((row['issueId'],row['sequence'],row['event']))
        receipts=[]
        seen_request_ids=set()
        for row in d['receipts']:
            exact(row,('operator','role','requestId','digest','issueId','response'))
            # The live API permits the same request ID for different actors.
            # This conservative candidate profile cannot safely restore such a
            # history yet, so reject it, never collapse or silently rewrite it.
            rid=row['requestId']
            if type(rid) is not str or rid in seen_request_ids:fail()
            seen_request_ids.add(rid)
            receipts.append((row['operator'],row['role'],row['requestId'],row['digest'],row['issueId'],row['response']))
        referenced=validate(d['sourceCaseId'],d['issues'],events,receipts,
                            lambda eid,sha:versions[eid,sha],
                            lambda eid,sha:authorize(d['sourceCaseId'],eid,sha))
        if referenced!=set(versions):fail() # reject missing AND surplus inventory
        return d
    except InvalidArchive:raise
    except (InvalidSnapshot,ValueError,TypeError,KeyError,UnicodeError,RecursionError,OverflowError,binascii.Error):fail()
