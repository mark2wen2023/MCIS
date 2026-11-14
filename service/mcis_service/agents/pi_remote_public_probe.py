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

async def run():
    lines=Lines()
    raw=lines.read(time.monotonic()+30)
    if raw is None:raise ValueError()
    supplied=json.loads(raw.decode(),object_pairs_hook=pairs,parse_constant=invalid)
    if type(supplied) is not dict or set(supplied)!={'apiKey'}:raise ValueError()
    cfg=validate_config(DeepSeekConfig(supplied['apiKey'],'deepseek-v4-pro'))
    del supplied,raw
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
            host=RemoteTranscriptHost(*args,cfg,approved_disclosure_digest=disclosure['approvalDigest'])
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
                    output(await asyncio.to_thread(host.dispatch,value))
                except Exception as exc:
                    output(safe_error(exc))
                    raise
                if value.get('op')=='final':return
        finally:
            if host is not None:host.close()
            db.engine.dispose()

def main():
    if sys.argv[1:]!=['--approved-public-report']:return 2
    try:
        asyncio.run(run());return 0
    except (Exception,KeyboardInterrupt):
        print('Public Pi probe stopped without a confirmed result.',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
