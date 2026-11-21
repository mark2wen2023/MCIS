"""Internal synthetic pilot only. No route, report writes, binding store or export.
Trusted bootstrap owns this object, the frozen sentence key and pin; never build
it from request JSON. Both independent session grants are rechecked per call.
"""
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

CASE = 'SYN-XREPO-001'
UTC = '2026-02-01T12:01:40.000Z'
OPERATION = 'report.reference.prepare'

class PrepareUnavailable(ValueError):
    pass

def _generation_event(row, verified_lines):
    """Bind relational projection to its verified line; case scope remains relational."""
    if row.line not in verified_lines:
        raise PrepareUnavailable('generation_audit_unavailable')
    try:
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError('duplicate field')
                result[key] = value
            return result
        record = json.loads(row.line, object_pairs_hook=pairs)
        if (type(record) is not dict or type(record.get('seq')) is not int
                or record['seq'] != row.seq
                or any(record.get(field) != getattr(row, field)
                       for field in ('action', 'category', 'entity_type', 'entity_id'))):
            raise ValueError('projection mismatch')
        return {'caseId': row.case_id, 'seq': record['seq'],
                'action': record['action'], 'category': record['category'],
                'entityType': record['entity_type'], 'entityId': record['entity_id'],
                'snapshotRef': record.get('snapshot_ref')}
    except (ValueError, TypeError, KeyError, RecursionError):
        raise PrepareUnavailable('generation_audit_inconsistent') from None


class PilotTrajectoryPrepare:
    def __init__(self, *, enabled=False, sessions=None, db=None, settings=None, subject=None, key=None, pin=None):
        self.enabled=enabled is True
        self.sessions,self.db,self.settings,self.subject=sessions,db,settings,subject
        self.key,self.pin=deepcopy(key),deepcopy(pin)

    async def prepare(self, credential):
        from ..common.local_review_pilot import PilotSessions
        from ..common.context import Ctx
        if not self.enabled or type(self.sessions) is not PilotSessions or not self.subject or self.db is None:
            raise PrepareUnavailable('pilot_unconfigured')
        async def authorize():
            a=await self.sessions.verify(credential,CASE,OPERATION)
            b=await self.sessions.verify(credential,CASE,'evidence.original.access')
            if a is None or b is None or a.subject!=self.subject or b.subject!=a.subject or b.role!=a.role:
                raise PrepareUnavailable('pilot_grant_required')
            return a
        grant=await authorize()
        key,pin=self.key,self.pin
        if (type(key) is not tuple or len(key)!=4 or key[0]!=CASE or type(pin) is not dict
                or set(pin)!={'caseId','evidenceId','requestDigest','sourceSha256'} or pin['caseId']!=CASE):
            raise PrepareUnavailable('fixed_scope_required')
        from ..db import WRITE_LOCK,get_doc
        from ..cases.service import load_case
        from ..audit import service as audit
        from ..audit.models import AuditEventRow
        from ..redaction.gateway import require
        from ..evidence_intake.router import _read_original_for_access
        from ..trajectory_exchange.validation import validate_trajectory
        from ..trajectory_exchange.registered_pair import _object
        from ..trajectory_exchange.registered_query import _point_from_committed_original,_stamp
        from ..common.contracts import validate
        from .access import begin,require_content
        from .models import ReportAuditRow
        from .generation_snapshot import generation_sentence
        from sqlalchemy import select
        ctx=Ctx(role=grant.role,operator=grant.subject,request=SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db=self.db,settings=self.settings))))
        # Same reserved-writer convention. Errors propagate outside the owned scope.
        with WRITE_LOCK:
            with self.db.session() as session:
                begin(session)
                require_content(session,CASE,grant.role)
                require(ctx,session,CASE,'report_draft')
                require(ctx,session,CASE,'audit')
                case=load_case(session,CASE)
                if case.get('isFictionalDemo') is not True:raise PrepareUnavailable('synthetic_case_required')
                snapshot=get_doc(session,ReportAuditRow,CASE,key[1])
                if not snapshot:raise PrepareUnavailable('generation_unavailable')
                if snapshot.get('snapshotId') != key[1]:raise PrepareUnavailable('generation_identity_mismatch')
                verified_lines=audit.all_lines(session,CASE)
                if not audit.verify_chain(verified_lines)['valid']:raise PrepareUnavailable('audit_invalid')
                row=session.scalars(select(AuditEventRow).where(AuditEventRow.case_id==CASE,AuditEventRow.seq==snapshot.get('auditSeq'))).one_or_none()
                if row is None:raise PrepareUnavailable('generation_audit_unavailable')
                frozen=generation_sentence(case_id=CASE,report_id=snapshot.get('reportId'),snapshot=snapshot,
                    audit_event=_generation_event(row,verified_lines),section_id=key[2],sentence_id=key[3],validate_contract=validate)
                receipt,raw=_read_original_for_access(ctx,session,CASE,pin['requestDigest'],'Synthetic pilot pending trajectory reference')
                if any(receipt.get(k)!=v for k,v in pin.items()) or type(raw) is not bytes or len(raw)>4*1024*1024 or hashlib.sha256(raw).hexdigest()!=pin['sourceSha256']:
                    raise PrepareUnavailable('original_pin_mismatch')
                try:
                    def invalid(_):raise ValueError('nonfinite')
                    doc=json.loads(raw.decode('utf-8'),object_pairs_hook=_object,parse_constant=invalid)
                    verdict=validate_trajectory(doc)
                    point=_point_from_committed_original({'pin':pin,'document':doc},_stamp(UTC))
                except (ValueError,TypeError,KeyError,RecursionError,UnicodeError):raise PrepareUnavailable('original_invalid') from None
                if (doc['caseId']!=CASE or doc['vessel']['vesselId']!='SYN-VESSEL-A' or not verdict['canReplaySynchronously']
                    or point['status']!='input_point' or point['locator']!={'jsonPointer':'/points/7'}
                    or doc['points'][7]['pointId']!='A-t100' or point['position']['kind']!='recorded'):
                    raise PrepareUnavailable('fixed_point_unavailable')
                # Session expiry/revocation checked again before commit. Not atomic
                # with an independent session provider; later revocation remains possible.
                if await authorize()!=grant:raise PrepareUnavailable('session_changed')
                result={'status':'proposed_reference_pending_human_review','caseId':CASE,
                    'generationSnapshotId':frozen['snapshotId'],'sectionId':key[2],'sentenceId':key[3],
                    'original':deepcopy(pin),'alignedUtc':UTC,'locator':deepcopy(point['locator']),
                    'positionKind':point['position']['kind'],'saved':False,'sourceVerified':False}
        # Only committed Access allows a result. No report/snapshot/binding mutation.
        return result
