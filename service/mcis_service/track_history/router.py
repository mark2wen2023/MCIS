from fastapi import APIRouter
from fastapi.responses import Response
from ..common.context import Ctx,CtxDep,problem
from ..db import WRITE_LOCK
from ..reports.access import NoStoreRoute,begin,require_content
from ..cases.service import load_case
from ..evidence.service import append_custody
from .service import read,entries
from ..working_records_archive.validation import sha
router=APIRouter(prefix='/api/v1/cases/{case_id}/archive-history/track-imports',tags=['track-history'],route_class=NoStoreRoute)
@router.get('')
def listing(case_id:str,vesselId:str,ctx:Ctx=CtxDep):
    with WRITE_LOCK,ctx.db.session()as s:
        begin(s);require_content(s,case_id,ctx.role);load_case(s,case_id)
        items=[read(ctx,s,case_id,r.key)[0]for r in entries(s,case_id)if r.doc['metadata']['vesselId']==vesselId]
    return {'caseId':case_id,'vesselId':vesselId,'mode':'archive-only','items':items}
@router.get('/{digest}')
def detail(case_id:str,digest:str,ctx:Ctx=CtxDep):
    with WRITE_LOCK,ctx.db.session()as s:
        begin(s);require_content(s,case_id,ctx.role);sha(digest);return read(ctx,s,case_id,digest)[0]
@router.get('/{digest}/{kind}')
def content(case_id:str,digest:str,kind:str,ctx:Ctx=CtxDep):
    with WRITE_LOCK,ctx.db.session()as s:
        begin(s);require_content(s,case_id,ctx.role);sha(digest)
        if kind not in ('source','report'):raise problem(404,'HISTORY_NOT_FOUND','没有此历史原件')
        summary,raws=read(ctx,s,case_id,digest);raw=raws[0 if kind=='source'else 1]
        append_custody(s,case_id=case_id,evidence_id=summary[kind+'EvidenceId'],kind='Access',operator=ctx.operator,role=ctx.role,sha256=summary[kind+'Sha256'],detail='读取航迹归档原件（非活跃回执）')
    name='source.csv'if kind=='source'else'report.json'
    return Response(raw,media_type='application/octet-stream',headers={'Content-Disposition':f'attachment; filename="{name}"','X-Sha256':summary[kind+'Sha256']})
