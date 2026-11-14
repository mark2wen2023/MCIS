"""Explicit trusted CLI for a fixed public-report Pi probe, never production auth.

Only run after the user authorized this exact public report/DeepSeek task. The
--approved-public-report flag is the trusted caller's assertion, not verified
human consent. Secret arrives once through stdin, never command argv or files.
"""
import asyncio
import hashlib
import json
import sys
import tempfile
import time
import uuid
from pathlib import Path
from fastapi import HTTPException
from ..config import Settings, PROJECT_ROOT
from ..db import Database, put_doc
from ..identity.demo import prepare, CASE
from ..interviews.models import InterviewRow
from ..common import contracts
from ..investigation.fixture_host import Lines, output
from ..investigation.http_trial import pairs, invalid
from .extraction_review_fixture import document, RECORD
from .deepseek_client import DeepSeekConfig, validate_config
from .pi_transcript_remote import RemoteTranscriptHost, describe_remote
from .pi_working_host import PiWorkingHost
from . import extraction_working_store as working
from ..identity import local

EXCERPT='事故导致“YANGZE 22”轮右舷船中部位船体\n破损，第 5 号货舱进水，1 号右燃油舱内共计约 171.053 吨\n燃油泄漏；“VEGA DREAM”轮球鼻艏及球鼻艏上方船壳破\n损，首尖舱进水。事故未造成人员伤亡，构成较大等级水上\n交通事故。'
TEXT_SHA='bca8f8b8ba04a5d0669a121bc6c9380c8cd6f8397f67be2d0b30b38871c22ef2'
EXCERPT_SHA='c158ad790b5605dc4eea9303f9dc3748bb9f5ce07b969fd10f30cee9d6c45748'

def public_document():
    raw=(PROJECT_ROOT/'reports/yangze22/report.txt').read_bytes()
    text=raw.decode('utf-8')
    if hashlib.sha256(raw).hexdigest()!=TEXT_SHA or text.count(EXCERPT)!=1 or text.find(EXCERPT)!=5987 or hashlib.sha256(EXCERPT.encode()).hexdigest()!=EXCERPT_SHA:
        raise ValueError()
    doc=document()
    doc['interviewee']={'intervieweeId':'PUBLIC-REPORT-ADAPTER','name':'公开报告摘录（非证人笔录）','role':'公开事故报告','affiliation':'公开资料'}
    doc['turns']=[{'round':1,'question':'以下是公开事故调查报告原文节选，不是证人笔录。仅提取报告声称的损害和数量，保留约等不确定性。','answer':EXCERPT,'sensitiveFragments':[]}]
    return doc

SAFE_CODES = frozenset({
    'PI_BINDING_INVALID','PI_RUN_CLOSED','PI_SOURCE_CHANGED','PI_MODEL_BUDGET',
    'PI_MODEL_STATE','PI_TOOL_BUDGET','PI_TOOL_INVALID','PI_PROTOCOL_INVALID',
    'PI_REMOTE_APPROVAL_REQUIRED','PI_REMOTE_SCOPE_CHANGED','PI_REMOTE_PROTOCOL_INVALID',
    'PI_DEEPSEEK_INPUT_INVALID','PI_DEEPSEEK_HTTP_ERROR','PI_DEEPSEEK_TIMEOUT',
    'PI_DEEPSEEK_UNAVAILABLE','PI_DEEPSEEK_OUTPUT_INVALID',
    'MODEL_OUTPUT_INVALID','INVALID_CITATION','DUPLICATE_CITATION','SOURCE_CHANGED',
})

def safe_error(exc):
    code = exc.detail.get('code') if isinstance(exc,HTTPException) and type(exc.detail) is dict else None
    return {'ok':False,'errorCode':code if code in SAFE_CODES else 'PI_HOST_REJECTED'}

