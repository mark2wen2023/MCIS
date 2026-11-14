"""Independent RPC security tests; no product modifications."""
import asyncio,base64,copy,uuid
import pytest
from sqlalchemy import select,func
from .test_working_history_archive import archive_bundle,permissions
from .test_extraction_working_store import working,host,decisions
from .test_host_extraction import extraction_case
from mcis_service.agents import working_archive_rpc as r,working_history_archive as a
from mcis_service.identity import local
from mcis_service.interviews.models import InterviewRow

def bridge(v):
    args,_=v
    return r.WorkingArchiveRPC(db=args[0],settings=args[1],session_token=args[2],case_id=args[3])
def req(c,action,**extra):return {k:v for k,v in c.scope.items() if k!='productionLogin'}|{'requestId':str(uuid.uuid4()),'action':action}|extra
def run(c,value):return asyncio.run(c.dispatch(value))
def encoded(raw):return base64.b64encode(raw).decode('ascii')
def imported_count(v):
    with v[0][0].session() as s:return s.scalar(select(func.count()).select_from(a.ImportedWorkingArchive))
def change_source(v):
    args,_=v
    with args[0].session() as s:
        row=s.scalars(select(InterviewRow).where(InterviewRow.case_id==args[3],InterviewRow.key==args[4])).one()
        row.doc={**row.doc,'signed':not row.doc.get('signed',False)}

def test_export_final_projection_source_change_cannot_return_stale_bundle(archive_bundle,monkeypatch):
    v,_=archive_bundle;c=bridge(v);old=r.bounded
    def bound(value,limit):
        result=old(value,limit)
        if isinstance(value,dict) and value.get('ok') is True:change_source(v)
        return result
    monkeypatch.setattr(r,'bounded',bound)
    out=run(c,req(c,'export'))
    assert out['ok'] is False and 'body' not in out


def test_export_worker_source_change_rejected(archive_bundle,monkeypatch):
    v,_=archive_bundle;c=bridge(v);old=r.run_in_threadpool
    async def worker(fn,*args):
        result=await old(fn,*args);change_source(v);return result
    monkeypatch.setattr(r,'run_in_threadpool',worker)
    assert not run(c,req(c,'export'))['ok']


def test_import_postcommit_projection_unknown_original_retry_replayed(archive_bundle,monkeypatch):
    v,raw=archive_bundle;permissions(v);c=bridge(v);request=req(c,'import',bundleBase64=encoded(raw));old=r.bounded
    def fail(value,limit):
        if isinstance(value,dict) and value.get('ok') is True:raise ValueError('projection')
        return old(value,limit)
    monkeypatch.setattr(r,'bounded',fail);out=run(c,request)
    assert out['status']==503 and out['code'].endswith('UNCONFIRMED') and imported_count(v)==1
    monkeypatch.setattr(r,'bounded',old);out=run(c,request)
    assert out['ok'] and out['body']['replayed'] and imported_count(v)==1


@pytest.mark.parametrize('mutation',['case','context','profile','extra','path','role','nested','null','badbase64','noncanonical','oversize','badsha'])
def test_rpc_hostile_request_rejected_without_import(archive_bundle,mutation):
    v,raw=archive_bundle;permissions(v);c=bridge(v);request=req(c,'import',bundleBase64=encoded(raw))
    if mutation=='case':request['caseId']='OTHER'
    elif mutation=='context':request['contextId']=str(uuid.uuid4())
    elif mutation=='profile':request['profile']='old-profile'
    elif mutation=='extra':request['sha256']='a'*64
    elif mutation=='path':request['path']='/tmp/secret'
    elif mutation=='role':request['role']='Admin'
    elif mutation=='nested':request['bundleBase64']={'x':[[]]}
    elif mutation=='null':request['bundleBase64']=None
    elif mutation=='badbase64':request['bundleBase64']='%%%'
    elif mutation=='noncanonical':request['bundleBase64']='Zh=='
    elif mutation=='oversize':request['bundleBase64']='A'*(r.ENCODED_LIMIT+4)
    elif mutation=='badsha':request=req(c,'read',sha256='not-hash')
    result=run(c,request)
    assert not result['ok'] and 'body' not in result and imported_count(v)==0


def test_same_requestid_cannot_change_payload_or_action(archive_bundle):
    v,raw=archive_bundle;permissions(v);c=bridge(v);request=req(c,'import',bundleBase64=encoded(raw))
    assert run(c,request)['ok']
    changed={**request,'bundleBase64':encoded(b'{}')}
    assert not run(c,changed)['ok']
    changed=req(c,'list');changed['requestId']=request['requestId']
    assert not run(c,changed)['ok'] and imported_count(v)==1


