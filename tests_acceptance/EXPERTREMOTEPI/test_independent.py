import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import threading
import time
import pytest
from research.expert_remote import isolated
from research.expert_remote.transport import TransportError
from research.expert_remote.receipt import validate_receipt, ReceiptError
from research.expert_executor.executor import Executor, ExecutionError
from research.expert_meeting.machine import Meeting, canonical
from research.expert_bridge.protocol import Bridge
from research.expert_group.engine import ROLES

@pytest.fixture(autouse=True)
def prohibit_parent_network(monkeypatch):
    import socket
    import research.expert_group.engine as engine
    import research.expert_executor.executor as executor
    def deny(*a,**k):pytest.fail('real network/old provider forbidden')
    monkeypatch.setattr(socket.socket,'connect',deny);monkeypatch.setattr(engine,'_remote',deny)
    monkeypatch.setattr(engine,'run_group',deny);monkeypatch.setattr(executor,'_fixture',deny)


def output():return {'ok':True,'transportMocked':True,'result':{'assistant':{'role':'assistant','content':'SYNTHETIC'},'responseMeta':{k:{'status':'unknown','value':None} for k in ('id','model','usage')},'identityVerified':False}}


def worker(monkeypatch,code):monkeypatch.setattr(isolated,'_command',lambda mocked:[sys.executable,'-c',code])
def run_worker(**kw):return asyncio.run(isolated.request([],[],key='SYNTHETIC_NOT_CREDENTIAL',deadline=time.monotonic()+1,mocked=True,**kw))


@pytest.mark.parametrize('kind',['null','missing','meta','identity','mode','trailing','bad_utf8'])
def test_malformed_worker_rejected_and_actual_cleanup_observed(monkeypatch,kind):
    value=output()
    if kind=='null':value['result']=None
    elif kind=='missing':del value['result']['assistant']
    elif kind=='meta':value['result']['responseMeta']={}
    elif kind=='identity':value['result']['identityVerified']=True
    elif kind=='mode':value['transportMocked']=False
    raw=json.dumps(value).encode()+ (b'junk' if kind=='trailing' else b'')
    if kind=='bad_utf8':raw=b'\xff'
    worker(monkeypatch,f'import sys;sys.stdin.buffer.read();sys.stdout.buffer.write({raw!r});sys.stdout.flush()')
    before=len(os.listdir('/proc/self/fd'))
    with pytest.raises(TransportError) as caught:run_worker()
    assert caught.value.dispatched and caught.value.worker=={'processStarted':True,'leaderReaped':True,'exitObserved':0,'transportMocked':True}
    assert len(os.listdir('/proc/self/fd'))==before


@pytest.mark.parametrize('behavior',['silent','eof','valid_hang','backpressure'])
def test_hard_deadline_even_when_worker_uncooperative(monkeypatch,behavior):
    prefix='import os,sys,time;'
    if behavior=='eof':prefix+='os.close(1);'
    if behavior=='valid_hang':prefix+=f'sys.stdin.buffer.read();print({json.dumps(output())!r},flush=True);'
    worker(monkeypatch,prefix+'time.sleep(60)')
    before=len(os.listdir('/proc/self/fd'));start=time.monotonic()
    messages=[{'role':'user','content':'x'*240000}] if behavior=='backpressure' else []
    with pytest.raises(TransportError) as error:asyncio.run(isolated.request(messages,[],key='SYNTHETIC',deadline=start+.15,mocked=True))
    assert time.monotonic()-start<2 and error.value.worker['leaderReaped']
    assert error.value.dispatched and len(os.listdir('/proc/self/fd'))==before


def test_worker_descendant_is_killed_before_success(monkeypatch,tmp_path):
    pidfile=tmp_path/'pid'
    script=f'import subprocess,sys,pathlib;sys.stdin.buffer.read();p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL);pathlib.Path({str(pidfile)!r}).write_text(str(p.pid));print({json.dumps(output())!r},flush=True)'
    worker(monkeypatch,script);result=run_worker();pid=int(pidfile.read_text())
    deadline=time.monotonic()+2
    while Path(f'/proc/{pid}/stat').exists() and Path(f'/proc/{pid}/stat').read_text().split()[2]!='Z':
        assert time.monotonic()<deadline;time.sleep(.01)
    assert result['worker']['leaderReaped'] and result['worker']['exitObserved']==0


