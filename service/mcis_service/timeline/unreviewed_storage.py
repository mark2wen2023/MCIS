"""Internal server-only unreviewed runs. No API, approval or timeline mutation."""
import hashlib
import json
import uuid
from types import SimpleNamespace
from sqlalchemy import Column, Integer, String, UniqueConstraint, select
from ..db import Base
from ..common.context import problem
from ..common.timeutil import iso, now_utc
from ..audit import service as audit
from ..audit.models import AuditEventRow
from ..cases.incarnation import current as current_case, CaseIncarnationRow
from ..reports.access import require_content
from .evidence_preview import RegisteredPreview
from .align_preview import preview_alignment
from .unreviewed_preflight import capture, validate_references
from .unreviewed_access import ensure_archive_capacity
from .unreviewed_history import PREFIX, declaration, strict_json, validate_lines


class UnreviewedRunRow(Base):
    __tablename__='timeline_local_unreviewed_runs'
    case_id=Column(String(64),primary_key=True)
    run_id=Column(String(36),primary_key=True,unique=True)
    case_incarnation=Column(String(36),nullable=False)
    operation_id=Column(String(36),nullable=False)
    audit_seq=Column(Integer,nullable=False)
    input_digest=Column(String(64),nullable=False)
    __table_args__=(UniqueConstraint('case_id','case_incarnation','operation_id'),
                   UniqueConstraint('case_id','audit_seq'))


def conflict(code='UNREVIEWED_RUN_INTEGRITY'):
    raise problem(409,code,'未审核结果记录、请求或当前来源不一致，未重建或批准')


def canonical(value):
    return json.dumps(value,ensure_ascii=True,allow_nan=False,sort_keys=True,separators=(',',':'))


def input_digest(request,operator,role):
    return hashlib.sha256(canonical({'profile':'unreviewed-run-scope-v1','request':request,
                                    'operator':operator,'role':role}).encode()).hexdigest()


def validate_local_history(session,case_id):
    rows=list(session.scalars(select(UnreviewedRunRow).where(UnreviewedRunRow.case_id==case_id)))
    lines=audit.all_lines(session,case_id)
    validate_lines(lines,case_id)
    # Decode before marker detection: escaped prefix spelling cannot conceal an
    # orphaned current-generation declaration. Legacy history is not authority.
    decoded=[json.loads(line) for line in lines]
    if not rows and not any(isinstance(x.get('snapshot_ref'),str) and x['snapshot_ref'].startswith(PREFIX) for x in decoded):return {}
    if session.get(CaseIncarnationRow,case_id) is None:
        if rows:conflict()
        return {}
    if not audit.verify_chain(lines)['valid']:conflict()
    identity=current_case(session,case_id)
    events={json.loads(line)['seq']:json.loads(line) for line in lines}
    local={}
    for seq,event in events.items():
        if isinstance(event.get('snapshot_ref'),str) and event['snapshot_ref'].startswith(PREFIX):
            d=declaration(event,case_id)
            if d['generationSnapshot']['caseIncarnation']==identity and d.get('operationId'):
                local[d['runId']]=(seq,event,d)
    if set(local)!={row.run_id for row in rows}:conflict()
    verified={}
    for row in rows:
        seq,event,d=local[row.run_id]
        if 'processing' not in d:conflict()
        if (row.audit_seq!=seq or row.case_incarnation!=identity or row.operation_id!=d['operationId']
                or row.input_digest!=input_digest(d['request'],event['operator'],event['role'])):conflict()
        verified[row.operation_id]=(row,d,event)
    return verified


def replay(session,ctx,case_id,operation_id,request,snapshot):
    records=validate_local_history(session,case_id)
    found=records.get(operation_id)
    if not found:return None
    row,d,event=found
    if row.input_digest!=input_digest(request,ctx.operator,ctx.role):conflict('UNREVIEWED_OPERATION_CONFLICT')
    if d['generationSnapshot']!=snapshot:conflict('UNREVIEWED_RUN_STALE')
    return {'runId':d['runId'],'saved':True,'status':'unreviewed','replayed':True,'declaration':d}