def test_seen_budget_allows_original_retry_not_new_requests(archive_bundle):
    v,_=archive_bundle;permissions(v);c=bridge(v);first=req(c,'list')
    assert run(c,first)['ok']
    for _ in range(63):assert run(c,req(c,'list'))['ok']
    assert not run(c,req(c,'list'))['ok'] and run(c,first)['ok']


def test_import_grant_revoked_after_commit_unknown_and_retry_denied(archive_bundle,monkeypatch):
    v,raw=archive_bundle;permissions(v);c=bridge(v);old=r.run_in_threadpool
    async def worker(fn,*args):
        result=await old(fn,*args);permissions(v,read=True,write=False);return result
    monkeypatch.setattr(r,'run_in_threadpool',worker);request=req(c,'import',bundleBase64=encoded(raw))
    out=run(c,request)
    assert not out['ok'] and out['status']==503 and imported_count(v)==1
    monkeypatch.setattr(r,'run_in_threadpool',old)
    assert run(c,request)['status']==403


def test_read_final_grant_revocation_hides_body(archive_bundle,monkeypatch):
    v,raw=archive_bundle;permissions(v);c=bridge(v);saved=run(c,req(c,'import',bundleBase64=encoded(raw)))['body'];old=r.bounded
    def bound(value,limit):
        result=old(value,limit)
        if isinstance(value,dict) and value.get('ok') is True:permissions(v,read=False,write=True)
        return result
    monkeypatch.setattr(r,'bounded',bound)
    out=run(c,req(c,'read',sha256=saved['sha256']))
    assert not out['ok'] and out['status']==403 and 'body' not in out


def test_close_after_worker_hides_committed_import(archive_bundle,monkeypatch):
    v,raw=archive_bundle;permissions(v);c=bridge(v);old=r.run_in_threadpool
    async def worker(fn,*args):
        result=await old(fn,*args);c.close();return result
    monkeypatch.setattr(r,'run_in_threadpool',worker)
    out=run(c,req(c,'import',bundleBase64=encoded(raw)))
    assert not out['ok'] and out['status']==503 and imported_count(v)==1


def test_live_source_change_does_not_disable_explicit_historical_reads(archive_bundle):
    v,raw=archive_bundle;permissions(v);c=bridge(v)
    saved=run(c,req(c,'import',bundleBase64=encoded(raw)))['body'];change_source(v)
    out=run(c,req(c,'read',sha256=saved['sha256']))
    assert out['ok'] and not out['body']['activated'] and not out['body']['historicalClaimsVerified']
    assert not run(c,req(c,'export'))['ok']

@pytest.mark.parametrize('raw',[b'['*2000+b']'*2000,b'{"x":NaN}',b'{"sha256":"a","sha256":"b"}',b' '*(a.MAX_BYTES+1)])
def test_malformed_and_overbudget_archive_never_saved(archive_bundle,raw):
    v,_=archive_bundle;permissions(v);c=bridge(v)
    result=run(c,req(c,'import',bundleBase64=encoded(raw)))
    assert not result['ok'] and 'body' not in result and imported_count(v)==0


def test_scope_epoch_change_cannot_rebind_existing_host(archive_bundle):
    from mcis_service.cases.models import CaseRow
    v,_=archive_bundle;permissions(v);c=bridge(v);args,_=v
    with args[0].session() as s:
        row=s.scalars(select(CaseRow).where(CaseRow.case_id==args[3])).one();row.doc={**row.doc,'caseEpochUtc':'2020-01-01T00:00:00Z'}
    assert not run(c,req(c,'list'))['ok']


def test_cancelled_response_may_have_saved_retry_is_same_import(archive_bundle,monkeypatch):
    v,raw=archive_bundle;permissions(v);c=bridge(v);old=r.run_in_threadpool;request=req(c,'import',bundleBase64=encoded(raw))
    async def worker(fn,*args):
        await old(fn,*args);raise asyncio.CancelledError()
    monkeypatch.setattr(r,'run_in_threadpool',worker)
    with pytest.raises(asyncio.CancelledError):run(c,request)
    assert imported_count(v)==1
    monkeypatch.setattr(r,'run_in_threadpool',old)
    result=run(c,request)
    assert result['ok'] and result['body']['replayed'] and imported_count(v)==1
