"""IQ-1 restricted manual API. Local self-reported role headers, not authentication."""
from copy import deepcopy
from uuid import uuid4
from fastapi import APIRouter,Request,Query
from fastapi.responses import JSONResponse
from sqlalchemy import select
from ..common.context import Ctx,CtxDep,problem
from ..common.timeutil import now_utc,iso
from ..db import WRITE_LOCK,get_doc,get_row
from ..cases.models import CaseRow
from ..evidence.models import EvidenceRow
from ..interviews.access import source as protect_source
from ..reports.access import NoStoreRoute,require_content
from .models import IssueRow,EventRow,ReceiptRow
from .domain import fail,obj,txt,uid,integer,parse,digest,refs,transition,MAX_BODY
router=APIRouter(prefix='/api/v1/cases/{case_id}/investigation-issues',tags=['investigation-issues'],route_class=NoStoreRoute)

def authorize(s,ctx,case_id,write=False):
    # Free text can contain all categories. Fail closed, not selective redaction.
    require_content(s,case_id,ctx.role,write=write)
    if get_doc(s,CaseRow,case_id,case_id)is None: raise problem(404,'CASE_NOT_FOUND','案件不存在')
    txt(ctx.operator,128)

def source_check(s,ctx,case_id,source_refs,current=False):
    stale=False
    for r in source_refs:
        doc=get_doc(s,EvidenceRow,case_id,r['evidenceId'])
        if not isinstance(doc,dict)or doc.get('caseId')!=case_id: raise problem(403,'SOURCE_UNAVAILABLE','来源不存在或无权访问')
        protect_source(s,case_id,ctx.role,r['evidenceId'])
        if doc.get('sha256')!=r['sha256']: stale=True
    if current and stale:fail('SOURCE_VERSION_CHANGED',409)
    return stale

def stale(s,ctx,cid,doc):
    changed=source_check(s,ctx,cid,doc['initialSources'])
    for h in doc['hypotheses'].values(): changed=source_check(s,ctx,cid,h['sourceRefs'])or changed
    for v in doc['currentVerifications'].values(): changed=source_check(s,ctx,cid,v['sourceRefs'])or changed
    return changed

def historical_access(s,ctx,cid,iid):
    # A deleted/restricted historical reference must not leak through events or receipts.
    for event in s.scalars(select(EventRow).where(EventRow.case_id==cid,EventRow.issue_id==iid)):
        source_check(s,ctx,cid,event.doc.get('payload',{}).get('sourceRefs',[]))

def issue(s,ctx,cid,iid):
    uid(iid);row=get_row(s,IssueRow,cid,iid)
    if row is None: raise problem(404,'ISSUE_NOT_FOUND','问题不存在')
    historical_access(s,ctx,cid,iid)
    return row

def view(s,ctx,cid,row):
    d=deepcopy(row.doc);d['sourcesStale']=stale(s,ctx,cid,d)
    d['archiveSupported']=False;d['identityMode']='unverified-self-reported'
    return d

async def body(request):
    if request.headers.get('content-type','').split(';')[0].strip().lower()!='application/json':fail('CONTENT_TYPE',415)
    raw=bytearray()
    async for part in request.stream():
        if len(raw)+len(part)>MAX_BODY: fail('ISSUE_LIMIT',413)
        raw.extend(part)
    return parse(raw)

def receipt(s,ctx,cid,rid):
    return s.scalar(select(ReceiptRow).where(ReceiptRow.case_id==cid,ReceiptRow.role==ctx.role,ReceiptRow.operator==ctx.operator,ReceiptRow.request_id==rid))

def save_receipt(s,ctx,cid,b,iid,response):
    s.add(ReceiptRow(case_id=cid,role=ctx.role,operator=ctx.operator,request_id=b['requestId'],digest=digest(b),issue_id=iid,response=deepcopy(response)))
    s.flush()

@router.post('',status_code=201)
async def create(case_id:str,request:Request,ctx:Ctx=CtxDep):
    # Authorize before parsing user text and check again inside the write transaction.
    with ctx.db.session()as s:authorize(s,ctx,case_id,True)
    b=await body(request);obj(b,('requestId','title','description','sourceRefs','acknowledgeArchiveUnsupported'))
    uid(b['requestId']);txt(b['title'],200);txt(b['description']);r=refs(b['sourceRefs'])
    if b['acknowledgeArchiveUnsupported']is not True:fail('ARCHIVE_ACK_REQUIRED',409)
    with WRITE_LOCK,ctx.db.session()as s:
        authorize(s,ctx,case_id,True)
        old=receipt(s,ctx,case_id,b['requestId'])
        if old:
            if old.digest!=digest(b):fail('REQUEST_REUSE',409)
            issue(s,ctx,case_id,old.issue_id)
            return JSONResponse(old.response,status_code=200)
        source_check(s,ctx,case_id,r,True)
        if len(s.scalars(select(IssueRow.id).where(IssueRow.case_id==case_id).limit(201)).all())>=200:fail('ISSUE_LIMIT',413)
        iid=str(uuid4());utc=iso(now_utc())
        d={'issueId':iid,'caseId':case_id,'title':b['title'],'description':b['description'],'initialSources':r,'revision':1,'stage':'Observed','round':0,'hypotheses':{},'currentVerifications':{},'packet':None,'createdBy':ctx.operator,'createdUtc':utc}
        ev={'sequence':1,'type':'Create','payload':{'title':b['title'],'description':b['description'],'sourceRefs':r},'actor':ctx.operator,'role':ctx.role,'utc':utc,'resultingStage':'Observed'}
        s.add(IssueRow(case_id=case_id,key=iid,doc=d));s.add(EventRow(case_id=case_id,issue_id=iid,seq=1,doc=ev))
        response={'issueId':iid,'revision':1,'event':ev};save_receipt(s,ctx,case_id,b,iid,response)
        return JSONResponse(response,status_code=201)

