"""Trusted-host working history only. No HTTP, facts, or imported authority."""
import copy
import json
import uuid
from sqlalchemy import Column,String,Integer,Boolean,JSON,UniqueConstraint,select,text
from sqlalchemy.orm import DeclarativeBase
from . import host_extraction as h,extraction
from .extraction_review_host import Decision
from ..investigation import journal as j
from ..common.context import problem
from ..common.timeutil import iso,now_utc

class WorkingBase(DeclarativeBase):pass
class WorkingGrant(WorkingBase):
    __tablename__='extraction_working_grants'
    subject_id=Column(String(36),primary_key=True)
    incarnation=Column(String(36),primary_key=True)
    enabled=Column(Boolean,nullable=False)
class WorkingProposal(WorkingBase):
    __tablename__='extraction_working_proposals'
    incarnation=Column(String(36),primary_key=True)
    proposal_id=Column(String(36),primary_key=True)
    operation_id=Column(String(36),nullable=False)
    record_id=Column(String(64),nullable=False)
    binding=Column(String(64),nullable=False)
    digest=Column(String(64),nullable=False)
    doc=Column(JSON,nullable=False)
    __table_args__=(UniqueConstraint('incarnation','operation_id'),)
class WorkingReview(WorkingBase):
    __tablename__='extraction_working_reviews'
    incarnation=Column(String(36),primary_key=True)
    proposal_id=Column(String(36),primary_key=True)
    seq=Column(Integer,primary_key=True)
    operation_id=Column(String(36),nullable=False)
    digest=Column(String(64),nullable=False)
    doc=Column(JSON,nullable=False)
    __table_args__=(UniqueConstraint('incarnation','proposal_id','operation_id'),)

def initialize(db):
    if db.engine.dialect.name!='sqlite':raise ValueError('SQLite required')
    WorkingBase.metadata.create_all(db.engine)
    with db.engine.begin() as c:
        for table in ('extraction_working_proposals','extraction_working_reviews'):
            for verb in ('UPDATE','DELETE'):
                c.execute(text(f"CREATE TRIGGER IF NOT EXISTS {table}_no_{verb.lower()} BEFORE {verb} ON {table} BEGIN SELECT RAISE(ABORT,'working history append-only'); END;"))

def grant(s,subject_id,case_id,*,enabled):
    j.begin(s)
    if type(enabled) is not bool or s.get(j.Subject,subject_id) is None:raise ValueError()
    key=(subject_id,j.case_current(s,case_id));row=s.get(WorkingGrant,key)
    if row is None:s.add(WorkingGrant(subject_id=key[0],incarnation=key[1],enabled=enabled))
    else:row.enabled=enabled
    s.flush()

def _auth(s,token,case_id,write=False):
    before,generation=j.auth(s,token,case_id)
    if write:
        g=s.get(WorkingGrant,(before.subject_id,generation),populate_existing=True)
        if g is None or not g.enabled:raise problem(403,'WORKING_GRANT_REQUIRED','未授予持久工作复核权限')
    return before,generation

def _snapshot(s,db,settings,token,case_id,record_id,binding):
    snap=h.snapshot_in_session(s,db,settings,token,case_id,record_id)
    if snap[0]!=binding:raise problem(409,'WORKING_SOURCE_CHANGED','来源或权限策略已变化，历史正文未开放')
    return snap

def _bounded(value,maximum=512*1024):
    if len(json.dumps(value,ensure_ascii=False,allow_nan=False).encode())>maximum:raise ValueError('working payload limit')
    return copy.deepcopy(value)

