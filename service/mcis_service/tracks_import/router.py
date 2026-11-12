"""Case-scoped first-track import. SQLite transaction + exclusive immutable blob writes.

One-process WRITE_LOCK is the existing service's concurrency boundary. A process crash
between blob creation and DB commit may leave an unreferenced orphan; no crash-ACID claim.
"""
from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import func, select

from ..audit import service as audit
from ..cases.models import TrackPointRow, VesselRow
from ..cases.service import load_case
from ..common import contracts
from ..common.context import Ctx, CtxDep, problem
from ..common.timeutil import iso, now_utc
from ..db import WRITE_LOCK, get_doc, put_doc
from ..evidence import service as evidence
from ..evidence.models import EvidenceRow
from ..redaction.gateway import filter_evidence, get_policy, require
from .parser import MAX_BODY, MAX_BYTES, SAFE_ID, canonical, inputs, preview, sha

router=APIRouter(prefix='/api/v1/cases/{case_id}', tags=['tracks-import'])


def authorize(ctx,s,case_id,*,write=False):
    if ctx.role not in ('Investigator','LeadInvestigator'):
        raise problem(403,'FORBIDDEN','此航迹输入与原件仅向调查组开放')
    if not SAFE_ID.fullmatch(case_id):
        raise problem(422,'CASE_ID','案件编号不适用于此输入切片')
    case=load_case(s,case_id)
    require(ctx,s,case_id,'ais_sim',write=write)
    require(ctx,s,case_id,'evidence_meta',write=write)
    # Both evidence items are Restricted. Honor any stricter current policy too.
    if not filter_evidence([{'confidentiality':'Restricted'}],ctx.role,get_policy(s,case_id)):
        raise problem(403,'FORBIDDEN','当前政策不允许访问受限原件')
    return case


def count_points(s,case_id,vessel_id):
    return s.scalar(select(func.count()).select_from(TrackPointRow).where(TrackPointRow.case_id==case_id,TrackPointRow.vessel_id==vessel_id)) or 0


def vessel(s,case_id,vessel_id):
    if get_doc(s,VesselRow,case_id,vessel_id) is None:
        raise problem(404,'VESSEL_NOT_FOUND','须先在本案件登记船舶，不自动新建或匹配 MMSI')


async def body_bounded(request):
    if request.headers.get('content-type','').split(';')[0].strip().lower()!='application/json':
        raise problem(415,'CONTENT_TYPE','仅接受 application/json')
    data=bytearray()
    async for chunk in request.stream():
        if len(data)+len(chunk)>MAX_BODY:
            raise problem(413,'REQUEST_LIMIT','请求体不得超过 1536 KiB')
        data.extend(chunk)
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d: raise ValueError('duplicate key')
            d[k]=v
        return d
    try:
        return json.loads(data,object_pairs_hook=unique,parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError,UnicodeError,RecursionError):
        raise problem(422,'JSON','请求必须为无重复键的有效 JSON')


def rels(digest):
    if not re.fullmatch('[0-9a-f]{64}',digest):
        raise problem(422,'DIGEST','摘要格式无效')
    root=f'raw/track-imports/{digest}'
    return root+'/source.csv',root+'/report.json'


def file_path(ctx,case_id,rel):
    # Do not follow symlinked case/import directories to write or expose other files.
    root=ctx.settings.blob_dir.resolve()
    path=root/case_id/rel
    current=root
    for part in path.relative_to(root).parts:
        current=current/part
        if current.is_symlink(): raise problem(409,'BLOB_PATH','存储路径含符号链接，已拒绝')
    return path


MAX_REPORT_BYTES=256*1024


def read_bounded_file(path,limit):
    with path.open('rb') as f:
        content=f.read(limit+1)
    if len(content)>limit: raise ValueError('file budget')
    return content


