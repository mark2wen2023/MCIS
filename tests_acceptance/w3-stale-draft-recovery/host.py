"""Fixed synthetic stdio test controls only; never an application endpoint."""
import asyncio,json,sys,tempfile,uuid,os
from pathlib import Path
sys.path.insert(0,os.environ['MCIS_HOST_SERVICE'])
from mcis_service.config import Settings
from mcis_service.db import Database
from mcis_service.identity.demo import prepare,CASE
from mcis_service.identity.local import authorize_read
from mcis_service.investigation import journal
from mcis_service.investigation.host_bridge import IssueHostClient
async def run():
 with tempfile.TemporaryDirectory(prefix='w3-stale-draft-') as directory:
  root=Path(directory);settings=Settings(data_dir=root,db_url=f'sqlite:///{root/"test.db"}',seed_demo=False,core_cmd='unused',host='127.0.0.1',port=0)
  settings.blob_dir.mkdir(parents=True);db=Database(settings.resolved_db_url);host=None
  try:
   db.create_all();journal.initialize(db);token=await prepare(db,settings)
   with db.session() as s:
    subject=authorize_read(s,token,CASE).subject_id;journal.grant(s,subject,CASE,enabled=True)
   host=IssueHostClient(db=db,settings=settings,session_token=token,case_id=CASE)
   def request(action,**kw):return {k:v for k,v in {**host.scope,'requestId':str(uuid.uuid4()),'action':action,**kw}.items() if k!='productionLogin'}
   sources=(await host.dispatch(request('sources')))['body']['items'];ids=[str(uuid.uuid4()),str(uuid.uuid4())]
   for i,item in enumerate(sources):
    result=await host.dispatch(request('save',issueId=ids[i],operationId=str(uuid.uuid4()),expectedRevision=0,entry={'kind':'judgment','note':['假设甲待核','假设乙待核'][i],'sourceIds':[item['evidenceId']]},sourcePins=[{k:item[k] for k in ('evidenceId','sourceIncarnation','sourceSha256')}]))
    assert result['ok']
   def output(x):print(json.dumps(x,ensure_ascii=False),flush=True)
   output({'scope':host.scope,'ids':ids})
   for line in sys.stdin:
    value=json.loads(line)
    if value=={'testControl':'advance-same-judgment'}:
     result=await host.dispatch(request('save',issueId=ids[0],operationId=str(uuid.uuid4()),expectedRevision=1,
                                        entry={'kind':'verification','note':'并行核实仍针对原判断','sourceIds':[],'outcome':'inconclusive','againstJudgment':1}))
     assert result['ok'] and result['body']['revision']==2
     output({'revision':2})
    elif value=={'testControl':'advance-new-judgment'}:
     result=await host.dispatch(request('save',issueId=ids[1],operationId=str(uuid.uuid4()),expectedRevision=1,
                                        entry={'kind':'judgment','note':'并行添加新的判断，仍未审核','sourceIds':[]}))
     assert result['ok'] and result['body']['revision']==2
     output({'revision':2})
    elif value=={'testControl':'reopen'}:
     await host.__aexit__(None,None,None);db.engine.dispose();db=Database(settings.resolved_db_url)
     host=IssueHostClient(db=db,settings=settings,session_token=token,case_id=CASE)
     output({'scope':host.scope,'ids':ids})
    else:output(await host.dispatch(value))
  finally:
   if host:await host.__aexit__(None,None,None)
   db.engine.dispose()
asyncio.run(run())
