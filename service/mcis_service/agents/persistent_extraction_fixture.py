"""Fictional per-process SQLite demo; no cross-process retention or real inputs."""
import asyncio,json,sys,tempfile,time
from pathlib import Path
from ..config import Settings
from ..db import Database,put_doc
from ..identity.demo import prepare,CASE
from ..identity.local import authorize_read
from ..interviews.models import InterviewRow
from ..common import contracts
from ..investigation.fixture_host import Lines,output
from ..investigation.http_trial import pairs,invalid
from .extraction_review_fixture import document,fixture_content,RECORD
from .host_extraction import FixtureProvider
from .persistent_extraction_review_host import PersistentExtractionReviewHost
from .persistent_extraction_rpc import PersistentExtractionRPC
from . import extraction_working_store as store

async def run():
    with tempfile.TemporaryDirectory(prefix='mcis-persistent-working-demo-') as directory:
        root=Path(directory);settings=Settings(data_dir=root,db_url=f'sqlite:///{root/"fixture.db"}',seed_demo=False,core_cmd='unused',host='127.0.0.1',port=0)
        settings.blob_dir.mkdir(parents=True);db=Database(settings.resolved_db_url)
        try:
            db.create_all();store.initialize(db);token=await prepare(db,settings)
            doc=document();contracts.validate('interview',doc)
            with db.session() as s:
                subject=authorize_read(s,token,CASE).subject_id
                put_doc(s,InterviewRow,CASE,RECORD,doc)
                store.grant(s,subject,CASE,enabled=True)
            host=PersistentExtractionReviewHost(db=db,settings=settings,session_token=token,case_id=CASE,record_id=RECORD,provider=FixtureProvider(fixture_content()))
            del token
            async with PersistentExtractionRPC(host) as rpc:
                output({**rpc.scope,'ready':True,'fixture':'fictional-fixed-output','storage':'temporary-sqlite-deleted-on-process-exit','crossProcessRetention':False})
                lines=Lines();deadline=time.monotonic()+300
                for _ in range(128):
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
