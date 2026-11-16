"""Optional local tasks: durable uncertainty, no redispatch or automatic cleanup."""
import asyncio
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
from .app import Storage, Revision, source, sample_source, receipt, strict, inspect_draft
from . import generation
from tools.audio_transcript_contract.sensevoice_candidate import convert


@dataclass(frozen=True)
class LocalRuntime:
    python: Path
    models: Path

class Task(Storage):
    __tablename__='audio_asr_tasks'
    task_id=Column(String,primary_key=True)
    case_id=Column(String,nullable=False,index=True)
    doc=Column(JSON,nullable=False)

router=APIRouter(prefix='/api/v1/cases/{case_id}/audio-asr-tasks',route_class=NoStoreRoute)

def get_task(s,case_id,task_id):
    row=s.get(Task,task_id)
    if row is None or row.case_id!=case_id:raise problem(404,'ASR_TASK_NOT_FOUND','本案未找到任务')
    return row

def public_doc(row):return {k:v for k,v in row.doc.items() if k not in ('raw','candidate')}

def checked_artifact(row,kind):
    raw=canonical(row.doc[kind])
    if sha(raw)!=row.doc['artifacts'][kind]['sha256']:raise problem(409,'ASR_TASK_ARTIFACT','结果版本不一致')
    return raw

def verify_task_binding(s,case_id,initial):
    row=get_task(s,case_id,initial['artifactTaskId'])
    if row.doc['status']!='succeeded' or row.doc['source']!=initial['machineDraft']['source'] or row.doc['audioReceipt']!=initial['audioReceipt']:
        raise problem(409,'ASR_TASK_BINDING','本地任务关联不可核对')
    if checked_artifact(row,'candidate')!=canonical(initial['machineDraft']) or sha(checked_artifact(row,'raw'))!=initial['machineDraft']['recognizerResultSha256']:
        raise problem(409,'ASR_TASK_BINDING','任务与原稿版本不一致')

