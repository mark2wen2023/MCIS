"""Internal generation prerequisite, NOT a save endpoint or admission token."""
import json
from ..common.context import problem
from ..common.timeutil import parse_iso
from ..cases.service import load_case
from ..cases.incarnation import current as case_identity
from ..evidence_intake.incarnation import current as source_identity
from ..redaction.gateway import require
from ..reports.access import begin
from .evidence_preview import RegisteredPreview, resolve
from .align_preview import preview_alignment

MAX_ENVELOPE_BYTES = 2 * 1024 * 1024


def capture(ctx, session, case_id, request, *, write=True):
    begin(session)
    require(ctx, session, case_id, 'timeline', write=write)
    resolved, sources, parents = resolve(ctx, session, case_id, request)
    incarnation = case_identity(session, case_id)
    ids = sorted({s.evidenceId for s in request.sources} |
                 {s.parentReport.evidenceId for s in request.sources if s.parentReport})
    identities = [source_identity(ctx, session, case_id, eid) for eid in ids]
    return resolved, {'caseId': case_id, 'caseIncarnation': incarnation,
                     'caseEpochUtc': load_case(session, case_id)['caseEpochUtc'],
                     'sourceIdentities': identities, 'sourceSnapshots': sources,
                     'reportSnapshots': parents}


def validate_references(result, request):
    ids = {s.evidenceId for s in request.sources}
    try:
        for row in result['clockOffsets']:
            if row['sourceId'] not in ids or row['referenceSourceId'] not in ids | {'GNSS'}:
                raise ValueError()
            if row['viaSourceId'] is not None and row['viaSourceId'] not in ids | {'GNSS'}:
                raise ValueError()
        for row in result['calibration']['sources']:
            if row['sourceId'] not in ids: raise ValueError()
            if row['viaSourceId'] is not None and row['viaSourceId'] not in ids | {'GNSS'}: raise ValueError()
        if not set(result['calibration']['uncalibratedSources']).issubset(ids): raise ValueError()
        for row in result['importDiagnostics'] + result['conflictDiagnostics']:
            if row['sourceId'] is not None and row['sourceId'] not in ids: raise ValueError()
        conflicts = set()
        for row in result['conflicts']:
            if row['conflictId'] in conflicts: raise ValueError()
            conflicts.add(row['conflictId'])
            if row['a']['sourceLabel'] == row['b']['sourceLabel']: raise ValueError()
            for side in ('a', 'b'):
                obs = row[side]
                if obs['sourceLabel'] not in ids: raise ValueError()
                if obs.get('evidenceId') is not None and obs['evidenceId'] != obs['sourceLabel']: raise ValueError()
    except (KeyError, ValueError, TypeError):
        raise problem(502, 'TIMELINE_RESULT_REFERENCES', '核心输出引用不属于本次来源，未采用结果') from None


def compute_unreviewed(ctx, case_id, request):
    # Copy and revalidate; retain no caller-owned mutable DTO across core work.
    request = RegisteredPreview.model_validate_json(request.model_dump_json())
    frozen_request = request.model_dump(mode='json')
    with ctx.db.session() as session:
        resolved, before = capture(ctx, session, case_id, request)
    # Only these captured, checked bytes enter the server core; no caller result.
    output = preview_alignment(case_id, resolved, ctx)
    validate_references(output['result'], request)
    if any(str(d.get('severity', '')).casefold() == 'error'
           for d in output['result']['importDiagnostics']):
        raise problem(422, 'TIMELINE_SOURCE_CORE_DIAGNOSTIC', '核心报告导入错误，未生成未审核结果')
    # Do not mutate this object or accept its return value as later write authority.
    with ctx.db.session() as session:
        _, after = capture(ctx, session, case_id, request)
        if before != after or parse_iso(output['caseEpochUtc']) != parse_iso(before['caseEpochUtc']):
            raise problem(409, 'TIMELINE_RESULT_SOURCE_CHANGED', '计算期间案件或来源代次改变，未生成结果')
        envelope = {'profile': 'mcis-unreviewed-preflight-v1', 'persisted': False,
                    'observationApproval': 'not_assessed', 'usableAsWriteCredential': False,
                    'request': frozen_request, 'generationSnapshot': before,
                    'serverPreview': output}
        # Engineering bound, not a signed/trusted serialization or save protocol.
        encoded = json.dumps(envelope, ensure_ascii=False, allow_nan=False, sort_keys=True,
                             separators=(',', ':')).encode('utf-8')
        if len(encoded) > MAX_ENVELOPE_BYTES:
            raise problem(413, 'TIMELINE_RESULT_LIMIT', '未审核计算封套超过2MiB，未截断或保存')
        return json.loads(encoded)
