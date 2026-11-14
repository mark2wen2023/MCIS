"""Supplemental issue bundle; restored records stay inert, never live authority."""
import base64
import hashlib
import json
from datetime import datetime
from types import SimpleNamespace
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,field_validator
from sqlalchemy import Column,String,JSON,select,text
from sqlalchemy.orm import DeclarativeBase
from . import journal as j
from ..evidence_intake.router import load_receipt
from ..common.context import problem

MAX_BYTES=8*1024*1024
class ArchiveBase(DeclarativeBase):pass
class ImportedArchive(ArchiveBase):
    __tablename__='investigation_imported_archives'
    incarnation=Column(String(36),primary_key=True)
    digest=Column(String(64),primary_key=True)
    doc=Column(JSON,nullable=False)
    imported_by=Column(String(36),nullable=False)
    target_epoch=Column(String(64),nullable=False)

class Strict(BaseModel):model_config=ConfigDict(extra='forbid',strict=True)
class Snapshot(Strict):
    version:Literal[1]
    caseId:str
    evidenceId:str=Field(min_length=1,max_length=64)
    incarnation:str
    caseIncarnation:str
    requestDigest:str=Field(pattern=r'^[0-9a-f]{64}$')
    sourceSha256:str=Field(pattern=r'^[0-9a-f]{64}$')
    registeredSeq:int=Field(ge=1)
    registeredUtc:str

    @field_validator('version',mode='before')
    @classmethod
    def exact_version(cls,value):
        if type(value) is not int or value!=1:raise ValueError('integer version1 required')
        return value

class Entry(j.Entry):
    seq:int=Field(ge=1,le=200)
    recordedUtc:str
    authorSubjectId:str
    sourceSnapshots:list[Snapshot]=Field(max_length=20)
    caseEpochUtc:str
    status:Literal['working_unreviewed']
class Card(Strict):
    issueId:str
    events:list[Entry]=Field(min_length=1,max_length=200)
class Payload(Strict):
    format:Literal['mcis-issue-bundle-v1']
    caseId:str=Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    originCaseIncarnation:str
    exportCaseEpochUtc:str
    cards:list[Card]=Field(max_length=100)
    sources:dict[str,str]
    authority:Literal['historical-untrusted-no-activation']


def initialize(db):
    if db.engine.dialect.name!='sqlite':raise ValueError('SQLite required')
    ArchiveBase.metadata.create_all(db.engine)
    with db.engine.begin() as c:
        for op in ('UPDATE','DELETE'):
            c.execute(text(f"CREATE TRIGGER IF NOT EXISTS issue_archive_no_{op.lower()} BEFORE {op} ON investigation_imported_archives BEGIN SELECT RAISE(ABORT,'issue archive append-only'); END;"))


def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def reject():raise problem(422,'ISSUE_ARCHIVE_INVALID','问题归档无效，未恢复')
def utc(value):
    try:
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        if parsed.utcoffset() is None:reject()
    except (ValueError,TypeError):reject()
def pairs(items):
    out={}
    for k,v in items:
        if k in out:reject()
        out[k]=v
    return out