def execute(runtime,job,audio,task_id):
    job.mkdir(parents=True,exist_ok=False);(job/'source.wav').write_bytes(audio);(job/'home').mkdir()
    worker=Path(__file__).resolve().parents[3]/'tools/audio_transcript_contract/run_sensevoice_task.py'
    env={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':str(job/'home'),'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1'}
    with (job/'worker.log').open('xb') as log:
        r=subprocess.run([str(runtime.python),str(worker),'--model',str(runtime.models),'--audio',str(job/'source.wav'),'--output',str(job/'raw.json'),'--task-id',task_id,'--input-sha256',sha(audio)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120,check=False)
    if r.returncode:raise ValueError('worker exit')
    path=job/'raw.json'
    if path.stat().st_size>262144:raise ValueError('output budget')
    result=strict(path.read_bytes())
    if result['inputSha256']!=sha(audio) or result['taskId']!=task_id or result['modelRevision']!='3847d57b6bdf2dd8875cb1508d2af43d80a16bf7':raise ValueError('worker binding')
    return result

@router.post('',status_code=201)
async def start(case_id:str,request:Request,ctx:Ctx=CtxDep):
    with ctx.db.session() as s:authorize(ctx,s,case_id,write=True)
    runtime=getattr(request.app.state,'audio_asr_runtime',None)
    if runtime is None:raise problem(503,'ASR_NOT_CONFIGURED','未配置本地执行器；不自动安装或下载')
    b=await body_bounded(request)
    if not isinstance(b,dict) or set(b)!={'taskId','audioReceipt','confirmed'} or b['confirmed'] is not True or not isinstance(b['taskId'],str) or not re.fullmatch('[a-f0-9]{32}',b['taskId']):
        raise problem(422,'ASR_TASK_INPUT','须明确确认本地执行与归档限制，提供固定任务号及原音回执')
    task_id=b['taskId']
    with WRITE_LOCK,ctx.db.session() as s:
        begin(s);authorize(ctx,s,case_id,write=True)
        if s.get(Task,task_id) is not None:raise problem(409,'ASR_TASK_EXISTS','任务号已存在；查询状态，不重新执行')
        all_tasks=s.scalars(select(Task)).all()
        if any(t.doc['status'] in ('running_or_unknown','interrupted_unknown') for t in all_tasks):raise problem(409,'ASR_TASK_BUSY','已有运行或未知任务，禁止并发或盲重试')
        if sum(t.case_id==case_id for t in all_tasks)>=20:raise problem(409,'ASR_TASK_LIMIT','每案最多20任务')
        if len(s.scalars(select(Revision.id).where(Revision.case_id==case_id,Revision.revision==0)).all())>=20:raise problem(409,'ASR_RUN_LIMIT','核对运行额度已满')
        snap,fmt=source(ctx,s,case_id,b['audioReceipt']);_,audio=receipt(ctx,s,case_id,b['audioReceipt']);binding=sample_source(snap,fmt)
        if fmt['channels']!=1 or fmt['sampleWidthBytes']!=2 or fmt['sampleRateHz']!=16000 or fmt['frames']>480000 or len(audio)>1048576:
            raise problem(422,'ASR_WAV_SCOPE','本地任务仅支持1–30秒、16kHz单声道16位PCM WAV，最多1MiB；不自动转换原音')
        doc={'taskId':task_id,'caseId':case_id,'audioReceipt':b['audioReceipt'],'source':binding,'status':'running_or_unknown','utc':iso(now_utc()),'operator':ctx.operator,'role':ctx.role,'runId':None,'factVerified':False,'archiveSupported':False}
        s.add(Task(task_id=task_id,case_id=case_id,doc=doc))
        event=audit.append(s,case_id=case_id,operator=ctx.operator,role=ctx.role,action='asr.task.start',category='Evidence',command=task_id,entity_id=task_id)
        generation_id=generation.register(s,case_id,task_id,binding,event)
    try:
        raw=await asyncio.to_thread(execute,runtime,ctx.settings.data_dir/'audio-asr-jobs'/task_id,audio,task_id)
        converted=convert(raw,binding);draft=converted['draft'];encoded=canonical(draft)
    except Exception as exc:
        with WRITE_LOCK,ctx.db.session() as s:
            begin(s);row=get_task(s,case_id,task_id)
            row.doc={**row.doc,'status':'interrupted_unknown' if isinstance(exc,subprocess.TimeoutExpired) else 'failed','errorCode':'LOCAL_ASR_FAILED','message':'本地结果未发布；原音保留，不自动重试','finishedUtc':iso(now_utc())}
            event=audit.append(s,case_id=case_id,operator=ctx.operator,role=ctx.role,action='asr.task.incomplete',category='Evidence',command=task_id,entity_id=task_id)
            generation.observe(s,generation_id,'timeout-observed' if isinstance(exc,subprocess.TimeoutExpired) else 'execution-or-conversion-exception-observed',event)
        raise problem(409,'LOCAL_ASR_FAILED','本地任务未完成，请查询状态，不自动重试')
    # Never classify authorization/final transaction failure as a safely retryable worker failure.
    with WRITE_LOCK,ctx.db.session() as s:
        begin(s);authorize(ctx,s,case_id,write=True);current,current_fmt=source(ctx,s,case_id,b['audioReceipt'])
        if sample_source(current,current_fmt)!=binding:raise problem(409,'ASR_SOURCE_CHANGED','来源版本变化，不发布结果')
        if len(s.scalars(select(Revision.id).where(Revision.case_id==case_id,Revision.revision==0)).all())>=20:raise problem(409,'ASR_RUN_LIMIT','核对运行额度已满，结果待核查')
        row=get_task(s,case_id,task_id)
        if row.doc['status']!='running_or_unknown':raise problem(409,'ASR_TASK_STATE','状态不允许发布')
        run_id='AR-'+task_id
        initial={'audioReceipt':b['audioReceipt'],'artifactTaskId':task_id,'acknowledgeArchiveBlocked':True,'machineDraft':draft,'draftBytesSha256':sha(encoded),'audio':fmt,
                 'machineContractInspection':inspect_draft(draft),'operator':ctx.operator,'role':ctx.role,'utc':iso(now_utc()),'scope':'local-asr-task-pending-human-review'}
        s.add(Revision(case_id=case_id,run_id=run_id,revision=0,doc=initial))
        row.doc={**row.doc,'status':'succeeded','runId':run_id,'finishedUtc':iso(now_utc()),'raw':raw,'candidate':draft,'conversionInspection':converted['inspection'],
                 'artifacts':{'raw':{'sha256':sha(canonical(raw))},'candidate':{'sha256':sha(encoded)}},'asrExecutedByService':True}
        event=audit.append(s,case_id=case_id,operator=ctx.operator,role=ctx.role,action='asr.task.succeeded',category='Evidence',command=task_id,entity_id=run_id)
        generation.observe(s,generation_id,'result-converted-and-source-rechecked',event)
        out=public_doc(row)
    return out

@router.get('')
def listing(case_id:str,ctx:Ctx=CtxDep):
    with ctx.db.session() as s:
        authorize(ctx,s,case_id)
        return [{k:t.doc[k] for k in ('taskId','caseId','status','utc','runId')} for t in s.scalars(select(Task).where(Task.case_id==case_id))]

@router.get('/{task_id}')
def status(case_id:str,task_id:str,ctx:Ctx=CtxDep):
    with WRITE_LOCK,ctx.db.session() as s:
        begin(s);authorize(ctx,s,case_id);row=get_task(s,case_id,task_id);source(ctx,s,case_id,row.doc['audioReceipt']);return public_doc(row)

@router.post('/{task_id}/artifacts/{kind}:download')
async def artifact(case_id:str,task_id:str,kind:str,request:Request,ctx:Ctx=CtxDep):
    with ctx.db.session() as s:authorize(ctx,s,case_id)
    b=await body_bounded(request)
    try:
        if kind not in ('raw','candidate') or not isinstance(b,dict) or set(b)!={'purpose'}:raise ValueError()
        text(b['purpose'],1000)
    except (ValueError,TypeError):raise problem(422,'ASR_ARTIFACT_INPUT','结果种类或目的无效')
    with WRITE_LOCK,ctx.db.session() as s:
        begin(s);authorize(ctx,s,case_id);row=get_task(s,case_id,task_id);source(ctx,s,case_id,row.doc['audioReceipt'])
        if row.doc['status']!='succeeded':raise problem(409,'ASR_NOT_READY','结果尚未确认')
        data=checked_artifact(row,kind)
        audit.append(s,case_id=case_id,operator=ctx.operator,role=ctx.role,action='asr.artifact.access',category='Evidence',command=task_id,entity_id=task_id,reason=b['purpose'])
    return Response(data,media_type='application/json',headers={'X-Sha256':sha(data),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Disposition':f'attachment; filename="asr-{kind}.json"'})
