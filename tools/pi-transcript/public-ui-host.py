"""Test-only explicit public Pi -> review/archive stdio broker. Never a server.

--approved-public-ui requires separately authorized public report/provider use.
--fixture mocks transport explicitly and never reads a key or calls the network.
No fallback. No model-accessible write tools. No key in files/environment/output.
"""
import asyncio
import json
import os
from pathlib import Path
import select
import sys
import tempfile
import time
import uuid

from mcis_service.config import Settings
from mcis_service.db import Database,put_doc
from mcis_service.identity.demo import prepare,CASE
from mcis_service.identity.local import authorize_read
from mcis_service.interviews.models import InterviewRow
from mcis_service.common import contracts
from mcis_service.investigation.http_trial import pairs,invalid
from mcis_service.agents import extraction_working_store as store,working_history_archive as archive,pi_deepseek_transport as transport
from mcis_service.agents.pi_remote_public_probe import public_document,EXCERPT_SHA,RECORD
from mcis_service.agents.deepseek_client import DeepSeekConfig,validate_config
from mcis_service.agents.pi_transcript_remote import describe_remote,COMPLETION_MARKER
from mcis_service.agents.pi_working_host import PiWorkingHost
from mcis_service.agents.persistent_extraction_review_host import PersistentExtractionReviewHost
from mcis_service.agents.persistent_extraction_rpc import PersistentExtractionRPC
from mcis_service.agents.working_archive_rpc import WorkingArchiveRPC

LIMIT=12*1024*1024
TOTAL_LIMIT=64*1024*1024
SOURCE='https://www.sh.msa.gov.cn/sgdc/104170.jhtml'

class Lines:
    def __init__(self):self.pending=b'';self.total=0
    def read(self,deadline,maximum=LIMIT):
        if time.monotonic()>=deadline:raise TimeoutError()
        while b'\n' not in self.pending:
            wait=deadline-time.monotonic()
            if wait<=0 or not select.select([sys.stdin.fileno()],[],[],wait)[0]:raise TimeoutError()
            chunk=os.read(sys.stdin.fileno(),65536)
            if not chunk:
                if self.pending:raise ValueError()
                return None
            self.total+=len(chunk)
            if self.total>TOTAL_LIMIT:raise ValueError()
            self.pending+=chunk
            if len(self.pending.split(b'\n',1)[0])>maximum:raise ValueError()
        line,self.pending=self.pending.split(b'\n',1)
        if len(line)>maximum:raise ValueError()
        if time.monotonic()>=deadline:raise TimeoutError()
        return line

def output(value):
    raw=json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
    if len(raw)>LIMIT:raise ValueError()
    sys.stdout.buffer.write(raw+b'\n');sys.stdout.buffer.flush()

def parse(raw):
    if raw is None:raise EOFError()
    return json.loads(raw.decode(),object_pairs_hook=pairs,parse_constant=invalid)

def fixture_transport():
    """Fixed public excerpt and mocked provider. Adapter labels are not live proof."""
    quote='事故未造成人员伤亡'
    content=json.dumps({'statements':[{'kind':'Observation','subject':'reported.casualties',
        'summary':'模拟模型读取公开报告：报告称无人员伤亡，待调查员核实。',
        'claim':{'valueType':'Occurrence','occurred':False},'round':1,'field':'Answer','quote':quote}]},ensure_ascii=False)
    def tool(cid,name,args):return {'id':cid,'type':'function','function':{'name':name,'arguments':json.dumps(args,ensure_ascii=False)}}
    calls=[tool('fixture-read','read_transcript_excerpt',{'round':1,'field':'Answer','start':0,'length':4000}),tool('fixture-validate','validate_extraction_proposal',{'content':content})]
    responses=[{'finish_reason':'tool_calls','message':{'role':'assistant','content':None,'tool_calls':[c]}} for c in calls]
    responses.append({'finish_reason':'stop','message':{'role':'assistant','content':COMPLETION_MARKER}})
    def complete(cfg,messages,*,deadline):
        if not responses:raise ValueError('fixture exhausted')
        return responses.pop(0)
    return complete

