"""Preserve registered PCM audio, machine drafts and append-only human revisions."""
import io
import json
from pathlib import Path
from uuid import uuid4
import wave
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import Column, Integer, String, JSON, UniqueConstraint, select, text as sql
from sqlalchemy.orm import DeclarativeBase
from tools.audio_transcript_contract.machine_contract import validate as validate_v2, inspect as inspect_v2
from tools.audio_transcript_contract.sample_machine_contract import validate as validate_v3, inspect as inspect_v3
from ..common.context import Ctx, CtxDep, problem
from ..common.timeutil import iso, now_utc
from ..db import WRITE_LOCK
from ..reports.access import begin, NoStoreRoute
from ..evidence_intake.router import authorize, body_bounded, load_receipt
from ..evidence_intake.parser import DIGEST, sha, canonical, text
from ..audit import service as audit

class Storage(DeclarativeBase):pass
class Revision(Storage):
    __tablename__='audio_review_revisions'
    id=Column(Integer,primary_key=True)
    case_id=Column(String,nullable=False,index=True)
    run_id=Column(String,nullable=False)
    revision=Column(Integer,nullable=False)
    doc=Column(JSON,nullable=False)
    __table_args__=(UniqueConstraint('case_id','run_id','revision'),)

router=APIRouter(prefix='/api/v1/cases/{case_id}/audio-reviews',route_class=NoStoreRoute)

def receipt(ctx,s,case_id,digest):
    if not isinstance(digest,str) or not DIGEST.fullmatch(digest):raise problem(422,'AUDIO_RECEIPT','登记回执无效')
    found=load_receipt(ctx,s,case_id,digest)
    if found is None:raise problem(409,'AUDIO_SOURCE_UNAVAILABLE','须先登记同案文件')
    return found

def source(ctx,s,case_id,digest):
    r,raw=receipt(ctx,s,case_id,digest)
    try:
        with wave.open(io.BytesIO(raw),'rb') as w:
            channels,width,rate,frames=w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes()
            if w.getcomptype()!='NONE' or channels not in (1,2) or width not in (1,2,3,4) or not 8000<=rate<=48000 or not rate<=frames<=rate*60:
                raise ValueError('bounded PCM required')
            if len(w.readframes(frames))!=frames*channels*width:raise ValueError('truncated PCM')
    except (wave.Error,EOFError,ValueError):raise problem(422,'AUDIO_FORMAT','本候选仅支持1至60秒的完整PCM WAV，8000–48000Hz单/双声道')
    actual=sha(raw)
    if actual!=r['sourceSha256'] or actual!=r['evidence']['currentSha256']:raise problem(409,'AUDIO_VERSION','实际字节与登记版本不一致')
    state={'caseId':case_id,'evidenceId':r['evidenceId'],'requestDigest':digest,'registeredSha256':r['sourceSha256'],'currentSha256':actual}
    return {'caseId':case_id,'evidenceId':r['evidenceId'],'registeredSha256':r['sourceSha256'],'currentSha256':actual,
            'stateDigest':sha(canonical(state)),'durationMs':(frames*1000+rate-1)//rate,'trackIndex':0}, {'channels':channels,'sampleWidthBytes':width,'sampleRateHz':rate,'frames':frames,'format':'PCM_WAV'}

def sample_source(snapshot, audio):
    return {**snapshot, 'frameCount':audio['frames'], 'sampleRateHz':audio['sampleRateHz']}

def matched_source(draft, snapshot, audio):
    if draft['version'] == 3:
        return draft['source'] == sample_source(snapshot, audio)
    return audio['frames']*1000 % audio['sampleRateHz'] == 0 and draft['source'] == snapshot

def validate(document):
    return validate_v3(document) if isinstance(document,dict) and document.get('version') == 3 else validate_v2(document)

def inspect_draft(document):
    return inspect_v3(document) if document['version'] == 3 else inspect_v2(document)

def rows(s,case_id,run_id):
    result=s.scalars(select(Revision).where(Revision.case_id==case_id,Revision.run_id==run_id).order_by(Revision.revision)).all()
    if not result:raise problem(404,'AUDIO_REVIEW_NOT_FOUND','本案未找到核对记录')
    return result

def check(ctx,s,case_id,initial):
    current,fmt=source(ctx,s,case_id,initial['audioReceipt'])
    if not matched_source(initial['machineDraft'],current,fmt):raise problem(409,'AUDIO_SOURCE_STALE','原音版本不符，保留原稿，不静默重绑定')
    if 'artifactTaskId' in initial:
        from .tasks import verify_task_binding
        verify_task_binding(s,case_id,initial)
        return
    _,raw=receipt(ctx,s,case_id,initial['draftReceipt'])
    if sha(raw)!=initial['draftBytesSha256']:raise problem(409,'AUDIO_DRAFT_STALE','机器原稿版本不符')

def result(rs):
    return {'caseId':rs[0].case_id,'runId':rs[0].run_id,'revision':rs[-1].revision,'initial':rs[0].doc,
            'humanRevisions':[r.doc for r in rs[1:]],'asrExecutedByService':'artifactTaskId' in rs[0].doc,'factVerified':False,'archiveSupported':False}

def strict(raw):
    if len(raw)>262144:raise ValueError('draft budget')
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d:raise ValueError('duplicate')
            d[k]=v
        return d
    return json.loads(raw.decode('utf-8'),object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('number')))