def working_acceptance(host,args,accepted):
    """Fixed scripted review rehearsal, explicitly NOT a human judgment."""
    db,settings,token,case,record=args
    operation=str(uuid.uuid4())
    saved=host.save(operation);pid=saved['proposalId']
    replay=host.save(operation)
    if not replay['replayed'] or replay['proposalId']!=pid:raise ValueError()
    if saved['factActivated'] or not saved['saved'] or saved['recordId']!=record:raise ValueError()
    original=saved['proposal']['result']
    if original['proposals']!=accepted['proposals'] or original['citations']!=accepted['citations']:raise ValueError()
    host.close();db.engine.dispose()
    reopened=Database(settings.resolved_db_url)
    try:
        before=working.read(reopened,settings,token,case,pid)
        if before['revision']!=0 or before['proposal']['result']!=original:raise ValueError()
        decisions=[{'index':i,'decision':'needs_verification','note':'自动化验收脚本：待调查员核实；非人工判断或事实确认。'} for i in range(1,len(original['proposals'])+1)]
        reviewed=working.append_review(reopened,settings,token,case,pid,str(uuid.uuid4()),0,decisions)
        if reviewed['revision']!=1 or reviewed['factActivated']:raise ValueError()
    finally:reopened.engine.dispose()
    reopened=Database(settings.resolved_db_url)
    try:
        final=working.read(reopened,settings,token,case,pid)
        if final['revision']!=1 or final['proposal']['result']!=original or final['reviews'][0]['decisions']!=decisions:raise ValueError()
    finally:reopened.engine.dispose()
    return {'workingSaved':True,'reopenedRead':True,'reviewRevision':1,'reviewActor':'scripted_test_not_human',
        'factActivated':False,'persistentDuringProbe':True,'storage':'temporary_sqlite_deleted_after_probe'}

async def run(working_mode=False):
    lines=Lines()
    raw=lines.read(time.monotonic()+30)
    if raw is None:raise ValueError()
    supplied=json.loads(raw.decode(),object_pairs_hook=pairs,parse_constant=invalid)
    if type(supplied) is not dict or set(supplied)!={'apiKey'}:raise ValueError()
    cfg=validate_config(DeepSeekConfig(supplied['apiKey'],'deepseek-v4-pro'))
    del supplied,raw
    final_result=None
    with tempfile.TemporaryDirectory(prefix='mcis-pi-public-probe-') as directory:
        root=Path(directory)
        settings=Settings(data_dir=root,db_url=f'sqlite:///{root/"probe.db"}',seed_demo=False,core_cmd='unused',host='127.0.0.1',port=0)
        settings.blob_dir.mkdir(parents=True)
        db=Database(settings.resolved_db_url);host=None
        try:
            db.create_all();token=await prepare(db,settings)
            doc=public_document();contracts.validate('interview',doc)
            with db.session() as s:put_doc(s,InterviewRow,CASE,RECORD,doc)
            args=(db,settings,token,CASE,RECORD)
            disclosure=describe_remote(*args,cfg)
            # Caller explicitly selected this fixed public scope. This is not a
            # browser consent receipt or permission for arbitrary future cases.
            if working_mode:
                working.initialize(db)
                with db.session() as s:working.grant(s,local.authorize_read(s,token,CASE).subject_id,CASE,enabled=True)
                host=PiWorkingHost(*args,cfg,approved_disclosure_digest=disclosure['approvalDigest'])
            else:host=RemoteTranscriptHost(*args,cfg,approved_disclosure_digest=disclosure['approvalDigest'])
            probe_args=args
            del token,args
            output({'ready':True,'fixture':False,'configuredModel':cfg.model,
                    'inputMeaning':'public-report-excerpt-not-witness-interview',
                    'source':'https://www.sh.msa.gov.cn/sgdc/104170.jhtml',
                    'pdf':'https://www.sh.msa.gov.cn/u/cms/www/202505/191445221747637122775.pdf',
                    'printedPage':1,'pdfPage':3,'excerptSha256':EXCERPT_SHA,
                    'sourceTextSha256':TEXT_SHA,'sourceCharacterStart':5987,
                    'disclosure':disclosure,'humanApprovalVerified':False,
                    'storage':'temporary-fixture-identity-no-production-login'})
            deadline=time.monotonic()+120
            for _ in range(32):
                raw=lines.read(min(deadline,time.monotonic()+30))
                if raw is None:return
                value=json.loads(raw.decode(),object_pairs_hook=pairs,parse_constant=invalid)
                try:
                    result=await asyncio.to_thread(host.dispatch,value)
                    if working_mode and value.get('op')=='final':
                        result={**result,'workingAcceptance':await asyncio.to_thread(working_acceptance,host,probe_args,result)}
                    if value.get('op')=='final':
                        final_result=result
                        break
                    output(result)
                except Exception as exc:
                    output(safe_error(exc))
                    raise
        finally:
            if host is not None:host.close()
            db.engine.dispose()
    # Emit success only after host/database close and normal temporary cleanup.
    if final_result is not None:output(final_result)

def main():
    if sys.argv[1:] not in (['--approved-public-report'],['--approved-public-report-working']):return 2
    try:
        asyncio.run(run(sys.argv[1:] == ['--approved-public-report-working']));return 0
    except (Exception,KeyboardInterrupt):
        print('Public Pi probe stopped without a confirmed result.',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
