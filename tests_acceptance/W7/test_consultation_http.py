"""Real loopback HTTP acceptance; disposable seeded SQLite, no project data writes."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error

import pytest

ROOT = Path(__file__).resolve().parents[2]
CASE = 'CASE-2026-DEMO-LILY-MARY'
OTHER = 'CASE-2025-HAILI5-WANA17'

@pytest.fixture()
def server(tmp_path_factory):
    tmp = tmp_path_factory.mktemp('w71-http')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    env = {**os.environ, 'MCIS_DATA_DIR':str(tmp), 'MCIS_DB_URL':f'sqlite:///{tmp}/test.db', 'MCIS_SEED_DEMO':'1'}
    log = (tmp/'server.log').open('w')
    p = subprocess.Popen([sys.executable,'-m','uvicorn','mcis_service.main:create_app','--factory','--host','127.0.0.1','--port',str(port)],cwd=ROOT/'service',env=env,stdout=log,stderr=log)
    base=f'http://127.0.0.1:{port}/api/v1/cases/'
    def call(method,path,body=None,role='Investigator',case=CASE):
        req=urllib.request.Request(base+case+path,method=method,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json','X-MCIS-Role':role})
        try:
            with urllib.request.urlopen(req,timeout=15) as response:return response.status,json.load(response)
        except urllib.error.HTTPError as e:return e.code,json.load(e)
    try:
        for _ in range(100):
            try:
                if call('GET','/consultation/rounds')[0]==200:break
            except (OSError,ValueError):pass
            time.sleep(.1)
        else:raise RuntimeError((tmp/'server.log').read_text())
        yield call
    finally:
        p.terminate();p.wait(timeout=15);log.close()

def audit(call):
    status,data=call('GET','/audit?category=Consultation');assert status==200;return data

def unchanged_failure(call,method,path,body,code,role='Investigator'):
    before=audit(call)
    status,_=call(method,path,body,role=role)
    assert status==code
    assert audit(call)==before

@pytest.mark.parametrize('role,read_status',[('InterestedState',200),('ExternalExpert',403),('Public',403)])
def test_read_only_and_deny_cannot_write_or_append_audit(server,role,read_status):
    assert server('GET','/consultation/rounds',role=role)[0]==read_status
    unchanged_failure(server,'POST','/consultation/rounds/2/replies',{'partyId':'FLAG-B','text':'not authorized'},403,role)
    unchanged_failure(server,'PATCH','/consultation/rounds/2/comments/R2-C01',{'decision':'Adopted'},403,role)

def test_reply_two_pending_distinct_decisions_persist_and_chain_valid(server):
    call=server; before=audit(call)
    other=call('GET','/consultation/rounds',case=OTHER)
    payload={'partyId':'FLAG-B','text':'Independent synthetic reply','comments':['first independent comment','second independent comment']}
    status,r=call('POST','/consultation/rounds/2/replies',payload);assert status==201
    ids=r['replies'][-1]['commentIds'];assert len(ids)==2 and len(set(ids))==2
    assert all(c['decision']=='Pending' for c in r['comments'] if c['commentId'] in ids)
    after=audit(call);assert len(after)==len(before)+1 and after[-1]['action']=='consultation.reply'
    unchanged_failure(call,'POST','/consultation/rounds/2/replies',payload,409)
    path='/consultation/rounds/2/comments/'
    unchanged_failure(call,'PATCH',path+ids[1],{'decision':'NotAdopted','feedback':'  '},422)
    for cid,decision,feedback in [(ids[0],'Adopted',''),(ids[1],'NotAdopted','Independent rationale')]:
        n=len(audit(call));assert call('PATCH',path+cid,{'decision':decision,'feedback':feedback})[0]==200
        assert len(audit(call))==n+1
        unchanged_failure(call,'PATCH',path+cid,{'decision':decision,'feedback':feedback},409)
    reloaded=next(r for r in call('GET','/consultation/rounds')[1] if r['roundNo']==2)
    assert [c['decision'] for c in reloaded['comments'] if c['commentId'] in ids]==['Adopted','NotAdopted']
    assert call('GET','/consultation/rounds',case=OTHER)==other
    status,verified=call('GET','/audit:verify');assert status==200 and verified['valid']

def test_closed_round_blocks_new_reply_but_pending_decision_remains_allowed(server):
    call=server
    unchanged_failure(call,'POST','/consultation/rounds/2:close',{},409)
    assert call('POST','/consultation/rounds/2/replies',{'partyId':'FLAG-B','text':'Synthetic close setup'})[0]==201
    assert call('POST','/consultation/rounds/2/waivers',{'partyId':'CO-MARY','reason':'Independent waiver'})[0]==201
    assert call('POST','/consultation/rounds/2:close',{})[0]==200
    unchanged_failure(call,'POST','/consultation/rounds/2/replies',{'partyId':'CO-MARY'},409)
    unchanged_failure(call,'POST','/consultation/rounds/2:close',{},409)
    r=next(x for x in call('GET','/consultation/rounds')[1] if x['roundNo']==2)
    pending=next(c for c in r['comments'] if c['decision']=='Pending')
    n=len(audit(call))
    assert call('PATCH',f"/consultation/rounds/2/comments/{pending['commentId']}",{'decision':'PartiallyAdopted','feedback':'Independent partial reason'})[0]==200
    assert len(audit(call))==n+1
    assert call('GET','/audit:verify')[1]['valid']
