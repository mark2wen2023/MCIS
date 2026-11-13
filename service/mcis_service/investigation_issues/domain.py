"""Deterministic manual hypotheses, per-round verification and discussion records."""
from copy import deepcopy
import hashlib, json, math, re
from ..common.context import problem
MAX_BODY = 64 * 1024

def fail(code='INVALID_ISSUE_INPUT', status=422):
    raise problem(status, code, '调查问题输入或流程不符合当前合同')

def obj(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields): fail()
    return value

def txt(value, limit=4000):
    if not isinstance(value, str) or not value.strip() or len(value)>limit or value != value.strip(): fail()
    try: value.encode('utf-8')
    except UnicodeError: fail()
    return value

def integer(value):
    if type(value) is not int or value<1: fail()
    return value

def uid(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',value): fail()
    return value

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def digest(value): return hashlib.sha256(canonical(value)).hexdigest()

def parse(raw):
    def pairs(items):
        result={}
        for k,v in items:
            if k in result: fail()
            result[k]=v
        return result
    try:
        body=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=lambda _: fail())
        pending=[(body,0)]; count=0
        while pending:
            v,d=pending.pop(); count+=1
            if d>16 or count>5000: fail()
            if isinstance(v,str): v.encode('utf-8')
            elif isinstance(v,float) and not math.isfinite(v): fail()
            elif isinstance(v,dict):
                for k,item in v.items(): k.encode('utf-8'); pending.append((item,d+1))
            elif isinstance(v,list): pending.extend((item,d+1)for item in v)
        return body
    except (ValueError,UnicodeError,RecursionError,OverflowError): fail()

def refs(value):
    if not isinstance(value,list) or len(value)>20: fail()
    seen=set()
    for v in value:
        obj(v,('evidenceId','sha256'))
        if not isinstance(v['evidenceId'],str) or not re.fullmatch(r'EV-[0-9]{3,}',v['evidenceId']) or v['evidenceId']in seen: fail()
        if not isinstance(v['sha256'],str) or not re.fullmatch('[a-f0-9]{64}',v['sha256']): fail()
        seen.add(v['evidenceId'])
    return sorted(deepcopy(value),key=lambda r:r['evidenceId'])

def strings(value, empty=True):
    if not isinstance(value,list) or len(value)>30 or (not empty and not value): fail()
    for v in value: txt(v,1000)
    return value

def invalidate(state):
    state['stage']='AssessmentRecorded'
    state['packet']=None
    state['currentVerifications']={}

def transition(original,kind,p,seq):
    s=deepcopy(original); stage=s['stage']; hs=s['hypotheses']
    def state(*allowed):
        if stage not in allowed: fail('INVALID_TRANSITION',409)
    if kind=='RecordHypothesis':
        state('Observed','AssessmentRecorded','Verifying','AwaitingDiscussion')
        obj(p,('hypothesisId','text','reason','expectedVersion','sourceRefs'))
        uid(p['hypothesisId']); txt(p['text']); txt(p['reason']); refs(p['sourceRefs'])
        old=hs.get(p['hypothesisId'])
        if type(p['expectedVersion'])is not int or p['expectedVersion'] != (old['version'] if old else 0): fail('HYPOTHESIS_VERSION_CONFLICT',409)
        if old is None and len(hs)>=30: fail('ISSUE_LIMIT',413)
        hs[p['hypothesisId']]={'id':p['hypothesisId'],'version':p['expectedVersion']+1,'text':p['text'],'reason':p['reason'],'sourceRefs':refs(p['sourceRefs']),'eventSeq':seq}
        invalidate(s)
    elif kind=='ReviewSources':
        state('Observed','AssessmentRecorded','Verifying','AwaitingDiscussion')
        obj(p,('sourceRefs','reason'));refs(p['sourceRefs']);txt(p['reason'])
        s['initialSources']=refs(p['sourceRefs']);invalidate(s)
    elif kind=='BeginVerification':
        state('AssessmentRecorded'); obj(p,('question','method')); txt(p['question']);txt(p['method'])
        if not hs: fail('ASSESSMENT_REQUIRED',409)
        s['round']+=1;s['currentVerifications']={};s['stage']='Verifying'
    elif kind=='RecordVerification':
        state('Verifying');obj(p,('hypothesisId','hypothesisVersion','activity','result','outcome','sourceRefs'))
        uid(p['hypothesisId']);integer(p['hypothesisVersion']);txt(p['activity']);txt(p['result']);refs(p['sourceRefs'])
        h=hs.get(p['hypothesisId'])
        if h is None or h['version']!=p['hypothesisVersion']:fail('HYPOTHESIS_VERSION_CONFLICT',409)
        if p['outcome'] not in ('Supported','Contradicted','Inconclusive','UnableToVerify'):fail()
        s['currentVerifications'][p['hypothesisId']]={'round':s['round'],'hypothesisVersion':h['version'],'eventSeq':seq,'sourceRefs':refs(p['sourceRefs']),'outcome':p['outcome']}
    elif kind=='SubmitDiscussion':
        state('Verifying');obj(p,('agenda','unresolved'));txt(p['agenda']);strings(p['unresolved'])
        if not hs or any(k not in s['currentVerifications'] or s['currentVerifications'][k]['round']!=s['round'] or s['currentVerifications'][k]['hypothesisVersion']!=v['version'] for k,v in hs.items()):fail('CURRENT_VERIFICATION_REQUIRED',409)
        s['stage']='AwaitingDiscussion';s['packet']={'revision':seq,'round':s['round'],'hypotheses':deepcopy(hs),'verifications':deepcopy(s['currentVerifications']),'agenda':p['agenda'],'unresolved':deepcopy(p['unresolved'])}
    elif kind=='RecordDiscussion':
        state('AwaitingDiscussion');obj(p,('packetRevision','summary','dissent','participantsRecorded','outcome'))
        integer(p['packetRevision']);txt(p['summary']);strings(p['dissent']);strings(p['participantsRecorded'],False)
        if p['packetRevision']!=s['packet']['revision']:fail('STALE_PACKET',409)
        if p['outcome']not in ('OpinionRecorded','MoreVerification','Undetermined'):fail()
        # Recorded participants are not signatures, votes or authorizations.
        s['stage']='DiscussionRecorded'
        if p['outcome']=='MoreVerification':
            s['round']+=1;s['currentVerifications']={};s['packet']=None;s['stage']='Verifying'
    elif kind=='Reopen':
        state('DiscussionRecorded');obj(p,('reason',));txt(p['reason']);invalidate(s)
    else: fail()
    s['revision']=seq
    return s
