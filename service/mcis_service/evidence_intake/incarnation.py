"""Local intake identity; neither imported history nor UUID is an approval."""
import json
import uuid
from sqlalchemy import Column, Integer, String, select
from ..db import Base
from ..common.context import problem
from ..audit import service as audit
from ..audit.models import AuditEventRow
from ..cases.incarnation import CaseIncarnationRow, current as current_case
from ..evidence.models import CustodyEventRow

PREFIX = 'local-source-incarnation:v1:'

class SourceIncarnationRow(Base):
    __tablename__ = 'source_local_incarnations'
    case_id = Column(String(64), primary_key=True)
    evidence_id = Column(String(64), primary_key=True)
    incarnation = Column(String(36), nullable=False, unique=True)
    case_incarnation = Column(String(36), nullable=False)
    request_digest = Column(String(64), nullable=False)
    source_sha256 = Column(String(64), nullable=False)
    registered_seq = Column(Integer, nullable=False)
    registered_utc = Column(String(32), nullable=False)
    audit_seq = Column(Integer, nullable=False)


def declaration(row):
    return {'version': 1, 'caseId': row.case_id, 'evidenceId': row.evidence_id,
            'incarnation': row.incarnation, 'caseIncarnation': row.case_incarnation,
            'requestDigest': row.request_digest, 'sourceSha256': row.source_sha256,
            'registeredSeq': row.registered_seq, 'registeredUtc': row.registered_utc}


def marker(value):
    return PREFIX + json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def allocate_for_intake(s, case_id, reg, digest, operator, role):
    # Never backfill an old case or derive authority from a historical marker.
    if s.get(CaseIncarnationRow, case_id) is None:
        return
    case_identity = current_case(s, case_id)
    if s.get(SourceIncarnationRow, (case_id, reg.evidence_id)) is not None:
        raise problem(409, 'SOURCE_INCARNATION_EXISTS', '来源代次已存在，未覆盖')
    row = SourceIncarnationRow(case_id=case_id, evidence_id=reg.evidence_id,
        incarnation=str(uuid.uuid4()), case_incarnation=case_identity,
        request_digest=digest, source_sha256=reg.sha256,
        registered_seq=reg.seq, registered_utc=reg.utc)
    event = audit.append(s, case_id=case_id, operator=operator, role=role,
        action='source.incarnation', category='Custody', command='分配本地来源代次',
        entity_type='evidence', entity_id=reg.evidence_id, snapshot_ref=marker(declaration(row)))
    row.audit_seq = event.seq
    s.add(row)
    s.flush()


def validate_archive_identities(s, case_id):
    rows = list(s.scalars(select(SourceIncarnationRow).where(SourceIncarnationRow.case_id == case_id)))
    if not rows:
        return
    case_identity = current_case(s, case_id)
    if not audit.verify_chain(audit.all_lines(s, case_id))['valid']:
        raise problem(409, 'SOURCE_INCARNATION_INTEGRITY', '来源代次审计链不完整')
    for row in rows:
        event = s.scalars(select(AuditEventRow).where(AuditEventRow.case_id == case_id,
                                                      AuditEventRow.seq == row.audit_seq)).first()
        reg = s.scalars(select(CustodyEventRow).where(CustodyEventRow.case_id == case_id,
                                                      CustodyEventRow.seq == row.registered_seq)).first()
        try:
            line = json.loads(event.line) if event is not None else {}
            valid = (str(uuid.UUID(row.incarnation)) == row.incarnation
                and row.case_incarnation == case_identity
                and reg is not None and reg.kind == 'Register' and reg.evidence_id == row.evidence_id
                and reg.sha256 == row.source_sha256 and reg.utc == row.registered_utc
                and event.action == line.get('action') == 'source.incarnation'
                and event.entity_id == line.get('entity_id') == row.evidence_id
                and line.get('seq') == row.audit_seq
                and line.get('snapshot_ref') == marker(declaration(row)))
        except (ValueError, TypeError, AttributeError):
            valid = False
        if not valid:
            raise problem(409, 'SOURCE_INCARNATION_INTEGRITY', '来源代次与完整历史声明不一致')


def current(ctx, s, case_id, evidence_id):
    """Internal prerequisite only. Authorize and re-read bytes; no implicit role grant."""
    from .router import authorize, load_receipt
    authorize(ctx, s, case_id)
    row = s.get(SourceIncarnationRow, (case_id, evidence_id))
    if row is None:
        raise problem(409, 'SOURCE_INCARNATION_MISSING', '此来源未分配本地代次，未从历史自动激活')
    validate_archive_identities(s, case_id)
    found = load_receipt(ctx, s, case_id, row.request_digest)
    if found is None:
        raise problem(409, 'SOURCE_INCARNATION_INTEGRITY', '来源登记回执缺失')
    receipt, _ = found
    if (receipt['evidenceId'] != evidence_id or receipt['sourceSha256'] != row.source_sha256
            or receipt['evidence']['needsReview'] or receipt['evidence']['status'] == 'Mismatch'):
        raise problem(409, 'SOURCE_INCARNATION_STALE', '来源已改变或待复核，未作为当前来源')
    return declaration(row)