def validate(raw):
    if not isinstance(raw,bytes) or len(raw)>MAX_BYTES:reject()
    try:
        wrapper=json.loads(raw.decode(),object_pairs_hook=pairs,parse_constant=lambda _:reject())
        if not isinstance(wrapper,dict) or set(wrapper)!={'sha256','payload'}:reject()
        digest=hashlib.sha256(canonical(wrapper['payload'])).hexdigest()
        if wrapper['sha256']!=digest:reject()
        p=Payload.model_validate(wrapper['payload']);j.canonical_id(p.originCaseIncarnation);utc(p.exportCaseEpochUtc)
        ids=set();needed=set()
        for card in p.cards:
            j.canonical_id(card.issueId)
            if card.issueId in ids:reject()
            ids.add(card.issueId);latest=0;verified=False
            for seq,e in enumerate(card.events,1):
                if e.seq!=seq:reject()
                j.canonical_id(e.authorSubjectId);utc(e.recordedUtc);utc(e.caseEpochUtc)
                if e.kind=='judgment':
                    if e.outcome is not None or e.againstJudgment is not None:reject()
                    latest=seq;verified=False
                else:
                    if not latest or e.againstJudgment!=latest:reject()
                    if e.kind=='verification':
                        if e.outcome is None:reject()
                        verified=True
                    elif e.outcome is not None or not verified:reject()
                if e.sourceIds!=[x.evidenceId for x in e.sourceSnapshots]:reject()
                for source in e.sourceSnapshots:
                    if type(source.version) is not int or source.caseId!=p.caseId or source.caseIncarnation!=p.originCaseIncarnation:reject()
                    j.canonical_id(source.incarnation);j.canonical_id(source.caseIncarnation);utc(source.registeredUtc)
                    needed.add(source.sourceSha256)
        if len(needed)>200 or set(p.sources)!=needed:reject()
        decoded_size=0
        for digest_key,encoded in p.sources.items():
            raw_source=base64.b64decode(encoded,validate=True)
            decoded_size+=len(raw_source)
            if decoded_size>MAX_BYTES:reject()
            if hashlib.sha256(raw_source).hexdigest()!=digest_key:reject()
        return digest,wrapper['payload']
    except Exception as error:
        from fastapi import HTTPException
        if isinstance(error,HTTPException) and error.status_code==422:raise
        reject()


