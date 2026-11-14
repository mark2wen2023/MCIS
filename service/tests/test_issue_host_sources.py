import asyncio,uuid,json
import httpx,pytest
from .test_issue_journal import ready
from .conftest import CASE
from mcis_service.investigation import host_bridge as h,journal
from mcis_service.identity import local


def message(c,**extra):return {**{k:c.scope[k] for k in ('profile','contextId','caseId')},'requestId':str(uuid.uuid4()),'action':'sources',**extra}
def client(v):return h.IssueHostClient(db=v[0].app.state.db,settings=v[0].app.state.settings,session_token=v[3],case_id=CASE)

def test_current_sources_minimal_projection(ready):
    async def run():
        async with client(ready) as c:
            result=await c.dispatch(message(c));assert result['ok'];body=result['body']
            assert body['profile']=='trial-issue-sources-v1'
            assert body['selectionSnapshotPinned'] is False and body['observationApproval']=='not_assessed'
            assert body['scope']=='current-local-supported-candidates-only'
            assert ready[1]['evidenceId'] in [x['evidenceId'] for x in body['items']]
            for item in body['items']:assert set(item)=={'evidenceId','sourceSha256','mediaKind','byteLength','registeredUtc','sourceIncarnation'}
            assert ready[3] not in json.dumps(result) and 'relativePath' not in json.dumps(result)
    asyncio.run(run())

@pytest.mark.parametrize('extra',[{'issueId':None},{'issueId':str(uuid.uuid4())},{'entry':None},{'expectedRevision':None},{'operationId':None},{'caseId':'OTHER'},{'contextId':'OTHER'},{'role':'LeadInvestigator'}])
def test_sources_rejects_write_or_foreign_fields_before_http(ready,extra,monkeypatch):
    async def fail(*a,**k):pytest.fail('bad request must not reach transport')
    monkeypatch.setattr(httpx.AsyncClient,'get',fail)
    async def run():
        async with client(ready) as c:assert not (await c.dispatch(message(c,**extra)))['ok']
    asyncio.run(run())

def test_sources_no_write_grant_required(ready):
    t,_,sub,token,_=ready
    with t.app.state.db.session() as s:journal.grant(s,sub,CASE,enabled=False)
    async def run():
        async with client(ready) as c:assert (await c.dispatch(message(c)))['ok']
    asyncio.run(run())

@pytest.mark.parametrize('change',['revoke','epoch','closed'])
def test_late_source_response_denied(ready,monkeypatch,change):
    async def run():
        async with client(ready) as c:
            old=httpx.AsyncClient.get
            async def changed(self,*args,**kwargs):
                result=await old(self,*args,**kwargs)
                if change=='revoke':
                    with ready[0].app.state.db.session() as s:local.revoke_session(s,ready[3])
                elif change=='epoch':
                    original=h.load_case
                    monkeypatch.setattr(h,'load_case',lambda *a:{**original(*a),'caseEpochUtc':'2000-01-01T00:00:00Z'})
                else:await c.__aexit__(None,None,None)
                return result
            monkeypatch.setattr(httpx.AsyncClient,'get',changed)
            result=await c.dispatch(message(c));assert not result['ok'] and 'items' not in result
    asyncio.run(run())

@pytest.mark.parametrize('damage',['case','generation','epoch','duplicate','hash','bytesbool','media','date','limit'])
def test_catalog_response_validation(ready,monkeypatch,damage):
    async def run():
        async with client(ready) as c:
            old=httpx.AsyncClient.get
            async def changed(self,*args,**kwargs):
                original=await old(self,*args,**kwargs);data=original.json()
                if damage=='case':data['caseId']='OTHER'
                if damage=='generation':data['caseIncarnation']=str(uuid.uuid4())
                if damage=='epoch':data['caseEpochUtc']='2000-01-01T00:00:00Z'
                if damage=='duplicate':data['items']*=2
                if damage=='hash':data['items'][0]['sourceSha256']='bad'
                if damage=='bytesbool':data['items'][0]['byteLength']=True
                if damage=='media':data['items'][0]['mediaKind']='video'
                if damage=='date':data['items'][0]['registeredUtc']='2026-01-01'
                if damage=='limit':data['items']*=101
                return httpx.Response(200,json=data)
            monkeypatch.setattr(httpx.AsyncClient,'get',changed)
            result=await c.dispatch(message(c));assert not result['ok'] and 'items' not in result
    asyncio.run(run())
