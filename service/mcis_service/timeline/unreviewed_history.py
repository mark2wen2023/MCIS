"""Strict historical declarations only. Never creates an index or approval."""
import json
import math
import uuid
from fastapi import HTTPException
from ..common import contracts
from ..common.context import problem
from ..common.timeutil import parse_iso
from .evidence_preview import RegisteredPreview
from .unreviewed_preflight import validate_references

PREFIX = 'local-unreviewed-result:v1:'
NAMESPACE = 'local-unreviewed-result'
MAX_BYTES = 2 * 1024 * 1024
MAX_DEPTH = 32


def fail():
    raise problem(422, 'UNREVIEWED_HISTORY_INVALID', '未审核结果历史声明格式、版本或关联无效；未授予本地权限')


def candidate(value):
    if not isinstance(value, dict): return False
    return (value.get('category') == 'TimelineUnreviewed'
            or str(value.get('action') or '').startswith('timeline.unreviewed')
            or any(value.get(k) == 'timeline-unreviewed-result' for k in ('entity_type','entityType'))
            or any(isinstance(value.get(k),str) and value[k].startswith(NAMESPACE) for k in ('snapshot_ref','snapshotRef')))


def strict_json(text):
    nesting=0;quoted=False;escaped=False
    for char in text:
        if quoted:
            if escaped:escaped=False
            elif char=='\\':escaped=True
            elif char=='"':quoted=False
        elif char=='"':quoted=True
        elif char in '[{':
            nesting+=1
            if nesting>MAX_DEPTH:raise ValueError('depth')
        elif char in ']}':nesting-=1
    def pairs(items):
        out={}
        for key,value in items:
            if key in out: raise ValueError('duplicate')
            out[key]=value
        return out
    def finite(v):
        n=float(v)
        if not math.isfinite(n):raise ValueError('finite')
        return n
    value=json.loads(text,object_pairs_hook=pairs,parse_float=finite,
                     parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    def depth(v,n=0):
        if n>MAX_DEPTH:raise ValueError('depth')
        if isinstance(v,dict):
            for x in v.values():depth(x,n+1)
        elif isinstance(v,list):
            for x in v:depth(x,n+1)
        elif isinstance(v,str):v.encode('utf-8')
    depth(value)
    return value


def declaration(event,case_id):
    marker=event.get('snapshot_ref')
    if not isinstance(marker,str) or not marker.startswith(PREFIX):fail()
    raw=marker[len(PREFIX):]
    try:
        if len(raw.encode('utf-8'))>MAX_BYTES or any(c in raw for c in ('\u0085','\u2028','\u2029','\x0b','\x0c','\x1c','\x1d','\x1e')):raise ValueError()
        d=strict_json(raw)
        if contracts.errors('unreviewed-result-history',d):raise ValueError()
        integer_keys={'version','registeredSeq','byteLength','anchorCount','usedAnchorCount',
                      'manualAnchorCount','lineNumber','sourcesImported','tracks','linesRead','sentencesUsed'}
        def exact_ints(v):
            if isinstance(v,dict):
                for key,item in v.items():
                    if key in integer_keys and type(item) is not int:raise ValueError('strict integer')
                    exact_ints(item)
            elif isinstance(v,list):
                for item in v:exact_ints(item)
        exact_ints(d)

        if d['caseId']!=case_id:raise ValueError()
        for key,value in [('runId',d['runId']),('caseIncarnation',d['generationSnapshot']['caseIncarnation'])]:
            if str(uuid.UUID(value))!=value:raise ValueError()
        if (event.get('action')!='timeline.unreviewed.save' or event.get('category')!='TimelineUnreviewed'
                or event.get('entity_type')!='timeline-unreviewed-result' or event.get('entity_id')!=d['runId']
                or type(event.get('seq')) is not int or event['seq']<1):raise ValueError()
        if 'snapshotRef' in event or 'entityType' in event or 'entityId' in event:raise ValueError()
        for key in ('case_id','caseId'):
            if key in event and event[key]!=case_id:raise ValueError()
        if parse_iso(event['utc'])!=parse_iso(d['createdUtc']):raise ValueError()
        req=RegisteredPreview.model_validate(d['request'])
        if req.model_dump(mode='json')!=d['request']:raise ValueError('normalized declaration')
        snap=d['generationSnapshot'];out=d['serverPreview']
        if snap['caseId']!=case_id or out['caseId']!=case_id or out['result']['caseId']!=case_id:raise ValueError()
        if any(x['caseId']!=case_id for x in out['result']['conflicts']):raise ValueError()
        if 'caseEpochUtc' in out['result'] and parse_iso(out['result']['caseEpochUtc'])!=parse_iso(snap['caseEpochUtc']):raise ValueError()
        if parse_iso(snap['caseEpochUtc'])!=parse_iso(out['caseEpochUtc']):raise ValueError()
        sources=[x.evidenceId for x in req.sources]
        parents=[x for x in req.sources if x.parentReport]
        ids=set(sources)|{x.parentReport.evidenceId for x in parents}
        identities=snap['sourceIdentities']
        if [x['evidenceId'] for x in identities]!=sorted(ids):raise ValueError()
        byid={x['evidenceId']:x for x in identities}
        if len({x['incarnation'] for x in identities})!=len(identities):raise ValueError()
        if len({x['registeredSeq'] for x in identities})!=len(identities):raise ValueError()
        for x in identities:
            if x['caseId']!=case_id or x['caseIncarnation']!=snap['caseIncarnation']:raise ValueError()
            if str(uuid.UUID(x['incarnation']))!=x['incarnation']:raise ValueError()
        if [x['evidenceId'] for x in snap['sourceSnapshots']]!=sources:raise ValueError()
        def bound(v):
            x=byid[v['evidenceId']]
            if (v['sourceSha256']!=x['sourceSha256'] or v['registrationDigest']!=x['requestDigest']
                    or v['registeredUtc']!=x['registeredUtc']):raise ValueError()
        for x in snap['sourceSnapshots']:bound(x)
        if len(snap['reportSnapshots'])!=len(parents):raise ValueError()
        for x,source in zip(snap['reportSnapshots'],parents):
            if x['extractEvidenceId']!=source.evidenceId or x['evidenceId']!=source.parentReport.evidenceId or x['sourceSha256']!=source.parentReport.sourceSha256:raise ValueError()
            bound(x)
        if any(str(x['severity']).casefold()=='error' for x in out['result']['importDiagnostics']):raise ValueError()
        validate_references(out['result'],req)
        return d
    except (HTTPException,ValueError,TypeError,KeyError,OverflowError,RecursionError,UnicodeError):fail()


def validate_lines(lines,case_id):
    """Reject only reserved declarations; unrelated old events retain behavior."""
    seen=set()
    for line in lines:
        found=False
        def observe(items):
            nonlocal found
            # Keep duplicate marker values visible during detection, even if a
            # later ordinary field would shadow one in a permissive old reader.
            for key,value in items:
                if candidate({key:value}):found=True
            return dict(items)
        try:
            event=json.loads(line,object_pairs_hook=observe)
            if not found and not candidate(event):continue
            event=strict_json(line)
            d=declaration(event,case_id)
        except (ValueError,TypeError,KeyError,OverflowError,RecursionError,UnicodeError):fail()
        if d['runId'] in seen:fail()
        seen.add(d['runId'])