def save_unreviewed(ctx,case_id,request,operation_id,*,_authorize=None,expected_selection=None):
    # operation ID selects an attempt; it never supplies output or authority.
    try:
        if not isinstance(operation_id,str) or str(uuid.UUID(operation_id))!=operation_id:raise ValueError()
        if not isinstance(ctx.operator,str) or not 1<=len(ctx.operator)<=200 or any(ord(c)<32 or c in '\u0085\u2028\u2029' for c in ctx.operator):raise ValueError()
        ctx.operator.encode('utf-8')
    except (ValueError,TypeError,AttributeError,UnicodeError):
        raise problem(422,'UNREVIEWED_OPERATION_INPUT','需要规范操作UUID与有效操作人') from None
    ctx=SimpleNamespace(role=ctx.role,operator=ctx.operator,db=ctx.db,settings=ctx.settings)
    frozen=RegisteredPreview.model_validate_json(request.model_dump_json())
    request_doc=frozen.model_dump(mode='json')
    expected_selection=json.loads(canonical(expected_selection)) if expected_selection is not None else None
    authority_before=None
    with ctx.db.session() as session:
        if _authorize is not None:
            authority_before=_authorize(session)
            ctx.operator=authority_before.subject_id; ctx.role=authority_before.role
        require_content(session,case_id,ctx.role)
        resolved,before=capture(ctx,session,case_id,frozen)
        if expected_selection is not None and expected_selection!=selection_snapshot(before):
            conflict('UNREVIEWED_SELECTION_CHANGED')
        if _authorize is not None and _authorize(session)!=authority_before:conflict('UNREVIEWED_AUTHORITY_CHANGED')
        old=replay(session,ctx,case_id,operation_id,request_doc,before)
        if old:return old
    output=preview_alignment(case_id,resolved,ctx)
    validate_references(output['result'],frozen)
    if any(str(x['severity']).casefold()=='error' for x in output['result']['importDiagnostics']):
        raise problem(422,'TIMELINE_SOURCE_CORE_DIAGNOSTIC','核心报告来源导入错误，未保存结果')
    with ctx.db.session() as session:
        if _authorize is not None:
            authority_after=_authorize(session)
            if authority_after!=authority_before:conflict('UNREVIEWED_AUTHORITY_CHANGED')
        require_content(session,case_id,ctx.role)
        _,after=capture(ctx,session,case_id,frozen)
        if before!=after:conflict('UNREVIEWED_RUN_STALE')
        if _authorize is not None and _authorize(session)!=authority_before:conflict('UNREVIEWED_AUTHORITY_CHANGED')
        old=replay(session,ctx,case_id,operation_id,request_doc,after)
        if old:return old
        run_id=str(uuid.uuid4());created=iso(now_utc())
        d={'version':1,'runId':run_id,'operationId':operation_id,'caseId':case_id,
           'createdUtc':created,'status':'unreviewed','request':request_doc,
           'generationSnapshot':after,'serverPreview':output,
           'processing':{'serviceProtocolVersion':'mcis-internal-unreviewed-save-v1',
                         'alignmentAdapterVersion':'registered-csv-preflight-v1',
                         'coreProtocolVersion':'mcis-core-align-json-v1',
                         'coreImplementationVersionStatus':'not_attested'}}
        # append and index are in this final reserved writer transaction; any
        # subsequent schema/budget/flush/commit error rolls both back.
        event=audit.append(session,case_id=case_id,operator=ctx.operator,role=ctx.role,
            action='timeline.unreviewed.save',category='TimelineUnreviewed',command='保存未审核计算结果',
            entity_type='timeline-unreviewed-result',entity_id=run_id,utc=created,snapshot_ref=PREFIX+canonical(d))
        declaration(strict_json(event.line),case_id)
        all_lines=audit.all_lines(session,case_id)
        ensure_archive_capacity(all_lines[:-1],all_lines[-1])
        session.add(UnreviewedRunRow(case_id=case_id,run_id=run_id,case_incarnation=after['caseIncarnation'],
            operation_id=operation_id,audit_seq=event.seq,input_digest=input_digest(request_doc,ctx.operator,ctx.role)))
        session.flush()
        result={'runId':run_id,'saved':True,'status':'unreviewed','replayed':False,'declaration':d}
    # Return only after successful commit. Unknown delivery can be retried using
    # the same operation ID, but only under unchanged scope/permissions/versions.
    return result


def save_authenticated_unreviewed(db,settings,token,case_id,request,operation_id,expected_selection=None):
    """Trusted-host entry. No HTTP header, actor, role or imported grant accepted.

    Legacy save_unreviewed remains an INTERNAL trusted-call compatibility entry;
    neither function is mounted in the closed protected HTTP app.
    """
    from ..identity.local import authorize_save
    ctx=SimpleNamespace(db=db,settings=settings,operator='authenticated',role='')
    return save_unreviewed(ctx,case_id,request,operation_id,
        _authorize=lambda session:authorize_save(session,token,case_id),expected_selection=expected_selection)


def read_authenticated_unreviewed(db, settings, token, case_id, run_id):
    """Read current local result only; never recompute, activate history or approve.

    The reserved SQLite transaction holds identity/content checks through response
    materialization. Revocation after that decision cannot recall already sent data.
    """
    from ..identity.local import authorize_read
    with db.session() as session:
        authority = authorize_read(session, token, case_id)
        require_content(session, case_id, authority.role)
        records = validate_local_history(session, case_id)
        found = next((d for row,d,event in records.values() if row.run_id == run_id), None)
        if found is None:
            raise problem(404, 'UNREVIEWED_RUN_NOT_FOUND', '没有可读取的当前本地结果')
        request = RegisteredPreview.model_validate(found['request'])
        ctx = SimpleNamespace(db=db, settings=settings, operator=authority.subject_id, role=authority.role)
        _, snapshot = capture(ctx, session, case_id, request, write=False)
        if snapshot != found['generationSnapshot']: conflict('UNREVIEWED_RUN_STALE')
        # Materialize only the reviewed result schema, not audit/operator/session data.
        response = json.loads(canonical({'runId':found['runId'], 'caseId':case_id,
            'status':'unreviewed', 'observationApproval':'not_assessed',
            'usableAsWriteCredential':False, 'createdUtc':found['createdUtc'],
            'request':found['request'], 'generationSnapshot':snapshot,
            'serverPreview':found['serverPreview'], 'processing':found['processing']}))
        if authorize_read(session, token, case_id) != authority:
            conflict('UNREVIEWED_AUTHORITY_CHANGED')
    return response


def selection_snapshot(snapshot):
    """Caller-visible version precondition, never an authorization credential."""
    return {'caseId':snapshot['caseId'],'caseIncarnation':snapshot['caseIncarnation'],
        'caseEpochUtc':snapshot['caseEpochUtc'],
        'sources':sorted([{'evidenceId':x['evidenceId'],'sourceSha256':x['sourceSha256'],
            'registrationDigest':x['requestDigest'],'sourceIncarnation':x['incarnation']}
            for x in snapshot['sourceIdentities']],key=lambda x:x['evidenceId'])}
