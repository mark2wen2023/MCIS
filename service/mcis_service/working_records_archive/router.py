"""Authorized historical bytes and latest-restore provenance; never replay."""
import hashlib
from fastapi import APIRouter
from fastapi.responses import Response
from sqlalchemy import select
from ..common.context import Ctx,CtxDep,problem
from ..db import WRITE_LOCK,get_doc
from ..cases.service import load_case
from ..reports.access import NoStoreRoute,require_content
from ..interviews.access import document as protect_interview,source as protect_source
from ..evidence import service as evidence
from ..evidence.models import EvidenceRow
from ..interviews.models import InterviewRow
from ..reports.models import ReportRow
from .service import archived_evidence,read_blob,full_access
from .validation import digest,fail

router=APIRouter(prefix='/api/v1/cases/{case_id}/archive-history',tags=['archive-history'],route_class=NoStoreRoute)

@router.get('/evidence/{evidence_id}/content')
def content(case_id:str,evidence_id:str,ctx:Ctx=CtxDep):
    with WRITE_LOCK,ctx.db.session()as s:
        require_content(s,case_id,ctx.role);load_case(s,case_id)
        item=protect_source(s,case_id,ctx.role,evidence_id)
        history=archived_evidence(s,case_id,evidence_id=evidence_id)
        if history is None:raise problem(404,'HISTORY_NOT_FOUND','没有可读取的历史原件记录')
        meta=history.doc['metadata']
        if item.get('relativePath')!=meta['relativePath']or item.get('sha256')!=meta['sourceSha256']:fail('历史原件登记不一致','ARCHIVE_HISTORY_INTEGRITY',409)
        raw=read_blob(ctx.settings.blob_dir,case_id,meta['relativePath'])
        h=hashlib.sha256(raw).hexdigest()
        if h!=meta['sourceSha256']:fail('历史原件完整性异常','ARCHIVE_HISTORY_INTEGRITY',409)
        evidence.append_custody(s,case_id=case_id,evidence_id=evidence_id,kind='Access',operator=ctx.operator,role=ctx.role,
                               sha256=h,detail='读取归档历史原件（非活跃导入回执）')
    return Response(raw,media_type='application/octet-stream',headers={'Content-Disposition':'attachment; filename="historical-source.bin"','X-Sha256':h,'Cache-Control':'no-store'})

@router.get('/provenance/{kind}/{record_id}')
def provenance(case_id:str,kind:str,record_id:str,ctx:Ctx=CtxDep):
    from ..package_intake.router import IntakeReceipt
    from ..package_intake.parser import parse_package
    with WRITE_LOCK,ctx.db.session()as s:
        require_content(s,case_id,ctx.role);load_case(s,case_id)
        if kind not in ('interview','report'):raise problem(422,'HISTORY_KIND','未知历史文档类型')
        current=get_doc(s,InterviewRow if kind=='interview'else ReportRow,case_id,record_id)
        if current is None:raise problem(404,'HISTORY_NOT_FOUND','当前文档不存在')
        full_access(s,ctx,case_id)
        if kind=='interview':protect_interview(s,ctx,current)
        result={'caseId':case_id,'kind':kind,'recordId':record_id,'provenance':None}
        row=s.scalars(select(IntakeReceipt).where(IntakeReceipt.case_id==case_id)).first()
        if row is None:return result
        raw=read_blob(ctx.settings.blob_dir,case_id,'_package_intake/source.mcase',32*1024*1024)
        if hashlib.sha256(raw).hexdigest()!=row.key or row.doc.get('sourceSha256')!=row.key or row.doc.get('byteLength')!=len(raw)or row.doc.get('caseId')!=case_id:fail('恢复来源完整性异常','ARCHIVE_HISTORY_INTEGRITY',409)
        try:parsed=parse_package(raw)
        except Exception:fail('恢复来源完整性异常','ARCHIVE_HISTORY_INTEGRITY',409)
        if parsed.case['caseId']!=case_id:fail('恢复来源案件不一致','ARCHIVE_HISTORY_INTEGRITY',409)
        for old in parsed.evidence:
            now=protect_source(s,case_id,ctx.role,old['evidenceId'])
            if now['sha256']!=old['sha256']:fail('恢复来源证据已变化','ARCHIVE_HISTORY_INTEGRITY',409)
        if parsed.working_archive is None:return result
        for entry in parsed.working_archive.data['interviews']:protect_interview(s,ctx,entry['doc'])
        coll='interviews'if kind=='interview'else'reports'
        entries=[e for e in parsed.working_archive.data[coll]if e['key']==record_id]
        if not entries:return result
        if len(entries)!=1:fail('恢复来源文档不唯一','ARCHIVE_HISTORY_INTEGRITY',409)
        old=entries[0]['doc'];before=digest(old);after=digest(current)
        result['provenance']={'origin':'restored-history','sourceArchiveSha256':row.key,'importedUtc':row.doc['importedUtc'],
                              'originalDocumentSha256':before,'currentDocumentSha256':after,'changedSinceImport':before!=after}
        return result
