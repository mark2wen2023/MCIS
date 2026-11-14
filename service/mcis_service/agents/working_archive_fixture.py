"""Fictional seeded per-process demo; bounded explicit archive bytes are accepted.
Use synthetic packages only. No cross-process retention.
"""
import asyncio,json,sys,tempfile,time,uuid,os,select
from pathlib import Path
from ..config import Settings
from ..db import Database,put_doc
from ..identity.demo import prepare,CASE
from ..identity.local import authorize_read
from ..interviews.models import InterviewRow
from ..common import contracts

from ..investigation.http_trial import pairs,invalid
from .extraction_review_fixture import document,fixture_content,RECORD
from .host_extraction import FixtureProvider
from .persistent_extraction_review_host import PersistentExtractionReviewHost
from .working_archive_rpc import WorkingArchiveRPC,RPC_LIMIT
from . import working_history_archive as archive
from . import extraction_working_store as store

class Lines:
    def __init__(self):self.pending=b''
    def read(self,deadline):
        while b'\n' not in self.pending:
            remaining=deadline-time.monotonic()
            if remaining<=0 or not select.select([sys.stdin.fileno()],[],[],remaining)[0]:raise TimeoutError()
            chunk=os.read(sys.stdin.fileno(),65536)
            if not chunk:
                if self.pending:raise ValueError()
                return None
            self.pending+=chunk
            if len(self.pending.split(b'\n',1)[0])>RPC_LIMIT:raise ValueError()
        line,self.pending=self.pending.split(b'\n',1)
        if len(line)>RPC_LIMIT:raise ValueError()
        return line

def output(value):
    raw=json.dumps(value,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    if len(raw)>RPC_LIMIT:raise ValueError()
    sys.stdout.buffer.write(raw+b'\n');sys.stdout.buffer.flush()

async def run():
    with tempfile.TemporaryDirectory(prefix='mcis-persistent-working-demo-') as directory:
        root=Path(directory);settings=Settings(data_dir=root,db_url=f'sqlite:///{root/"fixture.db"}',seed_demo=False,core_cmd='unused',host='127.0.0.1',port=0)
        settings.blob_dir.mkdir(parents=True);db=Database(settings.resolved_db_url)
        try:
            db.create_all();store.initialize(db);archive.initialize(db);token=await prepare(db,settings)
            doc=document();contracts.validate('interview',doc)
            with db.session() as s:
                subject=authorize_read(s,token,CASE).subject_id
                put_doc(s,InterviewRow,CASE,RECORD,doc)
                store.grant(s,subject,CASE,enabled=True)
                archive.grant(s,subject,CASE,can_import=True,can_read=True)
            host=PersistentExtractionReviewHost(db=db,settings=settings,session_token=token,case_id=CASE,record_id=RECORD,provider=FixtureProvider(fixture_content()))
            with host:
                proposal=host.generate(str(uuid.uuid4()))
                host.review(proposal['proposalId'],str(uuid.uuid4()),0,[{'index':i+1,'decision':'needs_verification','note':'虚构演示，待核实'} for i in range(len(proposal['proposal']['result']['proposals']))])
            async with WorkingArchiveRPC(db=db,settings=settings,session_token=token,case_id=CASE) as rpc:
                del token
                output({**rpc.scope,'ready':True,'fixture':'fictional-fixed-output','storage':'temporary-sqlite-deleted-on-process-exit','crossProcessRetention':False,'completeBackup':False})
                lines=Lines();deadline=time.monotonic()+300
                for _ in range(64):
                    raw=lines.read(min(deadline,time.monotonic()+30))
                    if raw is None:return
                    value=json.loads(raw.decode(),object_pairs_hook=pairs,parse_constant=invalid)
                    output(await rpc.dispatch(value))
        finally:db.engine.dispose()

def main():
    if len(sys.argv)!=1:return 2
    try:asyncio.run(run());return 0
    except (Exception,KeyboardInterrupt):
        print('Fictional working review stopped without a confirmed result.',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