@router.get('/source/{digest}')
def source_context(case_id:str,digest:str,ctx:Ctx=CtxDep):
    with WRITE_LOCK,ctx.db.session() as s:
        begin(s);authorize(ctx,s,case_id)
        snap,fmt=source(ctx,s,case_id,digest)
        return {'source':snap if fmt['frames']*1000%fmt['sampleRateHz']==0 else None,'sampleSource':sample_source(snap,fmt),'audio':fmt,'scope':'registered-byte-binding-only','humanListened':False,'authenticityVerified':False}

@router.post('',status_code=201)
async def attach(case_id:str,request:Request,ctx:Ctx=CtxDep):
    with ctx.db.session() as s:authorize(ctx,s,case_id,write=True)
    b=await body_bounded(request)
    if not isinstance(b,dict) or set(b)!={'audioReceipt','draftReceipt','acknowledgeArchiveBlocked'} or b['acknowledgeArchiveBlocked'] is not True:
        raise problem(422,'AUDIO_INPUT','须明确确认归档限制，并提供原音与机器原稿登记')
    with WRITE_LOCK,ctx.db.session() as s:
        begin(s);authorize(ctx,s,case_id,write=True)
        snap,fmt=source(ctx,s,case_id,b['audioReceipt']);_,raw=receipt(ctx,s,case_id,b['draftReceipt'])
        try:draft=validate(strict(raw))
        except (ValueError,TypeError,KeyError,UnicodeError,RecursionError):raise problem(422,'AUDIO_MACHINE_DRAFT','不是有效v2/v3机器待核对草稿')
        if not matched_source(draft,snap,fmt):raise problem(409,'AUDIO_SOURCE_STALE','草稿来源与本次登记字节绑定不一致')
        if draft['transcript']['revision']!=1:raise problem(422,'AUDIO_HISTORY_UNSUPPORTED','尚不接收缺少父链的旧版本机器草稿')
        if len(s.scalars(select(Revision.id).where(Revision.case_id==case_id,Revision.revision==0)).all())>=20:raise problem(409,'AUDIO_LIMIT','每案最多20个核对运行')
        run_id='AR-'+uuid4().hex
        doc={**b,'machineDraft':draft,'draftBytesSha256':sha(raw),'audio':fmt,'machineContractInspection':inspect_draft(draft),
             'operator':ctx.operator,'role':ctx.role,'utc':iso(now_utc()),'scope':'manual-review-candidate-not-approved-transcript'}
        s.add(Revision(case_id=case_id,run_id=run_id,revision=0,doc=doc));s.flush()
        audit.append(s,case_id=case_id,operator=ctx.operator,role=ctx.role,action='audio.draft.attach',category='Evidence',command=run_id,entity_id=run_id)
        out=result(rows(s,case_id,run_id))
    return out

@router.get('')
def listing(case_id:str,ctx:Ctx=CtxDep):
    with ctx.db.session() as s:
        authorize(ctx,s,case_id)
        return [{'caseId':case_id,'runId':r.run_id,'utc':r.doc['utc'],'sourceCheck':'not-performed-by-list'} for r in s.scalars(select(Revision).where(Revision.case_id==case_id,Revision.revision==0))]

