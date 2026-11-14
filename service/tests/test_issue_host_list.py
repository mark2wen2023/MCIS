import asyncio,uuid
from .test_issue_journal import ready
from .test_issue_host_sources import client,message
from .test_issue_host_bridge import request
from mcis_service.investigation import journal
from .conftest import CASE

def test_real_list_open_append_roundtrip(ready):
 async def run():
  async with client(ready) as c:
   assert (await c.dispatch(message(c,action='list')))['body']['items']==[]
   command=request(c,ready)
   assert (await c.dispatch(command))['ok']
   result=await c.dispatch(message(c,action='list'))
   assert result['ok'] and result['body']['profile']=='trial-issue-list-v1'
   summary=result['body']['items'][0]
   assert summary['issueId']==ready[4] and summary['revision']==1
   read=request(c,ready,action='read',operationId=None,entry=None,expectedRevision=None)
   assert (await c.dispatch(read))['body']['revision']==1
   command['operationId']=str(uuid.uuid4());command['expectedRevision']=1
   command['entry']={'kind':'verification','note':'继续核实','outcome':'inconclusive','againstJudgment':1}
   assert (await c.dispatch(command))['ok']
   assert (await c.dispatch(message(c,action='list')))['body']['items'][0]['revision']==2
   assert (await c.dispatch(read))['body']['events'][0]['note']=='保留判断'
 asyncio.run(run())