@router.get('')
def listing(case_id:str,offset:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=50),ctx:Ctx=CtxDep):
    with ctx.db.session()as s:
        authorize(s,ctx,case_id)
        rows=s.scalars(select(IssueRow).where(IssueRow.case_id==case_id).order_by(IssueRow.id).offset(offset).limit(limit+1)).all()
        items=[]
        for row in rows[:limit]:
            historical_access(s,ctx,case_id,row.key);v=view(s,ctx,case_id,row)
            items.append({k:v[k]for k in ('issueId','title','revision','stage','sourcesStale','archiveSupported')})
        return {'items':items,'nextOffset':offset+limit if len(rows)>limit else None}

@router.get('/{iid}')
def read(case_id:str,iid:str,ctx:Ctx=CtxDep):
    with ctx.db.session()as s:
        authorize(s,ctx,case_id);row=issue(s,ctx,case_id,iid)
        return JSONResponse(view(s,ctx,case_id,row),headers={'ETag':str(row.doc['revision'])})

@router.get('/{iid}/events')
def events(case_id:str,iid:str,after:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),ctx:Ctx=CtxDep):
    with ctx.db.session()as s:
        authorize(s,ctx,case_id);issue(s,ctx,case_id,iid)
        rows=s.scalars(select(EventRow).where(EventRow.case_id==case_id,EventRow.issue_id==iid,EventRow.seq>after).order_by(EventRow.seq).limit(limit+1)).all()
        return {'items':[deepcopy(r.doc)for r in rows[:limit]],'nextAfter':rows[limit-1].seq if len(rows)>limit else None}

@router.post('/{iid}/events')
async def append(case_id:str,iid:str,request:Request,ctx:Ctx=CtxDep):
    with ctx.db.session()as s:authorize(s,ctx,case_id,True)
    b=await body(request);obj(b,('requestId','expectedRevision','type','payload'))
    uid(b['requestId']);integer(b['expectedRevision']);txt(b['type'],50)
    fingerprint={**b,'issueId':iid}
    with WRITE_LOCK,ctx.db.session()as s:
        authorize(s,ctx,case_id,True);row=issue(s,ctx,case_id,iid)
        old=receipt(s,ctx,case_id,b['requestId'])
        if old:
            if old.digest!=digest(fingerprint):fail('REQUEST_REUSE',409)
            return deepcopy(old.response)
        if row.doc['revision']!=b['expectedRevision']:fail('REVISION_CONFLICT',409)
        if row.doc['revision']>=500:fail('ISSUE_LIMIT',413)
        if b['type']=='RecordDiscussion' and stale(s,ctx,case_id,row.doc):fail('SOURCE_VERSION_CHANGED',409)
        seq=row.doc['revision']+1;new=transition(row.doc,b['type'],b['payload'],seq)
        if 'sourceRefs'in b['payload']:source_check(s,ctx,case_id,refs(b['payload']['sourceRefs']),True)
        if b['type']in ('SubmitDiscussion','RecordDiscussion') and stale(s,ctx,case_id,new):fail('SOURCE_VERSION_CHANGED',409)
        utc=iso(now_utc());ev={'sequence':seq,'type':b['type'],'payload':deepcopy(b['payload']),'actor':ctx.operator,'role':ctx.role,'utc':utc,'resultingStage':new['stage'],'round':new['round']}
        if b['type']=='SubmitDiscussion':ev['packet']=deepcopy(new['packet'])
        if b['type']=='RecordDiscussion':ev['packet']=deepcopy(row.doc['packet'])
        row.doc=new;row.updated_utc=utc;s.add(EventRow(case_id=case_id,issue_id=iid,seq=seq,doc=ev))
        response={'issueId':iid,'revision':seq,'event':ev};save_receipt(s,ctx,case_id,fingerprint,iid,response)
        return response

def protect_export(s,case_id,role):
    exists=any(s.scalar(select(m.id).where(m.case_id==case_id).limit(1))is not None for m in (IssueRow,EventRow,ReceiptRow))
    if exists:
        require_content(s,case_id,role)
        raise problem(409,'ISSUE_ARCHIVE_UNSUPPORTED','案件包含调查问题历史，尚无完整归档支持，未生成部分案件包')
