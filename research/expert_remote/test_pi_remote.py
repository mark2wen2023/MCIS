import asyncio
import os
import socket
import sys
import threading
import time
import pytest
from research.expert_meeting.machine import Meeting, canonical
from research.expert_bridge.protocol import Bridge
from research.expert_executor.executor import Executor, ExecutionError
from research.expert_group.engine import ROLES
from research.expert_remote import isolated
from research.expert_remote.adapter import validate_receipt
from research.expert_remote.transport import TransportError


@pytest.fixture(autouse=True)
def forbid_legacy_and_network(monkeypatch):
    def forbidden(*a,**kw):raise AssertionError('forbidden real network/legacy/scripted path')
    import research.expert_group.engine as engine
    import research.expert_executor.executor as executor
    monkeypatch.setattr(engine,'_remote',forbidden)
    monkeypatch.setattr(executor,'_fixture',forbidden)
    monkeypatch.setattr(socket.socket,'connect',forbidden)


def executor():
    m=Meeting(provider_mode='remote');b=Bridge(m);return m,b,Executor(b,provider_mode='remote_mock')


def test_actual_pi_two_rounds_isolated_mock_http_never_claims_real():
    m,b,x=executor()
    for _ in range(2):
        m.act({'type':'start_round'})
        for role in ROLES:x.run_turn(role)
    r=x.receipt();p=validate_receipt(canonical(r['providerReceipt']))
    assert r['schemaVersion']==2 and r['transportMocked'] and not r['realDeepSeekExecuted']
    assert r['receiptComplete'] and len(p['attempts'])==12
    assert all(s['modelAttempts']==3 and s['toolCalls']==2 for s in r['bridgeAudit']['sessions'])
    assert len(r['runs'])==4 and all(s['status']=='completed_unverified' and s['leaderReaped'] for s in r['runs'])
    assert all(a['worker']=={'processStarted':True,'leaderReaped':True,'exitObserved':0,'transportMocked':True} for a in p['attempts'])
    rows=[e for e in r['runtimeEvents'] if e['phase']=='context_written_to_pipe']
    assert [e['previousOpinionCount'] for e in rows]==[0,0,2,2]
    assert rows[0]['contextDigest']==rows[1]['contextDigest'] and rows[2]['contextDigest']==rows[3]['contextDigest']
    actions=[e['action']['type'] for e in r['meetingSnapshot']['events']]
    assert actions.count('submit_provider_response')==4 and 'submit_simulated' not in actions


def test_modes_require_explicit_matching_bridge_and_credentials():
    with pytest.raises(ExecutionError):Executor(Bridge(Meeting()),provider_mode='remote_mock')
    with pytest.raises(ExecutionError):Executor(Bridge(Meeting(provider_mode='remote')))
    with pytest.raises(ValueError):Executor(Bridge(Meeting(provider_mode='remote')),provider_mode='remote')


def sleepy(monkeypatch):
    monkeypatch.setattr(isolated,'_command',lambda mocked:[sys.executable,'-c','import time; time.sleep(30)'])
    seen=[];original=isolated.subprocess.Popen
    def capture(*a,**kw):
        proc=original(*a,**kw);seen.append((proc,kw));return proc
    monkeypatch.setattr(isolated.subprocess,'Popen',capture)
    return seen


def test_hard_worker_deadline_reaps_without_cooperative_transport(monkeypatch):
    seen=sleepy(monkeypatch);started=time.monotonic()
    with pytest.raises(TransportError) as caught:
        asyncio.run(isolated.request([],[],key='synthetic',deadline=started+.15,mocked=True))
    assert time.monotonic()-started<2 and caught.value.dispatched
    assert caught.value.worker['leaderReaped'] and seen[0][0].returncode is not None
    assert 'synthetic' not in str(caught.value) and 'synthetic' not in str(seen[0][0].args)
    assert set(seen[0][1]['env'])=={'PATH','LANG'}


def test_cancel_inflight_reaps_provider_and_pi_retains_unknown(monkeypatch):
    seen=sleepy(monkeypatch);m,b,x=executor();m.act({'type':'start_round'});errors=[]
    def run():
        try:x.run_turn(ROLES[0])
        except ExecutionError:errors.append(1)
    thread=threading.Thread(target=run);thread.start()
    until=time.monotonic()+3
    while len(seen)<2 and time.monotonic()<until:time.sleep(.01)
    assert len(seen)==2
    x.cancel();thread.join(3)
    assert not thread.is_alive() and errors==[1]
    r=x.receipt();assert r['runs'][0]['status']=='unknown' and not r['realDeepSeekExecuted']
    assert r['providerReceipt']['attempts'][0]['status']=='unknown'
    assert all(proc.returncode is not None for proc,_ in seen)
    assert r['runs'][0]['leaderReaped'] and r['providerReceipt']['attempts'][0]['worker']['leaderReaped']
    assert m.snapshot()['phase']=='stopped_by_operator'


def test_parent_old_turn_deadline_interrupts_provider_worker(monkeypatch):
    seen=sleepy(monkeypatch);now=[0.0];m=Meeting(provider_mode='remote',clock=lambda:now[0]);b=Bridge(m,clock=lambda:now[0]);x=Executor(b,provider_mode='remote_mock');m.act({'type':'start_round'})
    errors=[]
    def run():
        try:x.run_turn(ROLES[0])
        except ExecutionError:errors.append(1)
    t=threading.Thread(target=run);t.start();until=time.monotonic()+3
    while len(seen)<2 and time.monotonic()<until:time.sleep(.01)
    assert len(seen)==2;now[0]=120;t.join(3)
    assert not t.is_alive() and errors==[1] and all(p.returncode is not None for p,_ in seen)
    assert x.receipt()['providerReceipt']['attempts'][0]['status']=='unknown'


def test_wrong_reserved_request_never_starts_worker():
    from research.expert_remote.adapter import Adapter,AdapterError
    m=Meeting(provider_mode='remote');b=Bridge(m);a=Adapter(b,key='synthetic',enabled=True,transport_mode='remote_mock')
    m.act({'type':'start_round'});t=b.issue(ROLES[0])['ticketId'];request=b.from_runner(t,{'op':'model'});request['messages']=[]
    with pytest.raises(AdapterError):asyncio.run(a.dispatch(t,reserved_request=request))
    assert a.receipt()['attempts']==[]


@pytest.mark.parametrize('result',[None,{}, {'assistant':{},'responseMeta':{},'identityVerified':True}, {'assistant':{'role':'assistant','content':'synthetic'},'responseMeta':{},'identityVerified':False}])
def test_malformed_worker_result_preserves_process_observation(monkeypatch,result):
    import json
    output=json.dumps({'ok':True,'transportMocked':True,'result':result})
    code='import sys; sys.stdin.buffer.read(); sys.stdout.write('+repr(output)+')'
    monkeypatch.setattr(isolated,'_command',lambda mocked:[sys.executable,'-c',code])
    with pytest.raises(TransportError) as caught:
        asyncio.run(isolated.request([],[],key='synthetic',deadline=time.monotonic()+2,mocked=True))
    assert caught.value.dispatched and caught.value.worker['processStarted'] and caught.value.worker['leaderReaped']
    assert caught.value.worker['exitObserved']==0
