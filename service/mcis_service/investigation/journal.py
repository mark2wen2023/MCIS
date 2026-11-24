"""Trusted-host issue notebook. Human working opinions, never approved findings.

Explicit initialize/grant are administrative provisioning, not HTTP endpoints.
Neither archive import nor old role headers confer read or write authority.
"""
import hashlib
import json
import uuid
from types import SimpleNamespace
from sqlalchemy import Column, String, Integer, Boolean, JSON, select, text
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Literal
from fastapi import HTTPException
from sqlalchemy.orm import DeclarativeBase

class JournalBase(DeclarativeBase):
    pass
from ..identity.local import authorize_read, Subject
from ..reports.access import require_content, begin
from ..cases.incarnation import current as case_current
from ..cases.service import load_case
from ..evidence_intake.incarnation import current as source_current
from ..common.context import problem
from ..common.timeutil import iso, now_utc


class Grant(JournalBase):
    __tablename__='investigation_issue_grants'
    subject_id=Column(String(36),primary_key=True)
    incarnation=Column(String(36),primary_key=True)
    enabled=Column(Boolean,nullable=False)


class Event(JournalBase):
    __tablename__='investigation_issue_events'
    incarnation=Column(String(36),primary_key=True)
    issue_id=Column(String(36),primary_key=True)
    seq=Column(Integer,primary_key=True)
    operation_id=Column(String(36),nullable=False)
    digest=Column(String(64),nullable=False)
    doc=Column(JSON,nullable=False)


