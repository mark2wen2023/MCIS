import asyncio,json,uuid
import httpx,pytest
from .test_issue_journal import ready,add
from .test_issue_host_sources import client,message
from .conftest import CASE
from mcis_service.investigation import host_bridge as h,journal
from mcis_service.identity import local


def test_list_real_empty_then_card_no_write_grant(ready):
    async def run():
        async with client(ready) as c:
            assert (await c.dispatch(message(c,action='list')))['body']['items']==[]
            add(ready,0,note='a'*250)
            with ready[0].app.state.db.session() as s:journal.grant(s,ready[2],CASE,enabled=False)
            result=await c.dispatch(message(c,action='list'));assert result['ok'];body=result['body']
            assert body['profile']=='trial-issue-list-v1' and body['caseId']==CASE
            assert body['items']==[{'issueId':ready[4],'revision':1,'openingNotePreview':'a'*200,'lastKind':'judgment','status':'working_unreviewed'}]
            assert ready[3] not in json.dumps(result) and 'authorSubjectId' not in json.dumps(result)
    asyncio.run(run())

@pytest.mark.parametrize('field',['issueId','operationId','expectedRevision','entry','sourcePins'])
def test_list_null_write_fields_rejected_before_transport(ready,monkeypatch,field):
    async def fail(*a,**kw):pytest.fail('invalid request must not reach transport')
    monkeypatch.setattr(httpx.AsyncClient,'get',fail)
    async def run():
        async with client(ready) as c:assert not (await c.dispatch(message(c,action='list',**{field:None})))['ok']
    asyncio.run(run())

@pytest.mark.parametrize('change',['revoke','epoch','closed','case'])
def test_list_scope_and_late_revocation(ready,monkeypatch,change):
    add(ready,0)
    async def run():
        async with client(ready) as c:
            old=httpx.AsyncClient.get
            async def changed(self,*args,**kwargs):
                result=await old(self,*args,**kwargs)
                if change=='revoke':
                    with ready[0].app.state.db.session() as s:local.revoke_session(s,ready[3])
                elif change=='epoch':
                    original=h.load_case;monkeypatch.setattr(h,'load_case',lambda *a:{**original(*a),'caseEpochUtc':'2000-01-01T00:00:00Z'})
                elif change=='closed':await c.__aexit__(None,None,None)
                else:pytest.fail('cross case must not reach transport')
                return result
            monkeypatch.setattr(httpx.AsyncClient,'get',changed)
            result=await c.dispatch(message(c,action='list',**({'caseId':'FOREIGN'} if change=='case' else {})))
            assert not result['ok'] and 'items' not in json.dumps(result)
    asyncio.run(run())

@pytest.mark.parametrize('damage',['case','duplicate','limit','revisionbool','revisionzero','revisionlarge','uuid','preview','approved','kind'])
def test_list_malformed_summary_rejected(ready,monkeypatch,damage):
    add(ready,0)
    async def run():
        async with client(ready) as c:
            old=httpx.AsyncClient.get
            async def changed(self,*args,**kwargs):
                result=await old(self,*args,**kwargs);data=result.json();item=data['items'][0]
                if damage=='case':data['caseId']='OTHER'
                elif damage=='duplicate':data['items']*=2
                elif damage=='limit':data['items']*=101
                elif damage=='revisionbool':item['revision']=True
                elif damage=='revisionzero':item['revision']=0
                elif damage=='revisionlarge':item['revision']=201
                elif damage=='uuid':item['issueId']='not-uuid'
                elif damage=='preview':item['openingNotePreview']='x'*201
                elif damage=='approved':item['status']='approved'
                else:item['lastKind']='fact'
                return httpx.Response(200,json=data)
            monkeypatch.setattr(httpx.AsyncClient,'get',changed)
            result=await c.dispatch(message(c,action='list'));assert not result['ok']
    asyncio.run(run())


def test_list_extra_internal_fields_never_projected(ready,monkeypatch):
    add(ready,0)
    async def run():
        async with client(ready) as c:
            old=httpx.AsyncClient.get
            async def changed(self,*args,**kwargs):
                result=await old(self,*args,**kwargs);data=result.json();data['items'][0].update(authorSubjectId='private',sourceSnapshots={'secret':'private'},events=['private'],token=ready[3]);return httpx.Response(200,json=data)
            monkeypatch.setattr(httpx.AsyncClient,'get',changed)
            result=await c.dispatch(message(c,action='list'));assert result['ok'] and 'private' not in json.dumps(result) and ready[3] not in json.dumps(result)
    asyncio.run(run())