def test_actual_mock_http_two_rounds_never_claims_real_and_reserved_once():
    meeting=Meeting(provider_mode='remote');bridge=Bridge(meeting);executor=Executor(bridge,provider_mode='remote_mock')
    for _ in range(2):
        meeting.act({'type':'start_round'})
        for role in ROLES:executor.run_turn(role)
    receipt=executor.receipt();validate_receipt(canonical(receipt))
    assert receipt['transportMocked'] is True and receipt['realDeepSeekExecuted'] is False
    assert len(receipt['runs'])==4 and len(receipt['providerReceipt']['attempts'])==12
    assert sum(s['modelAttempts'] for s in receipt['bridgeAudit']['sessions'])==12
    assert sum(s['toolCalls'] for s in receipt['bridgeAudit']['sessions'])==8
    assert all(a['worker']['transportMocked'] and a['worker']['leaderReaped'] for a in receipt['providerReceipt']['attempts'])
    for row in receipt['providerReceipt']['attempts']:assert row['responseMeta']['model']['value']=='MOCK-NOT-DEEPSEEK'
    assert [e['previousOpinionCount'] for e in receipt['runtimeEvents'] if e['phase']=='context_written_to_pipe']==[0,0,2,2]
    assert all(not r['realDeepSeekExecuted'] for r in receipt['runs'])
    for field in ['realDeepSeekExecuted','transportMocked']:
        bad=deepcopy(receipt);bad[field]=not bad[field]
        with pytest.raises(ReceiptError):validate_receipt(canonical(bad))
    actions=[e['action']['type'] for e in receipt['meetingSnapshot']['events']]
    assert actions.count('submit_provider_response')==4 and 'submit_simulated' not in actions


@pytest.mark.parametrize('stop',['cancel','old_deadline'])
def test_inflight_worker_pi_cleanup_unknown_partial_receipt(monkeypatch,tmp_path,stop):
    ready=tmp_path/'ready'
    worker(monkeypatch,f'import pathlib,time;pathlib.Path({str(ready)!r}).write_text("ready");time.sleep(60)')
    now=[0.0];meeting=Meeting(provider_mode='remote',clock=lambda:now[0]);bridge=Bridge(meeting,clock=lambda:now[0]);executor=Executor(bridge,provider_mode='remote_mock');meeting.act({'type':'start_round'})
    errors=[];before=len(os.listdir('/proc/self/fd'))
    def work():
        try:executor.run_turn(ROLES[0])
        except ExecutionError:errors.append(True)
    thread=threading.Thread(target=work);thread.start()
    try:
        end=time.monotonic()+4
        while not ready.exists():assert time.monotonic()<end;time.sleep(.01)
        if stop=='cancel':executor.cancel()
        else:now[0]=120
        thread.join(3)
    finally:
        if thread.is_alive():executor.cancel();thread.join(3)
    assert not thread.is_alive() and errors
    receipt=executor.receipt();validate_receipt(canonical(receipt))
    assert receipt['runs'][0]['status']=='unknown'
    assert receipt['runs'][0]['leaderReaped'] and receipt['providerReceipt']['attempts'][0]['worker']['leaderReaped']
    assert receipt['providerReceipt']['attempts'][0]['status']=='unknown'
    assert receipt['realDeepSeekExecuted'] is False and not meeting.snapshot()['rounds'][0]['responses']
    assert len(os.listdir('/proc/self/fd'))==before


def test_modes_cannot_mix():
    with pytest.raises(ExecutionError):Executor(Bridge(Meeting()),provider_mode='remote_mock')
    with pytest.raises(ExecutionError):Executor(Bridge(Meeting(provider_mode='remote')))
    meeting=Meeting(provider_mode='remote');meeting.act({'type':'start_round'});bridge=Bridge(meeting);ticket=bridge.issue(ROLES[0])['ticketId'];request=bridge.from_runner(ticket,{'op':'model'})
    with pytest.raises(ValueError):bridge.scripted_response(ticket,request['requestId'],{'role':'assistant','content':'SYNTHETIC'})
    assert not meeting.snapshot()['rounds'][0]['responses']


def test_completed_first_role_survives_unknown_second_role(monkeypatch,tmp_path):
    meeting=Meeting(provider_mode='remote');bridge=Bridge(meeting);executor=Executor(bridge,provider_mode='remote_mock');meeting.act({'type':'start_round'})
    executor.run_turn(ROLES[0]);accepted=deepcopy(meeting.snapshot()['rounds'][0]['responses'])
    ready=tmp_path/'second-ready';worker(monkeypatch,f'import pathlib,time;pathlib.Path({str(ready)!r}).write_text("ready");time.sleep(60)')
    errors=[]
    def work():
        try:executor.run_turn(ROLES[1])
        except ExecutionError:errors.append(True)
    thread=threading.Thread(target=work);thread.start()
    try:
        end=time.monotonic()+4
        while not ready.exists():assert time.monotonic()<end;time.sleep(.01)
    finally:executor.cancel();thread.join(3)
    assert not thread.is_alive() and errors
    receipt=executor.receipt();validate_receipt(canonical(receipt))
    assert [r['status'] for r in receipt['runs']]==['completed_unverified','unknown']
    assert meeting.snapshot()['rounds'][0]['responses']==accepted
    assert len(receipt['providerReceipt']['attempts'])==4
    assert receipt['providerReceipt']['attempts'][-1]['status']=='unknown'
    assert receipt['meetingSnapshot']['state']['phase']=='stopped_by_operator'
