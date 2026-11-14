"""Test-only fictional Pi transport -> actual working SQLite/RPC. Never a real provider."""
import asyncio,json,tempfile,time,uuid
from pathlib import Path
from mcis_service.config import Settings
from mcis_service.db import Database,put_doc
from mcis_service.identity.demo import prepare,CASE
from mcis_service.identity.local import authorize_read
from mcis_service.interviews.models import InterviewRow
from mcis_service.common import contracts
from mcis_service.investigation.fixture_host import Lines,output
from mcis_service.investigation.http_trial import pairs,invalid
from mcis_service.agents.extraction_review_fixture import document,fixture_content,RECORD
from mcis_service.agents.persistent_extraction_review_host import PersistentExtractionReviewHost
from mcis_service.agents.persistent_extraction_rpc import PersistentExtractionRPC
from mcis_service.agents import extraction_working_store as store,pi_transcript_remote as remote,pi_deepseek_transport as transport
from mcis_service.agents.pi_working_host import PiWorkingHost

def call(cid,name,args):return {'id':cid,'type':'function','function':{'name':name,'arguments':json.dumps(args)}}
def reply(calls):return {'finish_reason':'tool_calls','message':{'role':'assistant','content':None,'tool_calls':calls}}
def request(h):
    h.dispatch({'op':'model_start'});h.dispatch({'op':'model_request'});h.dispatch({'op':'model_end'})
async def run():
    with tempfile.TemporaryDirectory(prefix='mcis-pi-ui-fixture-') as directory:
        root=Path(directory);settings=Settings(data_dir=root,db_url=f'sqlite:///{root/"test.db"}',seed_demo=False,core_cmd='unused',host='127.0.0.1',port=0)
        settings.blob_dir.mkdir(parents=True);db=Database(settings.resolved_db_url)
        try:
            db.create_all();store.initialize(db);token=await prepare(db,settings);doc=document();contracts.validate('interview',doc)
            with db.session() as s:
                subject=authorize_read(s,token,CASE).subject_id;put_doc(s,InterviewRow,CASE,RECORD,doc);store.grant(s,subject,CASE,enabled=True)
            args=(db,settings,token,CASE,RECORD);cfg=transport.DeepSeekConfig('fictional-key-never-network');content=fixture_content()
            query=json.loads(content)['statements'][0]['quote']
            outputs=[reply([call('read','find_transcript_passages',{'query':query})]),reply([call('validate','validate_extraction_proposal',{'content':content})]),{'finish_reason':'stop','message':{'role':'assistant','content':remote.COMPLETION_MARKER}}]
            original=transport.complete
            transport.complete=lambda *a,**kw:outputs.pop(0)
            h=PiWorkingHost(*args,cfg,approved_disclosure_digest=remote.describe_remote(*args,cfg,completion_mode='validated-reference')['approvalDigest'],completion_mode='validated-reference')
            try:
                request(h);h.dispatch({'op':'tool','name':'find_transcript_passages','args':{'query':query},'callId':'read'})
                request(h);h.dispatch({'op':'tool','name':'validate_extraction_proposal','args':{'content':content},'callId':'validate'})
                request(h);h.dispatch({'op':'final','payload':remote.COMPLETION_MARKER});saved=h.save(str(uuid.uuid4()))
            finally:h.close();transport.complete=original
            decisions=[{'index':i,'decision':'needs_verification','note':'自动化测试脚本记录，不是调查员审核。'} for i in range(1,len(saved['proposal']['result']['proposals'])+1)]
            store.append_review(*args[:4],saved['proposalId'],str(uuid.uuid4()),0,decisions,review_origin='scripted_test')
            host=PersistentExtractionReviewHost(db=db,settings=settings,session_token=token,case_id=CASE,record_id=RECORD,provider=None)
            async with PersistentExtractionRPC(host) as rpc:
                output({**rpc.scope,'fixture':'mock-pi-provider-not-real-model','storage':'temporary-sqlite','proposalId':saved['proposalId']})
                lines=Lines();deadline=time.monotonic()+90
                for _ in range(32):
                    raw=lines.read(min(deadline,time.monotonic()+15))
                    if raw is None:return
                    output(await rpc.dispatch(json.loads(raw.decode(),object_pairs_hook=pairs,parse_constant=invalid)))
        finally:db.engine.dispose()
if __name__=='__main__':asyncio.run(run())
