"""Server-injected identity seam; no actual SSO provider is implemented."""
from dataclasses import dataclass
from sqlalchemy import Column, String, Boolean, select
from ..db import Base

@dataclass(frozen=True)
class Principal:
    issuer: str
    subject: str
    display_name: str
    source: str

class CaseMember(Base):
    __tablename__ = 'case_members'
    case_id = Column(String(64), primary_key=True)
    issuer = Column(String(255), primary_key=True)
    subject = Column(String(255), primary_key=True)
    active = Column(Boolean, nullable=False, default=True)

def member_filter(principal):
    return (CaseMember.issuer == principal.issuer, CaseMember.subject == principal.subject, CaseMember.active.is_(True))

def visible_cases(session, principal):
    from ..cases.models import CaseRow
    return [dict(r.doc) for r in session.scalars(select(CaseRow).join(CaseMember, CaseMember.case_id == CaseRow.case_id).where(*member_filter(principal)).order_by(CaseRow.id))]

def authorize_case(session, principal, case_id):
    from .context import problem
    from ..cases.models import CaseRow
    row = session.scalar(select(CaseRow.id).join(CaseMember, CaseMember.case_id == CaseRow.case_id).where(CaseRow.case_id == case_id, *member_filter(principal)))
    if row is None:
        raise problem(404, 'CASE_NOT_FOUND', 'Case not found')

def verify(verifier, token):
    if not callable(verifier) or not token:
        raise ValueError('Authentication required')
    p = verifier(token)
    if type(p) is not Principal or any(type(x) is not str or not x.strip() for x in (p.issuer,p.subject,p.display_name,p.source)):
        raise ValueError('Invalid principal')
    if p.source not in {'oidc','server-session','service-credential'}:
        raise ValueError('Untrusted source')
    return p