@router.get('/{run_id}')
def get(case_id:str,run_id:str,ctx:Ctx=CtxDep):
    with WRITE_LOCK,ctx.db.session() as s:
        begin(s);authorize(ctx,s,case_id);rs=rows(s,case_id,run_id);check(ctx,s,case_id,rs[0].doc);return result(rs)

@router.post('/{run_id}/revisions')
async def revise(case_id:str,run_id:str,request:Request,ctx:Ctx=CtxDep):
    with ctx.db.session() as s:authorize(ctx,s,case_id,write=True)
    b=await body_bounded(request)
    try:
        if not isinstance(b,dict) or set(b)!={'expectedRevision','segmentId','text','hearingStatus','startMs','endMs','reason'}:raise ValueError()
        if type(b['expectedRevision']) is not int or b['expectedRevision']<0:raise ValueError()
        text(b['segmentId'],200);text(b['text'],16000,empty=True);text(b['reason'],2000)
        if b['hearingStatus'] not in ('pending','transcription_checked','unintelligible'):raise ValueError()
        if b['hearingStatus']=='unintelligible' and b['text']!='':raise ValueError('do not invent text for unintelligible')
    except (ValueError,TypeError):raise problem(422,'AUDIO_REVISION_INPUT','核对输入无效；听不清须保留空文字')
    with WRITE_LOCK,ctx.db.session() as s:
        begin(s);authorize(ctx,s,case_id,write=True);rs=rows(s,case_id,run_id);initial=rs[0].doc;check(ctx,s,case_id,initial)
        if rs[-1].revision!=b['expectedRevision']:raise problem(412,'AUDIO_REVISION_STALE','有新修订；保留输入并重新核对，不自动重试')
        transcript=initial['machineDraft']['transcript'];segments=transcript['segments']+transcript['unlocatedSegments']
        if b['segmentId'] not in {r['id'] for r in segments}:raise problem(422,'AUDIO_SEGMENT','片段不存在')
        duration=initial['machineDraft']['source']['durationMs'];start,end=b['startMs'],b['endMs']
        if not (start is None and end is None) and not (type(start)is int and type(end)is int and 0<=start<end<=duration and end*initial['audio']['sampleRateHz']<=initial['audio']['frames']*1000):raise problem(422,'AUDIO_TIME','保留双空未知，或提供原音范围内的相对毫秒')
        if rs[-1].revision>=1000:raise problem(409,'AUDIO_LIMIT','最多1000次修订')
        n=rs[-1].revision+1
        doc={**b,'revision':n,'timeStatus':'unknown' if start is None else 'operator_declared','speaker':{'status':'unknown','id':None},
             'machineArtifactSha256':initial['machineDraft']['artifactSha256'],'audioSha256':initial['machineDraft']['source']['currentSha256'],
             'operator':ctx.operator,'role':ctx.role,'utc':iso(now_utc()),'factVerified':False}
        s.add(Revision(case_id=case_id,run_id=run_id,revision=n,doc=doc));s.flush()
        audit.append(s,case_id=case_id,operator=ctx.operator,role=ctx.role,action='audio.human.revise',category='Evidence',command=run_id,entity_id=run_id,after={'revision':n,'segmentId':b['segmentId']})
        out=result(rows(s,case_id,run_id))
    return out

def register_audio_review(app, *, sensevoice_runtime=None):
    """Register the isolated module once on an existing application."""
    if getattr(app.state, 'audio_review_registered', False):
        raise ValueError('audio review already registered')
    from . import tasks
    app.state.audio_asr_runtime=sensevoice_runtime
    Storage.metadata.create_all(app.state.db.engine)
    with app.state.db.engine.begin() as c:
        for op in ('UPDATE','DELETE'):
            c.execute(sql(f"CREATE TRIGGER IF NOT EXISTS audio_review_no_{op.lower()} BEFORE {op} ON audio_review_revisions BEGIN SELECT RAISE(ABORT,'append-only audio review'); END;"))
    app.include_router(router);app.include_router(tasks.router)
    @app.get('/audio-review-lab',response_class=HTMLResponse)
    def page():return HTMLResponse(Path(__file__).with_name('review.html').read_text(),headers={'Cache-Control':'no-store'})
    app.state.audio_review_registered = True
    return app


def create_audio_review_app(settings, *, sensevoice_runtime=None):
    from ..main import create_app
    return register_audio_review(create_app(settings), sensevoice_runtime=sensevoice_runtime)