def _validate_generated(result,snapshot,record_id):
    """Validate shape and citations; NOT proof of provenance. Caller must be trusted."""
    result=_bounded(result)
    if set(result)!={'status','inferencePerformed','fixture','proposals','citations','receipt','saved','citationMeaning'}:raise ValueError()
    if result['status']!='PendingReview' or result['saved'] is not False or result['citationMeaning']!='exact_quote_match_only_not_fact_verification':raise ValueError()
    binding,record,policy,source_scope=snapshot;receipt=result['receipt']
    if set(receipt)!={'bindingDigest','promptDigest','outputDigest','providerMode','modelIdentityVerified','configuredModel','persistentAudit','signature','sourceScope','runChecksum'}:raise ValueError()
    if receipt['providerMode'] not in ('fixture','local') or receipt['signature'] is not False or receipt['persistentAudit'] is not False or receipt['modelIdentityVerified'] is not False:raise ValueError()
    fixture=receipt['providerMode']=='fixture'
    if result['fixture'] is not fixture or result['inferencePerformed'] is not (not fixture):raise ValueError()
    if fixture and receipt['configuredModel'] is not None:raise ValueError()
    if not fixture and (not isinstance(receipt['configuredModel'],str) or not receipt['configuredModel'].strip() or len(receipt['configuredModel'])>200):raise ValueError()
    if receipt['bindingDigest']!=binding or receipt['sourceScope']!=source_scope or receipt['promptDigest']!=extraction.digest(extraction.prompt(record,policy)):raise ValueError()
    unsigned={k:v for k,v in receipt.items() if k!='runChecksum'}
    if receipt['runChecksum']!=extraction.digest(unsigned):raise ValueError()
    items=[]
    for st in result['proposals']:
        items.append({**{k:st[k] for k in ('kind','subject','summary','claim','quote')},'round':st['span']['round'],'field':st['span']['field']})
    payload=extraction.parse_output(json.dumps({'statements':items},ensure_ascii=False),record)
    statements,citations=extraction.checked_statements(payload,record,policy)
    if statements!=result['proposals'] or citations!=result['citations'] or receipt['outputDigest']!=extraction.digest(payload):raise ValueError()
    return result

def _history(s,generation,proposal_id):
    rows=list(s.scalars(select(WorkingReview).where(WorkingReview.incarnation==generation,WorkingReview.proposal_id==proposal_id).order_by(WorkingReview.seq).limit(101)))
    if len(rows)>100:raise problem(413,'WORKING_LIMIT','工作复核版本超出预算')
    return rows

def _view(s,row):
    history=_history(s,row.incarnation,row.proposal_id)
    return _bounded({'proposalId':row.proposal_id,'recordId':row.record_id,'revision':len(history),'status':'working_unreviewed',
        'saved':True,'persistence':'working_record_only','factActivated':False,'proposal':row.doc,'reviews':[r.doc for r in history]},4*1024*1024)

def _final(s,db,settings,token,case_id,record_id,binding,before,write):
    _snapshot(s,db,settings,token,case_id,record_id,binding)
    if _auth(s,token,case_id,write)!=before:raise problem(403,'WORKING_ACCESS_CHANGED','授权变化')

def _save_generated(db,settings,token,case_id,record_id,operation_id,expected_binding,result,provider_key=None):
    """Private trusted-host entry only; never accept UI-submitted model results."""
    return _save_checked(db,settings,token,case_id,record_id,operation_id,expected_binding,result,provider_key,_validate_generated)

def _save_checked(db,settings,token,case_id,record_id,operation_id,expected_binding,result,provider_key,validator):
    """Shared private transaction; validator supplied only by an in-process trusted host."""
    j.canonical_id(operation_id)
    with db.session() as s:
        before=_auth(s,token,case_id,True);authority,generation=before
        snapshot=_snapshot(s,db,settings,token,case_id,record_id,expected_binding)
        frozen=validator(result,snapshot,record_id)
        digest=extraction.digest({'recordId':record_id,'binding':expected_binding,'result':frozen,'actor':authority.subject_id,'providerKey':provider_key})
        row=s.scalars(select(WorkingProposal).where(WorkingProposal.incarnation==generation,WorkingProposal.operation_id==operation_id)).first()
        replayed=row is not None
        if row:
            if row.digest!=digest:raise problem(409,'WORKING_OPERATION_CONFLICT','操作编号内容冲突')
        else:
            if len(list(s.scalars(select(WorkingProposal.proposal_id).where(WorkingProposal.incarnation==generation).limit(50))))>=50:raise problem(413,'WORKING_LIMIT','工作提案数达到预算')
            row=WorkingProposal(incarnation=generation,proposal_id=str(uuid.uuid4()),operation_id=operation_id,record_id=record_id,binding=expected_binding,digest=digest,
                doc={'result':frozen,'generatedBySubjectId':authority.subject_id,'storedUtc':iso(now_utc()),'bindingDigest':expected_binding,'providerKey':provider_key})
            s.add(row);s.flush()
        response=_view(s,row);response['replayed']=replayed
        _final(s,db,settings,token,case_id,record_id,expected_binding,before,True)
        return response