def read_report(ctx,s,case_id,digest,item):
    """Bounded small report validation, used to select a vessel before CSV rebuild."""
    if not filter_evidence([item],ctx.role,get_policy(s,case_id)):
        raise problem(403,'FORBIDDEN','受限导入记录')
    try:
        data=read_bounded_file(file_path(ctx,case_id,rels(digest)[1]),MAX_REPORT_BYTES)
        if sha(data)!=item['sha256'] or item['caseId']!=case_id: raise ValueError('hash/case')
        saved=json.loads(data)
        receipt=saved['receipt']
        if (saved['format']!='MCIS-TRACK-IMPORT-1' or receipt['caseId']!=case_id
                or receipt['previewDigest']!=digest or receipt['reportEvidenceId']!=item['evidenceId']
                or not isinstance(receipt['vesselId'],str) or not SAFE_ID.fullmatch(receipt['vesselId'])
                or saved['metadata']['vesselId']!=receipt['vesselId']):
            raise ValueError('identity')
        return saved,data
    except (OSError,ValueError,KeyError,TypeError,UnicodeError,RecursionError):
        raise problem(409,'IMPORT_INTEGRITY','导入记录缺失、超出预算或哈希/归属不匹配；未核对为保存成功')


def load_receipt(ctx,s,case_id,digest):
    source_rel, report_rel=rels(digest)
    rows=s.scalars(select(EvidenceRow).where(EvidenceRow.case_id==case_id)).all()
    source_items=[r.doc for r in rows if r.doc.get('relativePath')==source_rel]
    report_items=[r.doc for r in rows if r.doc.get('relativePath')==report_rel]
    if len(source_items)>1 or len(report_items)>1:
        raise problem(409,'IMPORT_INTEGRITY','导入原件记录重复，无法唯一核对')
    source=source_items[0] if source_items else None
    report=report_items[0] if report_items else None
    if source is None and report is None: return None
    if source is None or report is None:
        raise problem(409,'IMPORT_INCOMPLETE','导入原件记录不完整，禁止重复覆盖')
    if len(filter_evidence([source,report],ctx.role,get_policy(s,case_id)))!=2:
        raise problem(403,'FORBIDDEN','受限导入原件')
    try:
        raw=read_bounded_file(file_path(ctx,case_id,source_rel),MAX_BYTES)
        saved,report_bytes=read_report(ctx,s,case_id,digest,report)
        if sha(raw)!=source['sha256'] or sha(report_bytes)!=report['sha256']:
            raise ValueError('hash')
        receipt=saved['receipt']
        if receipt['previewDigest']!=digest or receipt['caseId']!=case_id or receipt['sourceSha256']!=sha(raw):
            raise ValueError('identity')
        if receipt['sourceEvidenceId']!=source['evidenceId'] or receipt['reportEvidenceId']!=report['evidenceId']:
            raise ValueError('evidence')
        # A historical receipt is not proof that the current saved track still exists.
        # Rebuild the entire expected first import from immutable CSV + declared metadata,
        # using the CURRENT case epoch. Never repair missing/changed data during a read.
        if saved['format']!='MCIS-TRACK-IMPORT-1' or saved['role'] not in ('Investigator','LeadInvestigator'):
            raise ValueError('format')
        if not isinstance(saved['operator'],str) or not saved['operator']:
            raise ValueError('operator')
        metadata=saved['metadata']
        body={**metadata,'contentBase64':base64.b64encode(raw).decode('ascii')}
        inputs(body)
        case=load_case(s,case_id)
        rebuilt,expected=preview(body,raw,case,operator=saved['operator'],role=saved['role'],existing_count=0)
        if (not rebuilt['canCommit'] or rebuilt['previewDigest']!=digest
                or rebuilt['sourceSha256']!=receipt['sourceSha256']
                or rebuilt['vesselId']!=receipt['vesselId']
                or type(receipt['pointCount']) is not int or receipt['pointCount']!=len(expected)
                or canonical(saved['preview'])!=canonical(rebuilt)):
            raise ValueError('rebuild')
        vessel(s,case_id,receipt['vesselId'])
        if count_points(s,case_id,receipt['vesselId'])!=len(expected):
            raise ValueError('point count')
        current=s.scalars(select(TrackPointRow).where(TrackPointRow.case_id==case_id,
                          TrackPointRow.vessel_id==receipt['vesselId']).order_by(TrackPointRow.time_sec,TrackPointRow.id)
                          .limit(len(expected)+1)).all()
        if len(current)!=len(expected):
            raise ValueError('point count')
        for n,(row,point) in enumerate(zip(current,expected),1):
            expected_doc={**point,'source':f'CSV:{source["evidenceId"]}:row:{n}'}
            if row.time_sec!=point['timeSec'] or canonical(row.doc)!=canonical(expected_doc):
                raise ValueError('point content')
    except (OSError,ValueError,KeyError,TypeError,UnicodeError,RecursionError,HTTPException):
        raise problem(409,'IMPORT_INTEGRITY','当前航迹点、案件纪元或导入原件/记录不完整或不匹配；未核对为保存成功，也未修复数据')
    return {**receipt,'reportSha256':sha(report_bytes)},raw,report_bytes


