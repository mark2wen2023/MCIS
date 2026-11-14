import asyncio,base64,json,os,subprocess,sys,uuid
import pytest
from .test_host_extraction import extraction_case
from .test_extraction_working_store import working
from .test_working_history_archive import archive_bundle,permissions
from mcis_service.agents.working_archive_rpc import WorkingArchiveRPC,PROFILE
from mcis_service.agents import working_history_archive as a

def rpc(v):
    args,_=v
    return WorkingArchiveRPC(db=args[0],settings=args[1],session_token=args[2],case_id=args[3])
def request(c,action,**fields):return {k:c.scope[k] for k in ('profile','contextId','caseId')}|{'requestId':str(uuid.uuid4()),'action':action}|fields

def test_export_import_read_roundtrip(archive_bundle):
    v,raw=archive_bundle;permissions(v);c=rpc(v)
    async def check():
        exported=await c.dispatch(request(c,'export'));assert exported['ok']
        assert base64.b64decode(exported['body']['bundleBase64'])==raw
        req=request(c,'import',bundleBase64=exported['body']['bundleBase64'])
        first=await c.dispatch(req);second=await c.dispatch(req)
        assert first['ok'] and not first['body']['replayed'] and second['body']['replayed']
        listed=await c.dispatch(request(c,'list'));assert len(listed['body']['items'])==1
        read=await c.dispatch(request(c,'read',sha256=first['body']['sha256']))
        assert not read['body']['activated'] and not read['body']['historicalClaimsVerified']
        assert v[0][2] not in json.dumps(read)
        req['bundleBase64']=base64.b64encode(b'{}').decode();assert not (await c.dispatch(req))['ok']
    asyncio.run(check());c.close()

@pytest.mark.parametrize('extra',[{'path':'/tmp/secret'},{'provider':'local'},{'sha256':None},{'bundleBase64':'a'},{'token':'x'},{'body':{'payload':[]}}])
def test_forbidden_input(archive_bundle,extra):
    c=rpc(archive_bundle[0]);answer=asyncio.run(c.dispatch(request(c,'list',**extra)))
    assert not answer['ok'] and 'body' not in answer

@pytest.mark.parametrize('text',['%%%','e30=\n','e30','e31='])
def test_noncanonical_base64_rejected(archive_bundle,text):
    c=rpc(archive_bundle[0]);answer=asyncio.run(c.dispatch(request(c,'import',bundleBase64=text)))
    assert not answer['ok']

def test_import_not_read_grant(archive_bundle):
    v,raw=archive_bundle;permissions(v,read=False);c=rpc(v)
    out=asyncio.run(c.dispatch(request(c,'import',bundleBase64=base64.b64encode(raw).decode())))
    assert out['ok']
    assert asyncio.run(c.dispatch(request(c,'list')))['status']==403
    permissions(v,read=True,write=False)
    assert asyncio.run(c.dispatch(request(c,'read',sha256=out['body']['sha256'])))['ok']

def test_closed_and_scope(archive_bundle):
    c=rpc(archive_bundle[0]);req=request(c,'export');req['caseId']='other'
    assert not asyncio.run(c.dispatch(req))['ok']
    c.close();assert not asyncio.run(c.dispatch(request(c,'export')))['ok']

def test_subprocess_real_chain():
    env=dict(os.environ,PYTHONPATH='issue-journal/service')
    p=subprocess.Popen([sys.executable,'-m','mcis_service.agents.working_archive_fixture'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
    try:
        ready=json.loads(p.stdout.readline());assert ready['profile']==PROFILE and ready['crossProcessRetention'] is False
        def call(action,**data):
            req={k:ready[k] for k in ('profile','caseId','contextId')}|{'requestId':str(uuid.uuid4()),'action':action}|data
            p.stdin.write(json.dumps(req)+'\n');p.stdin.flush();return json.loads(p.stdout.readline())
        exported=call('export');assert exported['ok'] and not exported['body']['completeBackup']
        body=exported['body'];restored=call('import',bundleBase64=body['bundleBase64']);assert restored['ok']
        assert call('import',bundleBase64=body['bundleBase64'])['body']['replayed']
        assert len(call('list')['body']['items'])==1
        read=call('read',sha256=body['sha256']);assert read['ok']
        item=read['body']['payload']['proposals'][0]
        assert item['result']['fixture'] and len(item['reviews'])==1 and len(item['reviews'][0]['decisions'])==2
        p.stdin.close();assert p.wait(timeout=15)==0
    finally:
        if p.poll() is None:p.kill();p.wait()
