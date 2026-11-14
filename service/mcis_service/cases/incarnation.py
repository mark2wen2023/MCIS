"""Local case identity only; imported audit markers are never authority."""
import json
import uuid
from sqlalchemy import Column, String, Integer
from ..db import Base
from ..common.context import problem
from ..common.timeutil import iso,now_utc

PREFIX='local-case-incarnation:v1:'

class CaseIncarnationRow(Base):
    __tablename__='case_local_incarnations'
    case_id=Column(String(64),primary_key=True)
    incarnation=Column(String(36),nullable=False,unique=True)
    origin=Column(String(16),nullable=False)
    created_utc=Column(String(32),nullable=False)
    audit_seq=Column(Integer,nullable=False)


def allocate(session,case_id,origin):
    if origin not in ('created','imported'):raise ValueError('origin')
    if session.get(CaseIncarnationRow,case_id) is not None:
        raise problem(409,'CASE_INCARNATION_EXISTS','本地案件代次已存在，未覆盖')
    # Allocation is never a lookup/migration of imported audit claims.
    return {'version':1,'caseId':case_id,'incarnation':str(uuid.uuid4()),
            'origin':origin,'createdUtc':iso(now_utc())}


def marker(value):
    return PREFIX+json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))


def persist(session,value,event):
    session.add(CaseIncarnationRow(case_id=value['caseId'],incarnation=value['incarnation'],
        origin=value['origin'],created_utc=value['createdUtc'],audit_seq=event.seq))
    session.flush()


def current(session,case_id):
    """Missing legacy identity fails closed; no read-time backfill."""
    row=session.get(CaseIncarnationRow,case_id)
    if row is None:raise problem(409,'CASE_INCARNATION_MISSING','旧案件尚无本地代次；未自动授予可信状态')
    validate_archive_identity(session,case_id)
    return row.incarnation


def validate_archive_identity(session,case_id):
    """All current identity fields are preserved in an existing full audit line."""
    from sqlalchemy import select
    from ..audit.models import AuditEventRow
    from ..audit import service as audit
    from .models import CaseRow
    row=session.get(CaseIncarnationRow,case_id)
    if row is None:return  # Legacy case remains exportable, not upgraded.
    event=session.scalars(select(AuditEventRow).where(AuditEventRow.case_id==case_id,AuditEventRow.seq==row.audit_seq)).first()
    expected={'version':1,'caseId':case_id,'incarnation':row.incarnation,'origin':row.origin,'createdUtc':row.created_utc}
    action={'created':'case.create','imported':'package.import'}.get(row.origin)
    try:
        valid=(session.scalars(select(CaseRow).where(CaseRow.case_id==case_id)).first() is not None
               and str(uuid.UUID(row.incarnation))==row.incarnation and event is not None
               and event.action==action and event.entity_id==case_id
               and json.loads(event.line).get('action')==action
               and json.loads(event.line).get('entity_id')==case_id
               and json.loads(event.line).get('seq')==row.audit_seq
               and json.loads(event.line).get('snapshot_ref')==marker(expected)
               and audit.verify_chain(audit.all_lines(session,case_id))['valid'])
    except (ValueError,TypeError,AttributeError):valid=False
    if not valid:raise problem(409,'CASE_INCARNATION_INTEGRITY','本地代次与完整审计不一致，未继续')
