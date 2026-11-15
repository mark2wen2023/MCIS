"""Full forward conflict revisions; registry bindings are NOT file verification."""
from copy import deepcopy
import hashlib
import json
import re
from sqlalchemy import Column, Integer, String, JSON, DDL, event, select
from ..db import Base
from ..common.context import problem
from ..evidence.models import EvidenceRow
from ..evidence.service import custody_events, derive
from ..audit.models import AuditEventRow


class ConflictRevision(Base):
    __tablename__ = 'conflict_revisions'
    case_id = Column(String(64), primary_key=True)
    conflict_id = Column(String(64), primary_key=True)
    revision = Column(Integer, primary_key=True)
    doc = Column(JSON, nullable=False)


for operation in ('UPDATE','DELETE'):
    event.listen(ConflictRevision.__table__, 'after_create', DDL(
        f"CREATE TRIGGER IF NOT EXISTS conflict_revisions_no_{operation.lower()} BEFORE {operation} "
        f"ON conflict_revisions BEGIN SELECT RAISE(ABORT, 'conflict revisions are append-only'); END;"
    ).execute_if(dialect='sqlite'))


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,
        separators=(',',':'),allow_nan=False).encode()).hexdigest()


def last(s,case_id,key):
    return s.scalars(select(ConflictRevision).where(ConflictRevision.case_id==case_id,
        ConflictRevision.conflict_id==key).order_by(ConflictRevision.revision.desc()).limit(1)).first()


def prepare(s,case_id,key,before):
    if s.get_bind().dialect.name!='sqlite':
        raise problem(503,'CONFLICT_CAPTURE_UNAVAILABLE','完整冲突修订当前仅支持SQLite事务')
    previous=last(s,case_id,key)
    if previous is not None and previous.doc['after']!=before:
        raise problem(409,'CONFLICT_REVISION_DIVERGED','当前冲突与最后修订不一致，未覆盖')
    known_history=s.scalars(select(AuditEventRow).where(AuditEventRow.case_id==case_id,
        AuditEventRow.entity_type=='conflict',AuditEventRow.entity_id==key).limit(1)).first()
    coverage=previous.doc['coverage'] if previous else (
        'unknown-before-capture' if before is not None or known_history else 'captured-from-creation')
    return previous,coverage


def bindings(s,case_id,doc,before,previous):
    out={}
    for side in ('a','b'):
        # An unchanged observation keeps its originally captured registry version.
        if previous and before and before.get(side)==doc.get(side):
            out[side]=deepcopy(previous.doc['afterSources'][side]);continue
        observation=doc.get(side,{})
        evidence_id=observation.get('evidenceId')
        value={'evidenceId':evidence_id,'status':'unregistered','bytesVerified':False}
        if evidence_id:
            row=s.scalars(select(EvidenceRow).where(EvidenceRow.case_id==case_id,EvidenceRow.key==evidence_id)).first()
            value['status']='unresolved'
            if row and row.doc.get('caseId')==case_id:
                events=custody_events(s,case_id,evidence_id)
                current=derive(row.doc,events).get('currentSha256')
                if isinstance(current,str) and re.fullmatch('[0-9a-f]{64}',current):
                    value.update(status='registered-version',sha256=current,
                        registrationSha256=row.doc.get('sha256'),registryDocSha256=digest(row.doc),
                        custodyHeadSeq=events[-1].seq if events else None,
                        custodyHeadSha256=hashlib.sha256(events[-1].line.encode()).hexdigest() if events else None)
        out[side]=value
    return out


def capture(s,case_id,key,before,after,prepared,audit_row):
    previous,coverage=prepared
    before_sources=deepcopy(previous.doc['afterSources']) if previous else None
    doc={'format':'MCIS-CONFLICT-REVISION-1','caseId':case_id,'conflictId':key,
         'revision':previous.revision+1 if previous else 1,'coverage':coverage,
         'operator':audit_row.operator,'role':audit_row.role,'identityMode':'unverified-self-reported',
         'utc':audit_row.utc,'auditSeq':audit_row.seq,'auditLineSha256':hashlib.sha256(audit_row.line.encode()).hexdigest(),'operation':audit_row.action,
         'before':deepcopy(before),'after':deepcopy(after),
         'beforeSources':before_sources,'afterSources':bindings(s,case_id,after,before,previous),
         'previousSha256':previous.doc['sha256'] if previous else None}
    doc['sha256']=digest(doc)
    s.add(ConflictRevision(case_id=case_id,conflict_id=key,revision=doc['revision'],doc=doc))
    s.flush()


def history(s,ctx,case_id,key,current):
    from ..reports.access import require_content
    from ..interviews.access import source
    require_content(s,case_id,ctx.role)
    rows=list(s.scalars(select(ConflictRevision).where(ConflictRevision.case_id==case_id,
        ConflictRevision.conflict_id==key).order_by(ConflictRevision.revision)))
    previous=None
    for i,row in enumerate(rows,1):
        d=row.doc
        if (d.get('caseId')!=case_id or d.get('conflictId')!=key or d.get('revision')!=i
            or digest({k:v for k,v in d.items() if k!='sha256'})!=d.get('sha256')
            or d.get('previousSha256')!=(previous['sha256'] if previous else None)
            or previous is not None and d.get('before')!=previous['after']):
            raise problem(409,'CONFLICT_REVISION_DIVERGED','冲突修订关联不一致')
        audit_row=s.scalars(select(AuditEventRow).where(AuditEventRow.case_id==case_id,AuditEventRow.seq==d['auditSeq'])).first()
        if audit_row is None or hashlib.sha256(audit_row.line.encode()).hexdigest()!=d.get('auditLineSha256'):
            raise problem(409,'CONFLICT_REVISION_DIVERGED','冲突修订缺少对应审计')
        for snapshot in (d['before'],d['after']):
            if snapshot:
                for side in ('a','b'):
                    ref=snapshot.get(side,{}).get('evidenceId')
                    if ref:source(s,case_id,ctx.role,ref)
        previous=d
    if previous and previous['after']!=current:
        raise problem(409,'CONFLICT_REVISION_DIVERGED','当前冲突与最后修订不一致')
    return {'caseId':case_id,'conflictId':key,
        'coverage':previous['coverage'] if previous else 'unknown-before-capture',
        'identityMode':'unverified-self-reported','revisions':[r.doc for r in rows]}


def write_version(s,case_id,key,current):
    previous=last(s,case_id,key)
    return digest({'caseId':case_id,'conflictId':key,'current':current,
                   'revisionSha256':previous.doc['sha256'] if previous else None})


def expect_version(s,case_id,key,current,expected):
    if expected is None:
        raise problem(428,'CONFLICT_VERSION_REQUIRED','请重新读取带版本的冲突记录；旧客户端须升级后保存')
    if not isinstance(expected,str) or not re.fullmatch('[0-9a-f]{64}',expected):
        raise problem(422,'CONFLICT_VERSION_INVALID','冲突版本格式无效')
    if expected!=write_version(s,case_id,key,current):
        raise problem(412,'CONFLICT_VERSION_CHANGED','记录已更新；请保留本地说明，刷新并比对后重新编辑，未保存本次更改')