async def run(fixture=False):
    lines=Lines();deadline=time.monotonic()+300
    def emit(value):
        if time.monotonic()>=deadline:raise TimeoutError()
        output(value)
    if fixture:cfg=validate_config(DeepSeekConfig('fixture-not-a-credential','deepseek-v4-pro'))
    else:
        supplied=parse(lines.read(min(deadline,time.monotonic()+30),8192))
        if type(supplied) is not dict or set(supplied)!={'apiKey'}:raise ValueError()
        cfg=validate_config(DeepSeekConfig(supplied['apiKey'],'deepseek-v4-pro'));del supplied
    original_transport=transport.complete
    if fixture:transport.complete=fixture_transport()
    closed=False
    try:
        with tempfile.TemporaryDirectory(prefix='mcis-public-pi-ui-') as directory:
            root=Path(directory)
            settings=Settings(data_dir=root,db_url=f'sqlite:///{root/"trial.db"}',seed_demo=False,core_cmd='unused',host='127.0.0.1',port=0)
            settings.blob_dir.mkdir(parents=True)
            db=Database(settings.resolved_db_url);pi=review=arch=None
            try:
                db.create_all();store.initialize(db);archive.initialize(db);token=await prepare(db,settings)
                doc=public_document();contracts.validate('interview',doc)
                with db.session() as session:
                    subject=authorize_read(session,token,CASE).subject_id
                    put_doc(session,InterviewRow,CASE,RECORD,doc)
                    store.grant(session,subject,CASE,enabled=True)
                    archive.grant(session,subject,CASE,can_import=True,can_read=True)
                args=(db,settings,token,CASE,RECORD)
                disclosure=describe_remote(*args,cfg,completion_mode='validated-reference')
                pi=PiWorkingHost(*args,cfg,approved_disclosure_digest=disclosure['approvalDigest'],completion_mode='validated-reference')
                host=PersistentExtractionReviewHost(db=db,settings=settings,session_token=token,case_id=CASE,record_id=RECORD,review_origin='scripted_test')
                review=PersistentExtractionRPC(host)
                arch=WorkingArchiveRPC(db=db,settings=settings,session_token=token,case_id=CASE)
                del token,args,disclosure,doc
                emit({'ready':True,'mode':'fixture' if fixture else 'remote-deepseek','fixture':fixture,'remoteProviderSelected':not fixture,'inferencePerformed':False,'transportMocked':fixture,
                    'configuredModel':cfg.model,'completionMode':'validated-reference','excerptSha256':EXCERPT_SHA,
                    'source':SOURCE,'inputMeaning':'public-report-excerpt-not-witness-interview',
                    'reviewScope':review.scope,'archiveScope':arch.scope,'storage':'temporary_sqlite_until_explicit_close'})
                del cfg
                ui_ready=False;last_export=None;pi_commands=0
                for _ in range(96):
                    value=parse(lines.read(min(deadline,time.monotonic()+30)))
                    if time.monotonic()>=deadline:raise TimeoutError()
                    if type(value) is not dict:raise ValueError()
                    if value=={'channel':'close'}:
                        closed=True;break
                    if not ui_ready:
                        if 'channel' in value or pi_commands>=32:raise ValueError()
                        pi_commands+=1
                        result=await asyncio.to_thread(pi.dispatch,value)
                        if value.get('op')=='final':
                            saved=await asyncio.to_thread(pi.save,str(uuid.uuid4()))
                            result={**result,'workingReady':{'proposalId':saved['proposalId'],'recordId':saved['recordId'],
                                'proposals':len(result['proposals']),'citations':len(result['citations']),
                                'saved':True,'factActivated':False,'reviewOrigin':'scripted_test'}}
                            ui_ready=True;pi.close()
                        emit(result)
                    else:
                        if set(value)!={'channel','request'} or value['channel'] not in ('review','archive') or type(value['request']) is not dict:raise ValueError()
                        request=value['request']
                        if value['channel']=='review':
                            if request.get('action') not in ('list','read','review'):raise ValueError()
                            result=await review.dispatch(request)
                        else:
                            if request.get('action')=='import' and (last_export is None or request.get('bundleBase64')!=last_export):raise ValueError()
                            result=await arch.dispatch(request)
                            if request.get('action')=='export':
                                last_export=result['body']['bundleBase64'] if result.get('ok') is True else None
                        emit(result)
                if not closed:raise TimeoutError()
            finally:
                if pi is not None:pi.close()
                if review is not None:review.close()
                if arch is not None:arch.close()
                db.engine.dispose()
        # Success acknowledgement is only emitted after normal directory removal.
        emit({'closed':True,'cleanupConfirmed':True,'temporaryStorageRemoved':True})
    finally:
        transport.complete=original_transport

def main():
    if sys.argv[1:] not in (['--approved-public-ui'],['--fixture']):return 2
    try:asyncio.run(run(sys.argv[1:]==['--fixture']));return 0
    except (Exception,KeyboardInterrupt):
        output({'ok':False,'errorCode':'PUBLIC_UI_HOST_STOPPED'});return 2
if __name__=='__main__':raise SystemExit(main())
