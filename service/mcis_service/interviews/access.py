"""Original interview content gate. No claim of complete redaction/authentication."""
from fastapi import HTTPException
from sqlalchemy import select
from ..common.context import problem
from ..reports.access import begin, NoStoreRoute, require_content as report_policy_check
from ..redaction.gateway import level_of, filter_evidence
from ..evidence.models import EvidenceRow


def denied():
    raise problem(403, 'FORBIDDEN', '完整笔录内容不可访问')


def require_content(s, case_id, role, *, write=False):
    try: policy = report_policy_check(s, case_id, role)
    except HTTPException as exc:
        if exc.status_code == 403: denied()
        raise
    if write and level_of(policy, role, 'testimony') != 'ReadWrite': denied()
    return policy


def source(s, case_id, role, evidence_id):
    policy = require_content(s, case_id, role)
    row = s.scalars(select(EvidenceRow).where(EvidenceRow.case_id == case_id, EvidenceRow.key == evidence_id)).first()
    if row is None or not filter_evidence([row.doc], role, policy): denied()
    return row.doc


def document(s, ctx, doc, *, write=False):
    require_content(s, doc['caseId'], ctx.role, write=write)
    if doc.get('evidenceId'):
        registered = source(s, doc['caseId'], ctx.role, doc['evidenceId'])
        if doc.get('sourceSha256') and doc['sourceSha256'] != registered.get('sha256'):
            raise problem(409, 'INTERVIEW_SOURCE_CHANGED', '笔录绑定来源与当前登记不一致，未重新绑定')
    if write and doc.get('signed') is True:
        raise problem(409, 'INTERVIEW_SIGNED', '已签署笔录不可通过此接口修改')
    return doc


def draft_record_ids(d):
    ids=set()
    def walk(value, depth=0):
        if depth > 32: denied()
        if isinstance(value,dict):
            if 'recordId' in value:
                if not isinstance(value['recordId'],str) or not value['recordId']: denied()
                ids.add(value['recordId'])
            for v in value.values(): walk(v,depth+1)
        elif isinstance(value,list):
            for v in value: walk(v,depth+1)
    walk(d.get('payload',{})); walk(d.get('citations',[]))
    if d.get('targetEntityType') in ('interviewStatements','interview') and d.get('targetEntityId'):
        ids.add(d['targetEntityId'])
    return ids


def draft_related(d):
    citations=d.get('citations') or []
    span_marked=any(isinstance(c,dict) and 'round' in c for c in citations)
    payload=d.get('payload') or {}
    span_marked=span_marked or isinstance(payload,dict) and any(k in payload for k in ('span','statements'))
    return span_marked or bool(draft_record_ids(d)) or d.get('targetEntityType') in ('statement','interviewStatements','interview','crossCheck') or d.get('kind')=='statement_extraction'


def protect_draft(s, ctx, case_id, d, *, write=False):
    if not draft_related(d): return
    require_content(s,case_id,ctx.role,write=write)
    from .service import load
    ids=draft_record_ids(d)
    if not ids: denied()
    for rid in ids: document(s,ctx,load(s,case_id,rid),write=write)
    for citation in d.get('citations',[]):
        if citation.get('evidenceId'): source(s,case_id,ctx.role,citation['evidenceId'])


def event_related(e):
    import json
    def marker(v):
        return (v.get('category') == 'Interview' or v.get('entityType', v.get('entity_type')) in ('interview','statement','crossCheck')
            or str(v.get('action') or '').startswith(('interview.', 'statement.', 'testimony.')))
    if marker(e): return True
    if 'line' in e:
        def pairs(values):
            result={}
            for k,v in values:
                if k in result: raise ValueError()
                result[k]=v
            return result
        def invalid(_): raise ValueError()
        try: raw=json.loads(e['line'],object_pairs_hook=pairs,parse_constant=invalid)
        except (ValueError,TypeError,RecursionError): return True
        if not isinstance(raw,dict): return True
        if any(k in raw and not isinstance(raw[k],str) for k in ('category','action','entity_type','entityType')): return True
        return marker(raw)
    return False


def protect_events(s, case_id, role, events):
    from ..agents.models import AgentDraftRow
    from types import SimpleNamespace
    for e in events:
        if event_related(e):
            require_content(s,case_id,role)
            from .models import InterviewRow
            for row in s.scalars(select(InterviewRow).where(InterviewRow.case_id==case_id)):
                document(s,SimpleNamespace(role=role),row.doc)
        # Agent review summaries may carry original quotations; resolve their
        # target or conservatively gate orphaned/unclassifiable draft events.
        import json
        versions=[e]
        if 'line' in e:
            try:
                raw=json.loads(e['line'])
                if isinstance(raw,dict): versions.append(raw)
            except (ValueError,TypeError,RecursionError): pass
        for version in versions:
            if version.get('category')!='Agent': continue
            et=version.get('entityType',version.get('entity_type'))
            eid=version.get('entityId',version.get('entity_id'))
            if et=='agentDraft':
                row=s.scalars(select(AgentDraftRow).where(AgentDraftRow.case_id==case_id,AgentDraftRow.key==eid)).first()
                if row is None: require_content(s,case_id,role)
                else: protect_draft(s,SimpleNamespace(role=role),case_id,row.doc)
            elif et not in ('interview',):
                require_content(s,case_id,role)
    return events


def protect_package(s, case_id, role):
    from .models import InterviewRow
    from ..agents.models import AgentDraftRow
    from ..audit.models import AuditEventRow
    from ..audit.service import to_doc
    from types import SimpleNamespace
    ctx=SimpleNamespace(role=role)
    begin(s)
    for row in s.scalars(select(InterviewRow).where(InterviewRow.case_id==case_id)):
        document(s,ctx,row.doc)
    for row in s.scalars(select(AgentDraftRow).where(AgentDraftRow.case_id==case_id)):
        protect_draft(s,ctx,case_id,row.doc)
    events=(to_doc(row) for row in s.scalars(select(AuditEventRow).where(AuditEventRow.case_id==case_id)))
    protect_events(s,case_id,role,events)
