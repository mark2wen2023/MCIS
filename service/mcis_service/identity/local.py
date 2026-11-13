"""Server-only local identity; archive documents and request roles confer no authority.

Provisioning requires an already trusted host administrator. These functions are
not HTTP endpoints, seed hooks, or an identity-provider implementation.
"""
from dataclasses import dataclass
import hashlib
import secrets
import time
import threading
import uuid
from sqlalchemy import Column, String, Integer, Boolean
from ..db import Base
from ..reports.access import begin
from ..cases.incarnation import current
from ..common.context import problem


class Subject(Base):
    __tablename__ = 'identity_local_subjects'
    subject_id = Column(String(36), primary_key=True)
    enabled = Column(Boolean, nullable=False)
    revision = Column(Integer, nullable=False)


class SessionRecord(Base):
    __tablename__ = 'identity_local_sessions'
    token_hash = Column(String(64), primary_key=True)
    subject_id = Column(String(36), nullable=False)
    expires_at = Column(Integer, nullable=False)
    revoked = Column(Boolean, nullable=False)
    revision = Column(Integer, nullable=False)


class Membership(Base):
    __tablename__ = 'identity_local_memberships'
    subject_id = Column(String(36), primary_key=True)
    case_incarnation = Column(String(36), primary_key=True)
    case_id = Column(String(64), nullable=False)
    role = Column(String(32), nullable=False)
    can_save_unreviewed = Column(Boolean, nullable=False)
    enabled = Column(Boolean, nullable=False)
    revision = Column(Integer, nullable=False)


@dataclass(frozen=True)
class Authority:
    subject_id: str
    role: str
    scope: tuple


def denied():
    raise problem(403, 'LOCAL_AUTHORITY_DENIED', '身份、会话或本地案件授权无效')


def create_subject(session):
    begin(session)
    subject_id = str(uuid.uuid4())
    session.add(Subject(subject_id=subject_id, enabled=True, revision=1))
    session.flush()
    return subject_id


def issue_session(session, subject_id, *, lifetime_seconds=3600):
    begin(session)
    subject = session.get(Subject, subject_id)
    if subject is None or not subject.enabled: denied()
    if type(lifetime_seconds) is not int or not 1 <= lifetime_seconds <= 86400:
        raise ValueError('session lifetime must be 1..86400 seconds')
    token = secrets.token_urlsafe(32)
    session.add(SessionRecord(token_hash=hashlib.sha256(token.encode()).hexdigest(),
        subject_id=subject_id, expires_at=int(time.time()) + lifetime_seconds,
        revoked=False, revision=1))
    session.flush()
    return token


def set_membership(session, subject_id, case_id, *, role, enabled=True, can_save_unreviewed=False):
    begin(session)
    if role not in ('Investigator', 'LeadInvestigator') or type(enabled) is not bool or type(can_save_unreviewed) is not bool:
        raise ValueError('explicit supported role and boolean grants required')
    if session.get(Subject, subject_id) is None: denied()
    incarnation = current(session, case_id)
    row = session.get(Membership, (subject_id, incarnation))
    if row is None:
        row = Membership(subject_id=subject_id, case_incarnation=incarnation, case_id=case_id,
            role=role, enabled=enabled, can_save_unreviewed=can_save_unreviewed, revision=1)
        session.add(row)
    else:
        row.role=role; row.enabled=enabled; row.can_save_unreviewed=can_save_unreviewed
        row.revision += 1
    session.flush()


def revoke_session(session, token):
    begin(session)
    row = session.get(SessionRecord, hashlib.sha256(token.encode()).hexdigest())
    if row:
        row.revoked=True; row.revision += 1; session.flush()


def disable_subject(session, subject_id):
    begin(session)
    row = session.get(Subject, subject_id)
    if row:
        row.enabled=False; row.revision += 1; session.flush()


def authorize_save(session, token, case_id):
    # SQLite writer reservation precedes ALL identity and policy reads. A caller
    # must keep this same transaction through the protected write/return decision.
    if session.get_bind().dialect.name != 'sqlite': denied()
    begin(session)
    proof=session.info.get('_mcis_reserved_writer')
    if not isinstance(proof,tuple) or len(proof)!=3: denied()
    transaction,connection,owner=proof
    if (owner is not threading.current_thread() or transaction is not session.get_transaction()
            or transaction is None or not transaction.is_active or connection.closed
            or connection is not session.connection()
            or not connection.connection.driver_connection.in_transaction): denied()
    if not isinstance(token, str) or len(token) != 43 or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in token): denied()
    row = session.get(SessionRecord, hashlib.sha256(token.encode()).hexdigest(), populate_existing=True)
    if row is None or row.revoked or row.expires_at <= int(time.time()): denied()
    subject = session.get(Subject, row.subject_id, populate_existing=True)
    if subject is None or not subject.enabled: denied()
    incarnation = current(session, case_id)
    member = session.get(Membership, (subject.subject_id, incarnation), populate_existing=True)
    if (member is None or not member.enabled or not member.can_save_unreviewed
            or member.case_id != case_id or member.role not in ('Investigator','LeadInvestigator')): denied()
    return Authority(subject.subject_id, member.role,
        (subject.subject_id, subject.revision, row.token_hash, row.revision,
         row.expires_at, case_id, incarnation, member.revision, member.role))
