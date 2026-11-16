"""Explicit public-page local tasks; disabled unless runtime is configured by host.
Running/unknown tasks are never automatically restarted or deleted.
"""
import asyncio
import base64
from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
from fastapi import APIRouter, Request
from fastapi.responses import Response
from sqlalchemy import Column, String, JSON, select
from ..common.context import Ctx, CtxDep, problem
from ..common.timeutil import iso, now_utc
from ..db import WRITE_LOCK
from ..reports.access import NoStoreRoute, begin
from ..evidence_intake.router import authorize, body_bounded
from ..evidence_intake.parser import sha, canonical, text
from ..audit import service as audit
from .app import Storage, Record, receipts
from .ppocr import convert

PDF_SHA='99084b8e672da6e2f8d9809bea25a92fe5fcf31c318554832e14339610015d7f'
IMAGE_SHA='e097321c40047e305beb50f2676370f89a452ba49a11dc962ec4add9b6a70aff'

@dataclass(frozen=True)
class LocalRuntime:
    python: Path
    models: Path
    cache: Path

class Task(Storage):
    __tablename__='image_ocr_tasks'
    task_id=Column(String,primary_key=True)
    case_id=Column(String,nullable=False,index=True)
    doc=Column(JSON,nullable=False)

router=APIRouter(prefix='/api/v1/cases/{case_id}/image-ocr-tasks',route_class=NoStoreRoute)

def get_task(s,case_id,task_id):
    row=s.get(Task,task_id)
    if row is None or row.case_id!=case_id:raise problem(404,'OCR_TASK_NOT_FOUND','本案未找到任务')
    return row

def public_doc(row):
    return {k:v for k,v in row.doc.items() if k not in ('rawBase64','candidateBase64')}

def checked_artifact(row,kind):
    field={'raw':'rawBase64','candidate':'candidateBase64'}[kind]
    data=base64.b64decode(row.doc[field],validate=True)
    if sha(data)!=row.doc['artifacts'][kind]['sha256']:raise problem(409,'OCR_TASK_ARTIFACT','任务结果版本不一致')
    return data

def verify_task_binding(s,case_id,initial):
    row=get_task(s,case_id,initial['artifactTaskId'])
    if row.doc['status']!='succeeded' or row.doc['bindings']!=initial['bindings']:
        raise problem(409,'OCR_TASK_BINDING','任务关联不可核对')
    if sha(canonical(initial['candidate']))!=row.doc['artifacts']['candidate']['sha256']:raise problem(409,'OCR_TASK_BINDING','候选结果版本不一致')
    for kind in ('raw','candidate'):
        if sha(checked_artifact(row,kind))!=initial['sourceVersions'][kind]['sha256']:
            raise problem(409,'OCR_TASK_BINDING','任务结果版本不一致')