def append_review(db,settings,token,case_id,proposal_id,operation_id,expected_revision,decisions,*,review_origin='user_submission_unverified'):
    if type(review_origin) is not str or review_origin not in ('user_submission_unverified','scripted_test'):raise ValueError()
    j.canonical_id(proposal_id);j.canonical_id(operation_id)
    if type(expected_revision) is not int or not 0<=expected_revision<100:raise ValueError()
    if not isinstance(decisions,list) or len(decisions)>20:raise ValueError()
    decisions=[Decision.model_validate(d).model_dump() for d in decisions];decisions.sort(key=lambda x:x['index'])
    with db.session() as s:
        before=_auth(s,token,case_id,True);authority,generation=before
        row=s.get(WorkingProposal,(generation,proposal_id))
        if row is None:raise problem(404,'WORKING_NOT_FOUND','工作提案不存在')
        _snapshot(s,db,settings,token,case_id,row.record_id,row.binding)
        if [x['index'] for x in decisions]!=list(range(1,len(row.doc['result']['proposals'])+1)):raise ValueError()
        digest=extraction.digest({'actor':authority.subject_id,'expectedRevision':expected_revision,'decisions':decisions,'reviewOrigin':review_origin})
        history=_history(s,generation,proposal_id);prior=next((r for r in history if r.operation_id==operation_id),None)
        if prior:
            legacy_digest=extraction.digest({'actor':authority.subject_id,'expectedRevision':expected_revision,'decisions':decisions})
            legacy_retry='reviewOrigin' not in prior.doc and review_origin=='user_submission_unverified' and prior.digest==legacy_digest
            if prior.digest!=digest and not legacy_retry:raise problem(409,'WORKING_OPERATION_CONFLICT','操作编号内容冲突')
        else:
            if len(history)!=expected_revision:raise problem(409,'WORKING_REVISION_CONFLICT','请读取最新复核版本')
            event=WorkingReview(incarnation=generation,proposal_id=proposal_id,seq=expected_revision+1,operation_id=operation_id,digest=digest,
                doc={'revision':expected_revision+1,'authorSubjectId':authority.subject_id,'recordedUtc':iso(now_utc()),'decisions':decisions,'reviewedAsWorkingOnly':True,'factVerified':False,'reviewOrigin':review_origin})
            s.add(event);s.flush()
        response=_view(s,row);response['replayed']=prior is not None
        _final(s,db,settings,token,case_id,row.record_id,row.binding,before,True)
        return response

def read(db,settings,token,case_id,proposal_id):
    j.canonical_id(proposal_id)
    with db.session() as s:
        before=_auth(s,token,case_id);row=s.get(WorkingProposal,(before[1],proposal_id))
        if row is None:raise problem(404,'WORKING_NOT_FOUND','工作提案不存在')
        _snapshot(s,db,settings,token,case_id,row.record_id,row.binding)
        response=_view(s,row)
        _final(s,db,settings,token,case_id,row.record_id,row.binding,before,False)
        return response

def list_records(db,settings,token,case_id):
    with db.session() as s:
        before=_auth(s,token,case_id)
        rows=list(s.scalars(select(WorkingProposal).where(WorkingProposal.incarnation==before[1]).order_by(WorkingProposal.proposal_id).limit(51)))
        if len(rows)>50:raise problem(413,'WORKING_LIMIT','工作清单超出预算')
        items=[]
        for row in rows:
            _snapshot(s,db,settings,token,case_id,row.record_id,row.binding)
            items.append({'proposalId':row.proposal_id,'recordId':row.record_id,'revision':len(_history(s,before[1],row.proposal_id)),'status':'working_unreviewed'})
        for row in rows:_final(s,db,settings,token,case_id,row.record_id,row.binding,before,False)
        if _auth(s,token,case_id)!=before:raise problem(403,'WORKING_ACCESS_CHANGED','授权变化')
        return {'caseId':case_id,'items':items,'persistence':'working_record_only','factActivated':False}


def find_generated(db,settings,token,case_id,record_id,operation_id,binding,provider_key):
    """Authorized cross-host retry lookup before inference; no historical bypass."""
    j.canonical_id(operation_id)
    with db.session() as s:
        before=_auth(s,token,case_id,True)
        _snapshot(s,db,settings,token,case_id,record_id,binding)
        row=s.scalars(select(WorkingProposal).where(WorkingProposal.incarnation==before[1],WorkingProposal.operation_id==operation_id)).first()
        response=None
        if row:
            if row.record_id!=record_id or row.binding!=binding or row.doc['generatedBySubjectId']!=before[0].subject_id or row.doc.get('providerKey')!=provider_key:
                raise problem(409,'WORKING_OPERATION_CONFLICT','操作编号内容冲突')
            response=_view(s,row);response['replayed']=True
        _final(s,db,settings,token,case_id,record_id,binding,before,True)
        return response
