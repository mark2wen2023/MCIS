"""Synthetic loopback TCP queue/lock experiment; not a capacity or throughput benchmark."""
import base64
import http.client
import json
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
import uvicorn
from sqlalchemy import event
from tests.test_evidence_intake_w42 import local,CASE
from tests.conftest import H
from mcis_service.evidence import recorded_content
from mcis_service.redaction.policy import default_policy
from mcis_service.audit.models import AuditEventRow
from mcis_service.evidence.models import CustodyEventRow

URL=f'/api/v1/cases/{CASE}'


def test_four_tcp_reads_queue_not_reject_and_keep_revocation_order(local,monkeypatch):
    c,app=local;raw=b'synthetic-payload-'*65536
    r=c.post(URL+'/evidence',headers=H(),json={'title':'Synthetic queue study','source':'Synthetic',
        'extractedBy':'Independent','extractedUtc':'2026-01-01T00:00:00Z',
        'relativePath':'evidence/queue.bin','contentBase64':base64.b64encode(raw).decode()})
    assert r.status_code==201,r.text
    endpoint=URL+'/evidence/'+r.json()['evidenceId']+'/content'
    @event.listens_for(app.state.db.engine,'checkout')
    def timeout(conn,*_):conn.execute('PRAGMA busy_timeout=100')  # Test-only100ms.
    arrived=threading.Event();entered=threading.Event();release=threading.Event()
    guard=threading.Lock();metrics={'arrived':0,'active_reads':0,'max_active_reads':0,'read_calls':0}
    async def wrapper(scope,receive,send):
        if scope['type']=='http' and scope['method']=='GET' and scope['path']==endpoint:
            with guard:
                metrics['arrived']+=1
                if metrics['arrived']==4:arrived.set()
        await app(scope,receive,send)
    original=recorded_content.read_content
    def held(path):
        with guard:
            metrics['active_reads']+=1;metrics['read_calls']+=1
            metrics['max_active_reads']=max(metrics['max_active_reads'],metrics['active_reads'])
            first=metrics['read_calls']==1
        try:
            if first:entered.set();assert release.wait(8)
            return original(path)
        finally:
            with guard:metrics['active_reads']-=1
    monkeypatch.setattr(recorded_content,'read_content',held)
    sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen(16);port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(wrapper,host='127.0.0.1',port=port,lifespan='off',log_level='error',access_log=False))
    thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);thread.start()
    def request(method,path,body=None,headers=None):
        conn=http.client.HTTPConnection('127.0.0.1',port,timeout=10)
        try:
            conn.request(method,path,json.dumps(body) if body is not None else None,headers={**(headers or H()),'Content-Type':'application/json'})
            response=conn.getresponse();data=response.read()
            return response.status,data
        finally:conn.close()
    try:
        deadline=time.monotonic()+5
        while not server.started and thread.is_alive() and time.monotonic()<deadline:time.sleep(.01)
        assert server.started
        policy=default_policy();policy['matrix']['Investigator']['evidence_meta']='Deny'
        with ThreadPoolExecutor(4) as pool:
            first=pool.submit(request,'GET',endpoint);assert entered.wait(3)
            requests=[first]+[pool.submit(request,'GET',endpoint) for _ in range(3)]
            try:
                assert arrived.wait(3)  # All four TCP requests reached ASGI, not just client submission.
                assert sum(f.done() for f in requests)==0
                assert metrics['read_calls']==1 and metrics['max_active_reads']==1
                status,data=request('PUT',URL+'/access-policy',policy,H('LeadInvestigator'))
                problem=json.loads(data)
                assert status==503 and problem['code']=='POLICY_WRITE_BUSY'
                assert problem['detail']=={'commitState':'not_committed','retryable':True}
                assert sum(f.done() for f in requests)==0
            finally:release.set()
            responses=[future.result(timeout=8) for future in requests]
        assert all(status==200 and data==raw for status,data in responses)
        assert metrics['read_calls']==4 and metrics['max_active_reads']==1
        with app.state.db.session() as s:
            assert s.query(CustodyEventRow).filter_by(kind='Access').count()==4
            assert s.query(AuditEventRow).filter_by(action='policy.update').count()==0
        status,_=request('PUT',URL+'/access-policy',policy,H('LeadInvestigator'));assert status==200
        status,data=request('GET',endpoint);assert status==403 and raw not in data
        assert metrics['read_calls']==4
    finally:
        release.set();server.should_exit=True;thread.join(timeout=3);sock.close()
    assert not thread.is_alive()


def test_response_body_can_remain_live_after_database_and_python_locks_release(local):
    """Controlled ASGI send stall, not a measurement of real slow-client buffering."""
    import asyncio
    import sqlite3
    c,app=local;raw=b'synthetic-retained-body-'*32768
    r=c.post(URL+'/evidence',headers=H(),json={'title':'Synthetic send hold','source':'Synthetic',
        'extractedBy':'Independent','extractedUtc':'2026-01-01T00:00:00Z',
        'relativePath':'evidence/send-hold.bin','contentBase64':base64.b64encode(raw).decode()})
    assert r.status_code==201,r.text
    endpoint=URL+'/evidence/'+r.json()['evidenceId']+'/content'
    ready=threading.Event();release=threading.Event();observed={}
    async def wrapper(scope,receive,send):
        hold=scope['type']=='http' and (b'x-study-hold',b'1') in scope.get('headers',[])
        async def output(message):
            if hold and message['type']=='http.response.body' and message.get('body'):
                observed['retained_bytes']=len(message['body']);ready.set()
                assert await asyncio.to_thread(release.wait,6)
            await send(message)
        await app(scope,receive,output)
    sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen(16);port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(wrapper,host='127.0.0.1',port=port,lifespan='off',log_level='error',access_log=False))
    thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);thread.start()
    def request(method,path,body=None,headers=None):
        conn=http.client.HTTPConnection('127.0.0.1',port,timeout=8)
        try:
            conn.request(method,path,json.dumps(body) if body is not None else None,headers={**(headers or H()),'Content-Type':'application/json'})
            response=conn.getresponse();return response.status,response.read()
        finally:conn.close()
    try:
        deadline=time.monotonic()+5
        while not server.started and thread.is_alive() and time.monotonic()<deadline:time.sleep(.01)
        assert server.started
        with ThreadPoolExecutor(1) as pool:
            first=pool.submit(request,'GET',endpoint,None,{**H(),'X-Study-Hold':'1'})
            try:
                assert ready.wait(3) and observed['retained_bytes']==len(raw) and not first.done()
                db=sqlite3.connect(app.state.settings.data_dir/'test.db',timeout=.05)
                try:db.execute('BEGIN IMMEDIATE');db.rollback()
                finally:db.close()
                # Another GET takes WRITE_LOCK and commits while first response still holds bytes.
                status,data=request('GET',endpoint);assert status==200 and data==raw
                policy=default_policy();policy['matrix']['Investigator']['evidence_meta']='Deny'
                status,_=request('PUT',URL+'/access-policy',policy,H('LeadInvestigator'));assert status==200
                assert not first.done()
            finally:release.set()
            status,data=first.result(timeout=3);assert status==200 and data==raw
        status,_=request('GET',endpoint);assert status==403
    finally:release.set();server.should_exit=True;thread.join(timeout=3);sock.close()
    assert not thread.is_alive()