def execute(runtime,job,image):
    job.mkdir(parents=True,exist_ok=False)
    (job/'page.png').write_bytes(image);(job/'home').mkdir()
    script=Path(__file__).resolve().parents[3]/'tools/image_review/run_public_page6.py'
    env={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':str(job/'home'),'PADDLE_PDX_CACHE_HOME':str(runtime.cache)}
    with (job/'worker.log').open('xb') as log:
        result=subprocess.run([str(runtime.python),str(script),'--model-root',str(runtime.models),'--image',str(job/'page.png'),'--output',str(job/'output')],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120,check=False)
    if result.returncode:raise ValueError('LOCAL_WORKER_EXIT')
    def bounded(name):
        path=job/'output'/name
        if path.stat().st_size>2*1024*1024:raise ValueError('LOCAL_OUTPUT_LIMIT')
        return path.read_bytes()
    raw=bounded('raw.json');meta=json.loads(bounded('run.json'))
    if meta['raw_sha256']!=sha(raw) or meta['image_sha256']!=IMAGE_SHA or meta['mode']!='actual-local-ocr-run':raise ValueError('LOCAL_OUTPUT_VERSION')
    return raw,meta

@router.post('',status_code=201)
async def start(case_id:str,request:Request,ctx:Ctx=CtxDep):
    with ctx.db.session() as s:authorize(ctx,s,case_id,write=True)
    runtime=getattr(request.app.state,'image_ocr_runtime',None)
    if runtime is None:raise problem(503,'OCR_NOT_CONFIGURED','未配置本地执行器；不会自动安装或下载')
    b=await body_bounded(request)
    if not isinstance(b,dict) or set(b)!={'taskId','bindings','confirmed'} or b['confirmed'] is not True or not isinstance(b['taskId'],str) or not re.fullmatch('[a-f0-9]{32}',b['taskId']):
        raise problem(422,'OCR_TASK_INPUT','须提供固定任务号并明确确认归档限制与本地执行')
    if not isinstance(b['bindings'],dict) or set(b['bindings'])!={'pdf','image'}:raise problem(422,'OCR_TASK_INPUT','须提供PDF和页图登记回执')
    task_id=b['taskId'];bindings=b['bindings']
    with WRITE_LOCK,ctx.db.session() as s:
        begin(s);authorize(ctx,s,case_id,write=True)
        if s.get(Task,task_id) is not None:raise problem(409,'OCR_TASK_EXISTS','任务号已存在；只读核查，不重新执行')
        all_tasks=s.scalars(select(Task)).all()
        if any(t.doc['status'] in ('running_or_unknown','interrupted_unknown') for t in all_tasks):raise problem(409,'OCR_TASK_BUSY','已有运行或未知任务；禁止并发或盲重试')
        if sum(t.case_id==case_id for t in all_tasks)>=20:raise problem(409,'OCR_TASK_LIMIT','本候选每案最多20项任务')
        if len(s.scalars(select(Record.id).where(Record.case_id==case_id,Record.revision==0)).all())>=20:raise problem(409,'OCR_BUDGET','核对运行额度已满')
        found=receipts(ctx,s,case_id,bindings)
        if sha(found['pdf'][1])!=PDF_SHA or sha(found['image'][1])!=IMAGE_SHA:raise problem(422,'OCR_PUBLIC_SAMPLE_ONLY','本执行器目前仅支持已核实的公开报告第6页')
        versions={k:{'evidenceId':v[0]['evidenceId'],'sha256':sha(v[1])} for k,v in found.items()}
        image=found['image'][1]
        doc={'taskId':task_id,'caseId':case_id,'bindings':bindings,'status':'running_or_unknown','utc':iso(now_utc()),'operator':ctx.operator,'role':ctx.role,'runId':None,'factVerified':False,'archiveSupported':False}
        s.add(Task(task_id=task_id,case_id=case_id,doc=doc))
        audit.append(s,case_id=case_id,operator=ctx.operator,role=ctx.role,action='ocr.task.start',category='Evidence',command=task_id,entity_id=task_id)
    job=ctx.settings.data_dir/'image-ocr-jobs'/task_id
    try:
        raw,meta=await asyncio.to_thread(execute,runtime,job,image)
        source={'pdf_sha256':PDF_SHA,'image_sha256':IMAGE_SHA,'raw_sha256':sha(raw),'pdf_page_1based':6,'printed_page':'4','mapping_basis':'manual_source_manifest','width':1489,'height':2105}
        rec={**meta['versions'],'pipeline':'PP-OCRv5','models':['PP-OCRv5_mobile_det','PP-OCRv5_mobile_rec'],'device':meta['device']}
        candidate=convert(raw,source,rec);encoded=canonical(candidate)
    except Exception as exc:
        # Only worker/adapter errors BEFORE final commit reach this block. No automatic cleanup/retry.
        with WRITE_LOCK,ctx.db.session() as s:
            begin(s);row=get_task(s,case_id,task_id)
            row.doc={**row.doc,'status':('interrupted_unknown' if isinstance(exc,subprocess.TimeoutExpired) else 'failed'),'errorCode':'LOCAL_OCR_FAILED','message':'本地执行未完成；原件保留，不自动重试','finishedUtc':iso(now_utc())}
            audit.append(s,case_id=case_id,operator=ctx.operator,role=ctx.role,action=('ocr.task.unknown' if isinstance(exc,subprocess.TimeoutExpired) else 'ocr.task.failed'),category='Evidence',command=task_id,entity_id=task_id)
        raise problem(409,'LOCAL_OCR_FAILED','本地任务未完成；请读取任务状态，不自动重试')
    # Failures during authorization/final commit remain unknown, never rewritten as safely retryable.
    with WRITE_LOCK,ctx.db.session() as s:
        begin(s);authorize(ctx,s,case_id,write=True)
        current=receipts(ctx,s,case_id,bindings)
        if any(sha(value[1])!=versions[k]['sha256'] for k,value in current.items()):raise problem(409,'OCR_SOURCE_VERSION','来源版本已变化，不发布结果')
        if len(s.scalars(select(Record.id).where(Record.case_id==case_id,Record.revision==0)).all())>=20:raise problem(409,'OCR_BUDGET','核对运行额度已满，结果待核查')
        row=get_task(s,case_id,task_id)
        if row.doc['status']!='running_or_unknown':raise problem(409,'OCR_TASK_STATE','任务状态不允许发布')
        run_id='OCR-'+task_id
        versions.update({k:{'sha256':sha(v),'kind':'task-artifact'} for k,v in [('raw',raw),('candidate',encoded)]})
        initial={'bindings':bindings,'artifactTaskId':task_id,'candidate':candidate,'sourceVersions':versions,'operator':ctx.operator,'role':ctx.role,'utc':iso(now_utc()),'mode':'local-ocr-task','pageMappingVerified':False,'originalAuthenticityVerified':False}
        s.add(Record(case_id=case_id,run_id=run_id,revision=0,doc=initial))
        row.doc={**row.doc,'status':'succeeded','runId':run_id,'finishedUtc':iso(now_utc()),'runtime':meta,'rawBase64':base64.b64encode(raw).decode(),'candidateBase64':base64.b64encode(encoded).decode(),'artifacts':{k:versions[k] for k in ('raw','candidate')}}
        audit.append(s,case_id=case_id,operator=ctx.operator,role=ctx.role,action='ocr.task.succeeded',category='Evidence',command=task_id,entity_id=run_id)
        result=public_doc(row)
    return result

@router.get('')
def list_tasks(case_id:str,ctx:Ctx=CtxDep):
    with ctx.db.session() as s:
        authorize(ctx,s,case_id)
        rows=s.scalars(select(Task).where(Task.case_id==case_id)).all()
        return [{k:row.doc[k] for k in ('taskId','caseId','status','utc','runId')} for row in rows]

@router.get('/{task_id}')
def status(case_id:str,task_id:str,ctx:Ctx=CtxDep):
    with WRITE_LOCK,ctx.db.session() as s:
        begin(s);authorize(ctx,s,case_id);row=get_task(s,case_id,task_id);receipts(ctx,s,case_id,row.doc['bindings'])
        return public_doc(row)

@router.post('/{task_id}/artifacts/{kind}:download')
async def artifact(case_id:str,task_id:str,kind:str,request:Request,ctx:Ctx=CtxDep):
    with ctx.db.session() as s:authorize(ctx,s,case_id)
    b=await body_bounded(request)
    try:
        if kind not in ('raw','candidate') or set(b)!={'purpose'}:raise ValueError()
        text(b['purpose'],1000)
    except (ValueError,TypeError):raise problem(422,'OCR_ARTIFACT_INPUT','下载目的或结果类型无效')
    with WRITE_LOCK,ctx.db.session() as s:
        begin(s);authorize(ctx,s,case_id);row=get_task(s,case_id,task_id);receipts(ctx,s,case_id,row.doc['bindings'])
        if row.doc['status']!='succeeded':raise problem(409,'OCR_TASK_NOT_READY','任务结果尚未确认')
        data=checked_artifact(row,kind)
        audit.append(s,case_id=case_id,operator=ctx.operator,role=ctx.role,action='ocr.artifact.access',category='Evidence',command=task_id,entity_id=task_id,reason=b['purpose'])
    return Response(data,media_type='application/octet-stream',headers={'X-Sha256':sha(data),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Disposition':f'attachment; filename="ocr-{kind}.json"'})