@router.post('/track-imports:preview')
async def preview_input(case_id: str,request: Request,ctx: Ctx=CtxDep):
    # Gate before ingesting potentially large body.
    with ctx.db.session() as s: authorize(ctx,s,case_id,write=True)
    body=await body_bounded(request)
    raw=inputs(body)
    with ctx.db.session() as s:
        case=authorize(ctx,s,case_id,write=True)
        vessel(s,case_id,body['vesselId'])
        result,_=preview(body,raw,case,operator=ctx.operator,role=ctx.role,existing_count=count_points(s,case_id,body['vesselId']))
        return result


def exclusive_write(path: Path,data: bytes,created: list[Path]):
    path.parent.mkdir(parents=True,exist_ok=True)
    try:
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError:
        raise problem(409,'BLOB_EXISTS','目标原件已存在；不覆盖，需检查之前的导入状态')
    created.append(path)
    with os.fdopen(fd,'wb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


@router.post('/track-imports:commit')
async def commit_input(case_id: str,request: Request,ctx: Ctx=CtxDep):
    with ctx.db.session() as s: authorize(ctx,s,case_id,write=True)
    body=await body_bounded(request)
    raw=inputs(body,commit=True)
    created=[]
    # Covers session exit/commit as well as all blob writes. Failures roll back DB
    # then remove only files exclusively created by this attempt, never preexisting files.
    with WRITE_LOCK:
        try:
            with ctx.db.session() as s:
                case=authorize(ctx,s,case_id,write=True)
                vessel(s,case_id,body['vesselId'])
                result,points=preview(body,raw,case,operator=ctx.operator,role=ctx.role,existing_count=0)
                digest=result['previewDigest']
                if digest!=body['previewDigest']:
                    raise problem(409,'PREVIEW_STALE','内容、身份、导入配置或案件纪元已变化，请重新预览')
                saved=load_receipt(ctx,s,case_id,digest)
                if saved:
                    return {**saved[0],'replayed':True}
                if count_points(s,case_id,body['vesselId']):
                    raise problem(409,'TRACK_EXISTS','该船已有航迹，本切片不覆盖、不追加')
                if not result['canCommit']:
                    raise problem(422,'IMPORT_BLOCKED','存在阻断诊断，整批未保存',result)
                stamp=iso(now_utc())
                source_rel,report_rel=rels(digest)
                source_id=evidence.next_id(s,case_id)
                common={'caseId':case_id,'source':body['source'],'extractedBy':ctx.operator,
                        'extractedUtc':stamp,'confidentiality':'Restricted','category':'Other',
                        'note':'接收登记时间，不是源采集时间；来源及时间依据为提供者声明。'}
                source_item={**common,'evidenceId':source_id,'title':body['fileName'],
                             'sha256':sha(raw),'relativePath':source_rel}
                contracts.validate('evidence-item',source_item)
                put_doc(s,EvidenceRow,case_id,source_id,source_item)
                report_id=evidence.next_id(s,case_id)
                receipt={'caseId':case_id,'vesselId':body['vesselId'],'previewDigest':digest,
                         'sourceSha256':sha(raw),'pointCount':len(points),'sourceEvidenceId':source_id,
                         'reportEvidenceId':report_id,'committedUtc':stamp}
                report_data=canonical({'format':'MCIS-TRACK-IMPORT-1','receipt':receipt,
                                       'metadata':{k:v for k,v in body.items() if k not in ('contentBase64','confirmed','previewDigest')},
                                       'preview':result,'operator':ctx.operator,'role':ctx.role,
                                       'pointSourceFormat':f'CSV:{source_id}:row:<1-based-data-row>',
                                       'limitations':['原件是本次上传的 CSV 字节，不证明原始 AIS 报文或采集链完整。',
                                                      'reported 为来源声明；未清洗或插值，未评定时间精度。']})
                report_item={**common,'evidenceId':report_id,'title':'航迹输入记录 '+body['fileName'],
                             'sha256':sha(report_data),'relativePath':report_rel}
                contracts.validate('evidence-item',report_item)
                put_doc(s,EvidenceRow,case_id,report_id,report_item)
                for n,p in enumerate(points,1):
                    p={**p,'source':f'CSV:{source_id}:row:{n}'}
                    contracts.validate('track-point',p)
                    s.add(TrackPointRow(case_id=case_id,vessel_id=body['vesselId'],time_sec=p['timeSec'],doc=p))
                for item in (source_item,report_item):
                    evidence.append_custody(s,case_id=case_id,evidence_id=item['evidenceId'],kind='Register',
                        operator=ctx.operator,role=ctx.role,sha256=item['sha256'],detail='W10.2 CSV输入原件/派生记录登记',item=item)
                audit.append(s,case_id=case_id,operator=ctx.operator,role=ctx.role,action='track.import',category='Case',
                             command='人工确认单船首次航迹输入',after=receipt,entity_type='track-import',entity_id=digest)
                exclusive_write(file_path(ctx,case_id,source_rel),raw,created)
                exclusive_write(file_path(ctx,case_id,report_rel),report_data,created)
                s.flush()
            return {**receipt,'reportSha256':sha(report_data),'replayed':False}
        except BaseException as error:
            cleanup_failed=False
            for path in reversed(created):
                try: path.unlink()
                except FileNotFoundError: pass
                except OSError: cleanup_failed=True
            if cleanup_failed:
                raise problem(500,'IMPORT_CLEANUP_FAILED','保存未成功；本次原件清理未全部完成，请检查存储状态，勿将本次视为已保存') from error
            raise


@router.get('/track-imports')
def list_inputs(case_id: str,vesselId: str,ctx: Ctx=CtxDep):
    with ctx.db.session() as s:
        authorize(ctx,s,case_id)
        vessel(s,case_id,vesselId)
        candidates=[]
        for row in s.scalars(select(EvidenceRow).where(EvidenceRow.case_id==case_id)):
            rel=row.doc.get('relativePath','')
            match=re.fullmatch(r'raw/track-imports/([0-9a-f]{64})/report\.json',rel)
            if match:
                # Other vessels: only verify/read bounded metadata, never decode their
                # CSV or query/rebuild their track points on this vessel's request.
                saved,_=read_report(ctx,s,case_id,match.group(1),row.doc)
                if saved['receipt']['vesselId']==vesselId:
                    candidates.append(match.group(1))
        if len(candidates)>1:
            raise problem(409,'IMPORT_INTEGRITY','本船有多条首次导入记录，无法唯一核对')
        if not candidates: return []
        saved=load_receipt(ctx,s,case_id,candidates[0])
        return [{**saved[0],'replayed':True}]


@router.get('/track-imports/{digest}')
def receipt_input(case_id: str,digest: str,ctx: Ctx=CtxDep):
    with ctx.db.session() as s:
        authorize(ctx,s,case_id)
        saved=load_receipt(ctx,s,case_id,digest)
        if saved is None: raise problem(404,'IMPORT_NOT_FOUND','没有找到该预览摘要的已保存记录')
        return {**saved[0],'replayed':True}


@router.get('/track-imports/{digest}/{kind}')
def read_input(case_id: str,digest: str,kind: str,ctx: Ctx=CtxDep):
    if kind not in ('source','report'): raise problem(404,'NOT_FOUND','原件类型不存在')
    with ctx.db.session() as s:
        authorize(ctx,s,case_id)
        saved=load_receipt(ctx,s,case_id,digest)
        if saved is None: raise problem(404,'IMPORT_NOT_FOUND','没有找到已保存记录')
        data=saved[1] if kind=='source' else saved[2]
        name='source.csv' if kind=='source' else 'report.json'
        return Response(data,media_type='application/octet-stream',headers={
            'Content-Disposition':f'attachment; filename="{name}"','X-Sha256':sha(data),'Cache-Control':'no-store'})
