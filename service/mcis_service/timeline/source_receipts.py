"""Registry observation receipts. No file reads or human-reading verification."""
from copy import deepcopy
from datetime import timedelta
import hashlib
import re
import uuid
from sqlalchemy import Column, Integer, String, JSON, select
from ..db import Base
from ..common.context import problem
from ..common.timeutil import now_utc, iso, parse_iso
from ..evidence.service import custody_events, derive
from ..interviews.access import source
from . import revisions


class ConflictSourceReceipt(Base):
    __tablename__='conflict_source_receipts'
    id=Column(String(36),primary_key=True)
    case_id=Column(String(64),nullable=False,index=True)
    conflict_id=Column(String(64),nullable=False)
    doc=Column(JSON,nullable=False)
    consumed_revision=Column(Integer,nullable=True)


def changed(before,after):
    return [side for side in ('a','b') if before.get(side)!=after.get(side)]


def registry(s,ctx,case_id,before,after):
    sides=changed(before,after)
    if not sides:raise problem(422,'SOURCE_CHANGE_REQUIRED','观察未改变，无需来源回执')
    # Check both old and new references for each changed observation. Removing an
    # unknown source must not turn it into an implicitly verified new observation.
    refs=set()
    for side in sides:
        for doc in (before,after):
            ref=doc[side].get('evidenceId')
            if not isinstance(ref,str) or not ref:
                raise problem(409,'SOURCE_VERSION_UNKNOWN','变更侧原来源或新来源未知，暂不能核对；请保留输入')
            refs.add(ref)
    docs={ref:source(s,case_id,ctx.role,ref) for ref in sorted(refs)}
    result={}
    for ref,doc in docs.items():
        events=custody_events(s,case_id,ref)
        current=derive(doc,events).get('currentSha256') if isinstance(doc.get('sha256'),str) else None
        if doc.get('caseId')!=case_id or not isinstance(current,str) or not re.fullmatch('[a-f0-9]{64}',current):
            raise problem(409,'SOURCE_VERSION_UNKNOWN','来源登记版本未知，未保存')
        result[ref]={'sha256':current,'registryDocSha256':revisions.digest(doc),
                     'custodyHeadSeq':events[-1].seq if events else None,
                     'custodyHeadSha256':hashlib.sha256(events[-1].line.encode()).hexdigest() if events else None,
                     'bytesVerified':False}
    return result


def issue(s,ctx,case_id,key,before,after,expected):
    revisions.expect_version(s,case_id,key,before,expected)
    observed=registry(s,ctx,case_id,before,after)
    now=now_utc(); token=str(uuid.uuid4())
    doc={'kind':'registry-observation-v1','caseId':case_id,'conflictId':key,
         'conflictVersion':expected,'observationsSha256':revisions.digest({x:after[x] for x in ('a','b')}),
         'role':ctx.role,'operator':ctx.operator,'issuedUtc':iso(now),'expiresUtc':iso(now+timedelta(minutes=10)),
         'sources':observed,'bytesVerified':False,'humanReadVerified':False,'identityVerified':False}
    s.add(ConflictSourceReceipt(id=token,case_id=case_id,conflict_id=key,doc=doc))
    s.flush()
    return {'receiptId':token,**deepcopy(doc)}


def accept(s,ctx,case_id,key,before,after,token,expected):
    # Recheck stricter permissions before revealing receipt/version applicability.
    current=registry(s,ctx,case_id,before,after)
    row=s.get(ConflictSourceReceipt,token) if isinstance(token,str) and len(token)==36 else None
    if row is None or row.case_id!=case_id or row.conflict_id!=key:
        raise problem(409,'SOURCE_RECEIPT_UNAVAILABLE','回执未知或不适用；保留输入，未保存')
    d=row.doc;now=now_utc()
    if (row.consumed_revision is not None or d['role']!=ctx.role or d['operator']!=ctx.operator
        or not parse_iso(d['issuedUtc'])<=now<parse_iso(d['expiresUtc'])
        or d['conflictVersion']!=expected
        or d['observationsSha256']!=revisions.digest({x:after[x] for x in ('a','b')})):
        raise problem(409,'SOURCE_RECEIPT_UNAVAILABLE','回执过期、已使用或与输入不符；保留输入，未保存')
    if current!=d['sources']:
        raise problem(412,'SOURCE_VERSION_CHANGED','登记版本已变化；保留草稿，重新查看登记版本并比对，未保存')
    return row
