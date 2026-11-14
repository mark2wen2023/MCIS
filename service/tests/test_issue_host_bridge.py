import asyncio,uuid
import pytest
from .test_issue_journal import ready
from .conftest import CASE
from mcis_service.investigation.host_bridge import IssueHostClient
from mcis_service.investigation import journal
from mcis_service.identity import local

def request(client,v,**more):return {'profile':client.scope['profile'],'contextId':client.scope['contextId'],'requestId':str(uuid.uuid4()),'action':'save','caseId':CASE,'issueId':v[4],'operationId':str(uuid.uuid4()),'expectedRevision':0,'entry':{'kind':'judgment','note':'保留判断'},**more}

def test_real_protected_roundtrip(ready):
 async def run():
  t,_,_,token,_=ready
  async with IssueHostClient(db=t.app.state.db,settings=t.app.state.settings,session_token=token,case_id=CASE) as c:
   msg=request(c,ready);one=await c.dispatch(msg);two=await c.dispatch(msg)
   assert one['ok'] and two['ok'] and one['body']['revision']==two['body']['revision']==1
   read=await c.dispatch(request(c,ready,action='read',operationId=None,entry=None,expectedRevision=None))
   assert read['body']['events'][0]['note']=='保留判断'
   assert token not in str(read) and 'authorSubjectId' not in str(read)
 asyncio.run(run())

@pytest.mark.parametrize('extra',[{'caseId':'FOREIGN'},{'contextId':'foreign'},{'role':'LeadInvestigator'},{'url':'http://evil'},{'token':'fake'}])
def test_injected_scope(ready,extra):
 async def run():
  t,_,_,token,_=ready
  async with IssueHostClient(db=t.app.state.db,settings=t.app.state.settings,session_token=token,case_id=CASE) as c:
   result=await c.dispatch(request(c,ready,**extra));assert not result['ok'] and token not in str(result)
   assert journal.list_issues(t.app.state.db,token,CASE)['items']==[]
 asyncio.run(run())

def test_revoked_and_closed(ready):
 async def run():
  t,_,sub,token,_=ready
  async with IssueHostClient(db=t.app.state.db,settings=t.app.state.settings,session_token=token,case_id=CASE) as c:
   msg=request(c,ready)
   with t.app.state.db.session() as s:local.revoke_session(s,token)
   assert not (await c.dispatch(msg))['ok']
  assert not (await c.dispatch(msg))['ok']
 asyncio.run(run())