def export_bundle(db,settings,token,case_id):
    with db.session() as s:
        before,generation=j.auth(s,token,case_id)
        ids=list(s.scalars(select(j.Event.issue_id).where(j.Event.incarnation==generation).distinct().order_by(j.Event.issue_id).limit(101)))
        if len(ids)>100:raise problem(413,'ISSUE_ARCHIVE_LIMIT','归档超出预算')
        payload={'format':'mcis-issue-bundle-v1','caseId':case_id,'originCaseIncarnation':generation,
                 'exportCaseEpochUtc':j.load_case(s,case_id)['caseEpochUtc'],'cards':[],'sources':{},'authority':'historical-untrusted-no-activation'}
        ctx=SimpleNamespace(db=db,settings=settings,role=before.role,operator=before.subject_id)
        checked={}
        for i in ids:
            events=[r.doc for r in j.rows(s,generation,i)]
            payload['cards'].append({'issueId':i,'events':events})
            if len(canonical(payload))>MAX_BYTES-128:raise problem(413,'ISSUE_ARCHIVE_LIMIT','记录超出归档预算')
            for e in events:
                for snapshot in e['sourceSnapshots']:
                    key=snapshot['evidenceId']
                    if key in checked:
                        if checked[key]!=snapshot:raise problem(409,'ISSUE_ARCHIVE_SOURCE_CHANGED','历史来源版本冲突')
                        continue
                    if len(checked)>=200:raise problem(413,'ISSUE_ARCHIVE_LIMIT','直接来源数超出预算')
                    current=j.source_current(ctx,s,case_id,key)
                    if current!=snapshot:raise problem(409,'ISSUE_ARCHIVE_SOURCE_CHANGED','历史来源已变更，未导出不完整包')
                    found=load_receipt(ctx,s,case_id,current['requestDigest'])
                    if found is None:raise problem(409,'ISSUE_ARCHIVE_SOURCE_MISSING','来源缺失')
                    _,raw=found
                    if hashlib.sha256(raw).hexdigest()!=snapshot['sourceSha256']:raise problem(409,'ISSUE_ARCHIVE_SOURCE_CHANGED','来源变化')
                    if len(raw)>MAX_BYTES:raise problem(413,'ISSUE_ARCHIVE_LIMIT','来源超出预算')
                    encoded_size=0 if snapshot['sourceSha256'] in payload['sources'] else 4*((len(raw)+2)//3)+80
                    if len(canonical(payload))+encoded_size>MAX_BYTES-128:raise problem(413,'ISSUE_ARCHIVE_LIMIT','来源编码超出预算')
                    payload['sources'][snapshot['sourceSha256']]=base64.b64encode(raw).decode()
                    checked[key]=current
            if len(canonical(payload))>MAX_BYTES-128:raise problem(413,'ISSUE_ARCHIVE_LIMIT','归档超出预算')
        result=canonical({'sha256':hashlib.sha256(canonical(payload)).hexdigest(),'payload':payload})
        validate(result)
        for key,snapshot in checked.items():
            if j.source_current(ctx,s,case_id,key)!=snapshot:raise problem(409,'ISSUE_ARCHIVE_SOURCE_CHANGED','来源变化')
        if j.load_case(s,case_id)['caseEpochUtc']!=payload['exportCaseEpochUtc']:raise problem(409,'ISSUE_ARCHIVE_EPOCH_CHANGED','案件时基变化')
        if j.auth(s,token,case_id)!=(before,generation):raise problem(403,'ISSUE_ACCESS_DENIED','授权变化')
        return result


def restore_bundle(db,token,case_id,raw):
    with db.session() as s:
        before,generation=j.auth(s,token,case_id,True)
        digest,payload=validate(raw)
        if payload['caseId']!=case_id:reject()
        target_epoch=j.load_case(s,case_id)['caseEpochUtc']
        key=(generation,digest);row=s.get(ImportedArchive,key);replayed=row is not None
        if row is not None and row.target_epoch!=target_epoch:raise problem(409,'ISSUE_ARCHIVE_EPOCH_CHANGED','目标案件时基变化')
        if row is None:
            count=len(list(s.scalars(select(ImportedArchive.digest).where(ImportedArchive.incarnation==generation).limit(20))))
            if count>=20:raise problem(413,'ISSUE_ARCHIVE_LIMIT','恢复历史数量达到预算')
            s.add(ImportedArchive(incarnation=generation,digest=digest,doc=payload,imported_by=before.subject_id,target_epoch=target_epoch));s.flush()
        response={'sha256':digest,'replayed':replayed,'cards':len(payload['cards']),
                  'status':'imported_history_untrusted','activated':False}
        if j.auth(s,token,case_id,True)!=(before,generation):raise problem(403,'ISSUE_ACCESS_DENIED','授权变化')
        if j.load_case(s,case_id)['caseEpochUtc']!=target_epoch:raise problem(409,'ISSUE_ARCHIVE_EPOCH_CHANGED','案件时基变化')
        return response


def read_imported(db,token,case_id,digest):
    import re
    if not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest):reject()
    with db.session() as s:
        before,generation=j.auth(s,token,case_id)
        row=s.get(ImportedArchive,(generation,digest))
        if row is None:raise problem(404,'ISSUE_ARCHIVE_NOT_FOUND','历史归档不存在')
        if row.target_epoch!=j.load_case(s,case_id)['caseEpochUtc']:raise problem(409,'ISSUE_ARCHIVE_EPOCH_CHANGED','目标案件时基变化')
        response={'sha256':digest,'status':'imported_history_untrusted','activated':False,'targetCaseEpochUtc':row.target_epoch,'payload':row.doc}
        if j.auth(s,token,case_id)!=(before,generation):raise problem(403,'ISSUE_ACCESS_DENIED','授权变化')
        if j.load_case(s,case_id)['caseEpochUtc']!=row.target_epoch:raise problem(409,'ISSUE_ARCHIVE_EPOCH_CHANGED','案件时基变化')
        return response


def list_imported(db,token,case_id):
    with db.session() as s:
        before,generation=j.auth(s,token,case_id)
        epoch=j.load_case(s,case_id)['caseEpochUtc']
        rows=list(s.scalars(select(ImportedArchive).where(ImportedArchive.incarnation==generation,ImportedArchive.target_epoch==epoch).order_by(ImportedArchive.digest).limit(21)))
        if len(rows)>20:raise problem(413,'ISSUE_ARCHIVE_LIMIT','历史清单超出预算')
        result={'caseId':case_id,'items':[{'sha256':r.digest,'cards':len(r.doc['cards']),
                'status':'imported_history_untrusted','activated':False} for r in rows]}
        if j.auth(s,token,case_id)!=(before,generation):raise problem(403,'ISSUE_ACCESS_DENIED','授权变化')
        if j.load_case(s,case_id)['caseEpochUtc']!=epoch:raise problem(409,'ISSUE_ARCHIVE_EPOCH_CHANGED','案件时基变化')
        return result
