"""Nonproduction minimal authorized discovery. No legacy listing passthrough."""
from types import SimpleNamespace
from sqlalchemy import select
from fastapi import HTTPException
from .local import authorize_session, authorize_read, Membership
from ..reports.access import require_content
from ..cases.service import load_case
from ..cases.incarnation import current
from ..common.context import problem
from ..evidence_intake.incarnation import SourceIncarnationRow, current as source_current
from ..evidence_intake.router import authorize as intake_authorize, load_receipt

MAX_ITEMS=100

def limit(rows):
    if len(rows)>MAX_ITEMS:raise problem(413,'CATALOG_LIMIT','试验清单超过单次预算，未返回部分列表')
    return rows


def cases(db,token):
    with db.session() as s:
        before=authorize_session(s,token);subject=before[0]
        rows=limit(list(s.scalars(select(Membership).where(Membership.subject_id==subject,
            Membership.enabled.is_(True)).order_by(Membership.case_id).limit(MAX_ITEMS+1))))
        items=[]
        for row in rows:
            try:
                authority=authorize_read(s,token,row.case_id)
                if row.case_incarnation!=current(s,row.case_id):continue
                require_content(s,row.case_id,authority.role)
                doc=load_case(s,row.case_id)
                items.append({'caseId':row.case_id,'caseIncarnation':row.case_incarnation,'caseEpochUtc':doc['caseEpochUtc']})
            except HTTPException as error:
                if error.status_code not in (403,404,409):raise
                # Never expose other/old/denied cases, titles, counts or reasons.
                continue
        if authorize_session(s,token)!=before:raise problem(403,'LOCAL_AUTHORITY_DENIED','会话变化')
        return {'profile':'trial-authorized-cases-v1','items':items}


def sources(db,settings,token,case_id):
    with db.session() as s:
        try:before=authorize_read(s,token,case_id)
        except HTTPException:
            raise problem(403,'LOCAL_AUTHORITY_DENIED','身份或案件授权无效') from None
        require_content(s,case_id,before.role)
        ctx=SimpleNamespace(db=db,settings=settings,role=before.role,operator=before.subject_id)
        intake_authorize(ctx,s,case_id)
        generation=current(s,case_id)
        rows=limit(list(s.scalars(select(SourceIncarnationRow).where(SourceIncarnationRow.case_id==case_id,
            SourceIncarnationRow.case_incarnation==generation).order_by(SourceIncarnationRow.evidence_id).limit(MAX_ITEMS+1))))
        items=[]
        for row in rows:
            identity=source_current(ctx,s,case_id,row.evidence_id)
            found=load_receipt(ctx,s,case_id,row.request_digest)
            if found is None:raise problem(409,'CATALOG_SOURCE_CHANGED','登记变化')
            receipt,raw=found
            # No title, filename/path, operator, metadata body, source text or
            # archive-history rows. Only supported current candidates projected.
            filename=receipt['fileName'].lower()
            kind='csv' if filename.endswith('.csv') else 'pdf' if filename.endswith('.pdf') and receipt['evidence']['category']=='Document' else None
            if kind is None:continue
            items.append({'evidenceId':row.evidence_id,'sourceSha256':receipt['sourceSha256'],
                'registrationDigest':receipt['requestDigest'],'byteLength':len(raw),
                'registeredUtc':receipt['registeredUtc'],'sourceIncarnation':identity['incarnation'],
                'mediaKind':kind,'observationApproval':'not_assessed'})
        response={'profile':'trial-current-sources-v1','caseId':case_id,'caseIncarnation':generation,
            'caseEpochUtc':load_case(s,case_id)['caseEpochUtc'],'items':items,
            'scope':'current-local-supported-candidates-only'}
        if authorize_read(s,token,case_id)!=before:raise problem(403,'LOCAL_AUTHORITY_DENIED','授权变化')
        return response
