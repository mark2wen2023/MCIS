"""Explicit fictional stdio fixture; no real input, account arguments or listener."""
import asyncio,json,sys,tempfile,time
from pathlib import Path
from ..config import Settings
from ..db import Database,put_doc
from ..identity.demo import prepare,CASE
from ..interviews.models import InterviewRow
from ..common import contracts
from ..investigation.fixture_host import Lines,output
from ..investigation.http_trial import pairs,invalid
from .host_extraction import FixtureProvider
from .extraction_review_host import ExtractionReviewHost

RECORD='IR-91'
def document():
 return {'recordId':RECORD,'caseId':CASE,'interviewee':{'intervieweeId':'FICTIONAL-PERSON','name':'虚构人员','role':'船员','affiliation':'虚构测试'},
 'startUtc':'2026-05-18T06:15:00Z','turns':[
 {'round':1,'question':'采取了什么行动？','answer':'我声称右满舵避让。','sensitiveFragments':[]},
 {'round':2,'question':'观察到了什么？','answer':'我声称看到目标船左转。','sensitiveFragments':[]}], 'statements':[]}
def fixture_content():
 return json.dumps({'statements':[
 {'kind':'Operation','subject':'rudder','summary':'声称右满舵避让，待核实','claim':{'valueType':'Occurrence','occurred':True},'round':1,'field':'Answer','quote':'右满舵避让'},
 {'kind':'Observation','subject':'other_ship','summary':'声称目标船左转，待核实','claim':{'valueType':'Occurrence','occurred':True},'round':2,'field':'Answer','quote':'目标船左转'}]},ensure_ascii=False)
async def run():
 with tempfile.TemporaryDirectory(prefix='mcis-extraction-review-') as directory:
  root=Path(directory);settings=Settings(data_dir=root,db_url=f'sqlite:///{root/"fixture.db"}',seed_demo=False,core_cmd='unused',host='127.0.0.1',port=0)
  settings.blob_dir.mkdir(parents=True);db=Database(settings.resolved_db_url)
  try:
   db.create_all();token=await prepare(db,settings)
   doc=document();contracts.validate('interview',doc)
   with db.session() as s:put_doc(s,InterviewRow,CASE,RECORD,doc)
   async with ExtractionReviewHost(db=db,settings=settings,session_token=token,case_id=CASE,record_id=RECORD,provider=FixtureProvider(fixture_content())) as host:
    del token
    output({**host.scope,'ready':True,'fixture':'fictional-fixed-output','storage':'temporary-sqlite-deleted-on-exit'})
    lines=Lines();deadline=time.monotonic()+300
    for _ in range(64):
     raw=lines.read(min(deadline,time.monotonic()+30))
     if raw is None:return
     value=json.loads(raw.decode(),object_pairs_hook=pairs,parse_constant=invalid)
     output(await host.dispatch(value))
  finally:db.engine.dispose()
def main():
 if len(sys.argv)!=1:return 2
 try:asyncio.run(run());return 0
 except (Exception,KeyboardInterrupt):
  print('Fictional extraction review stopped without a confirmed result.',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