class Entry(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    kind: Literal['judgment','verification','discussion']
    note: str=Field(min_length=1,max_length=8000)
    sourceIds: list[str]=Field(default_factory=list,max_length=20)
    outcome: Literal['supports','refutes','inconclusive'] | None=None
    againstJudgment: int | None=Field(default=None,ge=1,le=200)

    @field_validator('note')
    @classmethod
    def nonblank(cls,v):
        if not v.strip() or '\x00' in v:raise ValueError('nonblank text required')
        return v

    @field_validator('sourceIds')
    @classmethod
    def ids(cls,v):
        if len(set(v))!=len(v) or any(not x or len(x)>64 for x in v):raise ValueError('unique source IDs required')
        return v


def initialize(db):
    """Trusted-host explicit setup; no authority issued and no legacy app changed."""
    if db.engine.dialect.name!='sqlite':raise ValueError('SQLite required')
    JournalBase.metadata.create_all(db.engine,tables=[Grant.__table__,Event.__table__])
    with db.engine.begin() as c:
        for verb in ('UPDATE','DELETE'):
            c.execute(text(f"CREATE TRIGGER IF NOT EXISTS issue_event_no_{verb.lower()} BEFORE {verb} ON investigation_issue_events BEGIN SELECT RAISE(ABORT, 'issue history is append-only'); END;"))


def grant(session,subject_id,case_id,*,enabled):
    begin(session)
    if type(enabled) is not bool or session.get(Subject,subject_id) is None:raise ValueError('explicit subject and boolean required')
    key=(subject_id,case_current(session,case_id));row=session.get(Grant,key)
    if row is None:session.add(Grant(subject_id=key[0],incarnation=key[1],enabled=enabled))
    else:row.enabled=enabled
    session.flush()


def canonical_id(value):
    try:
        if not isinstance(value,str) or str(uuid.UUID(value))!=value:raise ValueError()
    except (ValueError,AttributeError):raise problem(422,'ISSUE_ID_INVALID','需要规范 UUID') from None
    return value


def auth(s,token,case_id,write=False):
    try:a=authorize_read(s,token,case_id)
    except Exception:raise problem(403,'ISSUE_ACCESS_DENIED','身份或案件授权无效') from None
    require_content(s,case_id,a.role)
    generation=case_current(s,case_id)
    if write:
        row=s.get(Grant,(a.subject_id,generation),populate_existing=True)
        if row is None or not row.enabled:raise problem(403,'ISSUE_WRITE_DENIED','未授予问题记录权限')
    return a,generation


def rows(s,generation,issue_id):
    result=list(s.scalars(select(Event).where(Event.incarnation==generation,Event.issue_id==issue_id).order_by(Event.seq).limit(201)))
    if len(result)>200:raise problem(413,'ISSUE_LIMIT','问题记录超出读取预算')
    return result


def project(case_id,issue_id,history):
    return {'caseId':case_id,'issueId':issue_id,'revision':len(history),'status':'working_unreviewed',
      'sourceSnapshots':'historical-at-entry-not-current-attestation','events':[dict(r.doc) for r in history]}


class SourcePin(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    evidenceId:str=Field(min_length=1,max_length=64)
    sourceIncarnation:str
    sourceSha256:str=Field(pattern=r'^[0-9a-f]{64}$')

    @field_validator('sourceIncarnation')
    @classmethod
    def uuid_value(cls,value):return canonical_id(value)


def selection_changed():
    raise problem(409,'SOURCE_SELECTION_CHANGED','所选来源已变化，请刷新来源清单后重新选择')


def selected_current(ctx,s,case_id,source_ids,pins):
    try:snapshots=[source_current(ctx,s,case_id,eid) for eid in source_ids]
    except HTTPException as error:
        if pins is not None and error.status_code==409:selection_changed()
        raise
    if pins is not None:
        actual={x['evidenceId']:(x['incarnation'],x['sourceSha256']) for x in snapshots}
        if any(actual.get(x['evidenceId'])!=(x['sourceIncarnation'],x['sourceSha256']) for x in pins):selection_changed()
    return snapshots


def append(db,settings,token,case_id,issue_id,operation_id,expected_revision,entry,source_pins=None):
    """Create with revision 0 + judgment; append never replaces prior opinions."""
    canonical_id(issue_id);canonical_id(operation_id)
    if type(expected_revision) is not int or not 0<=expected_revision<200:raise problem(422,'ISSUE_REVISION_INVALID','版本不合法')
    entry=Entry.model_validate(entry)
    if (entry.kind=='verification')!=(entry.outcome is not None):raise problem(422,'ISSUE_OUTCOME_INVALID','核实必须给出结果，其他记录不得给出核实结果')
    request={'expectedRevision':expected_revision,'entry':entry.model_dump()}
    pins=None
    if source_pins is not None:
        if not isinstance(source_pins,list) or len(source_pins)>20:raise problem(422,'ISSUE_SOURCE_PINS_INVALID','来源选择无效')
        pins=[SourcePin.model_validate(x).model_dump() for x in source_pins]
        ids=[x['evidenceId'] for x in pins]
        if len(set(ids))!=len(ids) or set(ids)!=set(entry.sourceIds):raise problem(422,'ISSUE_SOURCE_PINS_INVALID','来源选择必须完整对应')
        pins.sort(key=lambda x:x['evidenceId'])
        if pins:request['sourcePins']=pins


    with db.session() as s:
        before,generation=auth(s,token,case_id,True)
        request['authorSubjectId']=before.subject_id
        digest=hashlib.sha256(json.dumps(request,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        history=rows(s,generation,issue_id)
        prior=next((r for r in history if r.operation_id==operation_id),None)
        if prior:
            if prior.digest!=digest:raise problem(409,'ISSUE_OPERATION_CONFLICT','同一操作编号不得改变内容')
            response=project(case_id,issue_id,history);response['replayed']=True
            if auth(s,token,case_id,True)!=(before,generation):raise problem(403,'ISSUE_ACCESS_DENIED','授权变化')
            return response
        if len(history)!=expected_revision:raise problem(409,'ISSUE_REVISION_CONFLICT','记录已更新，请读取后再追加')
        if not history:
            issue_ids=list(s.scalars(select(Event.issue_id).where(Event.incarnation==generation).distinct().limit(100)))
            if len(issue_ids)>=100:raise problem(413,'ISSUE_LIST_LIMIT','当前案件问题数达到试验预算')
        if not history and entry.kind!='judgment':raise problem(409,'ISSUE_INITIAL_JUDGMENT_REQUIRED','先记录初步判断')
        last_judgment=max((r.seq for r in history if r.doc['kind']=='judgment'),default=0)
        if entry.kind=='judgment':
            if entry.againstJudgment is not None:raise problem(422,'ISSUE_REFERENCE_INVALID','判断不应伪装为核实记录')
        elif not last_judgment or entry.againstJudgment!=last_judgment:
            raise problem(409,'ISSUE_REFERENCE_INVALID','核实或讨论必须指向最新判断')
        if entry.kind=='discussion':
            if not any(r.seq>last_judgment and r.doc['kind']=='verification' for r in history):
                raise problem(409,'ISSUE_VERIFICATION_REQUIRED','最新判断须先核实再讨论')
        ctx=SimpleNamespace(db=db,settings=settings,role=before.role,operator=before.subject_id)
        snapshots=selected_current(ctx,s,case_id,entry.sourceIds,pins)
        document={**entry.model_dump(),'seq':expected_revision+1,'recordedUtc':iso(now_utc()),
                  'authorSubjectId':before.subject_id,'sourceSnapshots':snapshots,'caseEpochUtc':load_case(s,case_id)['caseEpochUtc'],'status':'working_unreviewed'}
        row=Event(incarnation=generation,issue_id=issue_id,seq=expected_revision+1,operation_id=operation_id,digest=digest,doc=document)
        s.add(row);s.flush()
        response=project(case_id,issue_id,[*history,row]);response['replayed']=False
        if selected_current(ctx,s,case_id,entry.sourceIds,pins)!=snapshots:
            if pins is not None:selection_changed()
            raise problem(409,'ISSUE_SOURCE_CHANGED','来源变化')
        if auth(s,token,case_id,True)!=(before,generation):raise problem(403,'ISSUE_ACCESS_DENIED','授权变化')
        return response


def source_version_states(ctx,s,case_id,event,checked):
    """Request-local integrity results, compared against each immutable snapshot."""
    snapshots={x['evidenceId']:x for x in event.get('sourceSnapshots',[])}
    result=[]
    for evidence_id in event['sourceIds']:
        key=(case_id,evidence_id)
        if key not in checked:
            try:
                checked[key]=(source_current(ctx,s,case_id,evidence_id),None)
            except HTTPException as error:
                # Do not cache or downgrade an authorization failure.
                if error.status_code in (401,403):raise
                if error.status_code==409:
                    code=error.detail.get('code') if isinstance(error.detail,dict) else None
                    status='unavailable' if code=='SOURCE_INCARNATION_MISSING' else 'needs_review'
                elif error.status_code in (404,503):status='unavailable'
                else:raise
                checked[key]=(None,status)
        current,status=checked[key]
        old=snapshots.get(evidence_id)
        if current is not None:
            keys=('caseId','evidenceId','caseIncarnation','incarnation','sourceSha256')
            status=('current' if all(old.get(k)==current.get(k) for k in keys) else 'needs_review') if old is not None else 'unavailable'
        result.append({'evidenceId':evidence_id,'status':status})
    return result


def read(db,token,case_id,issue_id,settings=None):
    canonical_id(issue_id)
    with db.session() as s:
        before,generation=auth(s,token,case_id)
        history=rows(s,generation,issue_id)
        if not history:raise problem(404,'ISSUE_NOT_FOUND','问题不存在')
        response=project(case_id,issue_id,history)
        if settings is not None:
            ctx=SimpleNamespace(db=db,settings=settings,role=before.role,operator=before.subject_id)
            checked={}  # Lifetime is this authorized read only; never a host/global cache.
            for event in response['events']:
                event['sourceVersionStates']=source_version_states(ctx,s,case_id,event,checked)
        if auth(s,token,case_id)!=(before,generation):raise problem(403,'ISSUE_ACCESS_DENIED','授权变化')
        return response


def list_issues(db,token,case_id):
    with db.session() as s:
        before,generation=auth(s,token,case_id)
        ids=list(s.scalars(select(Event.issue_id).where(Event.incarnation==generation).distinct().order_by(Event.issue_id).limit(101)))
        if len(ids)>100:raise problem(413,'ISSUE_LIST_LIMIT','问题清单超出读取预算')
        items=[]
        for i in ids:
            h=rows(s,generation,i)
            items.append({'issueId':i,'revision':len(h),'openingNotePreview':h[0].doc['note'][:200],
                          'lastKind':h[-1].doc['kind'],'status':'working_unreviewed'})
        response={'caseId':case_id,'items':items}
        if auth(s,token,case_id)!=(before,generation):raise problem(403,'ISSUE_ACCESS_DENIED','授权变化')
        return response
