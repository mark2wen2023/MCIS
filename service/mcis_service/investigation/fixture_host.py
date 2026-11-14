"""Explicit fictional stdio fixture: no actual account args, socket or old server."""
import asyncio
import json
import os
from pathlib import Path
import select
import sys
import tempfile
import time
from ..config import Settings
from ..db import Database
from ..identity.demo import prepare,CASE
from ..identity.local import authorize_read
from . import journal
from .host_bridge import IssueHostClient
from .http_trial import pairs,invalid

LIMIT=65536
class Lines:
    def __init__(self):self.pending=b''
    def read(self,deadline):
        while b'\n' not in self.pending:
            remaining=deadline-time.monotonic()
            if remaining<=0 or not select.select([sys.stdin.fileno()],[],[],remaining)[0]:raise TimeoutError()
            chunk=os.read(sys.stdin.fileno(),4096)
            if not chunk:
                if self.pending:raise ValueError()
                return None
            self.pending+=chunk
            if len(self.pending.split(b'\n',1)[0])>LIMIT:raise ValueError()
        line,self.pending=self.pending.split(b'\n',1)
        if len(line)>LIMIT:raise ValueError()
        return line

def output(value):
    raw=json.dumps(value,ensure_ascii=False,separators=(',',':'))
    if len(raw.encode())>8*1024*1024:raise ValueError()
    print(raw,flush=True)

async def run():
    # Fixed local fictional data; all configuration points to newly-created tempdir.
    with tempfile.TemporaryDirectory(prefix='mcis-issue-host-') as directory:
        root=Path(directory);settings=Settings(data_dir=root,db_url=f'sqlite:///{root/"fixture.db"}',seed_demo=False,core_cmd='unused',host='127.0.0.1',port=0)
        settings.blob_dir.mkdir(parents=True);db=Database(settings.resolved_db_url)
        try:
            db.create_all();journal.initialize(db);token=await prepare(db,settings)
            with db.session() as s:journal.grant(s,authorize_read(s,token,CASE).subject_id,CASE,enabled=True)
            async with IssueHostClient(db=db,settings=settings,session_token=token,case_id=CASE) as client:
                del token
                output({**client.scope,'ready':True,'fixture':'fictional','storage':'temporary-sqlite-deleted-on-exit'})
                lines=Lines();deadline=time.monotonic()+300
                for _ in range(100):
                    raw=lines.read(min(deadline,time.monotonic()+30))
                    if raw is None:return
                    value=json.loads(raw.decode(),object_pairs_hook=pairs,parse_constant=invalid)
                    output(await client.dispatch(value))
        finally:db.engine.dispose()

def main():
    if len(sys.argv)!=1:return 2
    try:asyncio.run(run());return 0
    except (Exception,KeyboardInterrupt):
        print('Fixture host stopped without a confirmed result.',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
