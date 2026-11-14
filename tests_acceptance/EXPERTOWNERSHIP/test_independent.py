import asyncio
import os
import signal
import subprocess
import sys
import time
from types import SimpleNamespace
import pytest
from research.expert_executor import ownership as own
from research.expert_executor import executor as ex
from research.expert_remote import isolated
from research.expert_remote.transport import TransportError
from research.expert_meeting.machine import Meeting
from research.expert_bridge.protocol import Bridge
from research.expert_group.engine import ROLES


@pytest.mark.parametrize('signal_value',[signal.SIG_IGN,lambda *_:None])
def test_nondefault_signal_blocks_both_launch_paths(monkeypatch,signal_value):
    monkeypatch.setattr(signal,'getsignal',lambda _:signal_value)
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**kw:pytest.fail('unexpected spawn'))
    m=Meeting();m.act({'type':'start_round'});x=ex.Executor(Bridge(m))
    with pytest.raises(ex.ExecutionError):x.run_turn(ROLES[0])
    assert x.receipt()['runs'][0]['processStarted'] is False
    with pytest.raises(TransportError) as error:asyncio.run(isolated.request([],[],key='SYNTHETIC',deadline=time.monotonic()+1,mocked=True))
    assert error.value.dispatched is False and error.value.worker['processStarted'] is False


@pytest.mark.parametrize('loss',['echild','returncode','signal_changed','pid_mismatch'])
def test_sticky_loss_never_signals_even_when_environment_recovers(monkeypatch,loss):
    proc=SimpleNamespace(pid=123456789,returncode=None);kills=[]
    monkeypatch.setattr(os,'killpg',lambda *a:kills.append(a))
    if loss=='echild':monkeypatch.setattr(os,'waitid',lambda *a:(_ for _ in ()).throw(ChildProcessError()))
    elif loss=='returncode':proc.returncode=0
    elif loss=='signal_changed':monkeypatch.setattr(signal,'getsignal',lambda _:signal.SIG_IGN)
    else:monkeypatch.setattr(os,'waitid',lambda *a:SimpleNamespace(si_pid=42))
    with pytest.raises(own.OwnershipError):own.observe(proc)
    proc.returncode=None;monkeypatch.setattr(os,'waitid',lambda *a:None);monkeypatch.setattr(signal,'getsignal',lambda _:signal.SIG_DFL)
    for _ in range(2):
        with pytest.raises(own.OwnershipError):own.cleanup(proc)
    assert kills==[] and proc._mcis_ownership_lost


@pytest.mark.parametrize('path',['pi','provider'])
def test_external_reaper_causes_unknown_incomplete_without_killpg(monkeypatch,path):
    original=subprocess.Popen;created=[];kills=[]
    def reap(*args,**kwargs):
        p=original(*args,**kwargs);os.waitpid(p.pid,0);created.append(p);return p
    monkeypatch.setattr(subprocess,'Popen',reap)
    monkeypatch.setattr(os,'killpg',lambda *args:kills.append(args))
    if path=='pi':
        monkeypatch.setattr(ex,'_command',lambda:[sys.executable,'-c','pass'])
        m=Meeting();m.act({'type':'start_round'});x=ex.Executor(Bridge(m))
        with pytest.raises(ex.ExecutionError):x.run_turn(ROLES[0])
        r=x.receipt();run=r['runs'][0]
        assert run['status']=='unknown' and not run['leaderReaped'] and not run['groupKillSent']
        assert not r['receiptComplete'] and not run['receiptComplete']
        assert not m.snapshot()['rounds'][0]['responses']
    else:
        monkeypatch.setattr(isolated,'_command',lambda mocked:[sys.executable,'-c','pass'])
        with pytest.raises(TransportError) as error:asyncio.run(isolated.request([],[],key='SYNTHETIC',deadline=time.monotonic()+1,mocked=True))
        assert error.value.dispatched and error.value.worker['processStarted']
        assert not error.value.worker['leaderReaped']
    assert kills==[] and created[0]._mcis_ownership_lost
    created[0].returncode=0 # It was actually reaped by this controlled external reaper.


def test_cleanup_rechecks_after_prior_successful_observation(monkeypatch):
    proc=SimpleNamespace(pid=123456789,returncode=None);calls=[];kills=[]
    def observed(*args):
        calls.append(args)
        if len(calls)==1:return None
        raise ChildProcessError()
    monkeypatch.setattr(os,'waitid',observed);monkeypatch.setattr(os,'killpg',lambda *a:kills.append(a))
    assert own.observe(proc) is None
    with pytest.raises(own.OwnershipError):own.cleanup(proc)
    assert len(calls)==2 and kills==[]


def test_normal_cleanup_uses_own_waitid_not_popen_wait(monkeypatch):
    p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],start_new_session=True)
    monkeypatch.setattr(p,'wait',lambda *a,**kw:pytest.fail('Popen.wait must not hide ECHILD'))
    code=own.cleanup(p)
    assert code==-signal.SIGKILL and p.returncode==code
    with pytest.raises(ChildProcessError):os.waitpid(p.pid,os.WNOHANG)


def test_normal_mock_pi_and_worker_paths_remain_operational():
    m=Meeting(provider_mode='remote');b=Bridge(m);x=ex.Executor(b,provider_mode='remote_mock');m.act({'type':'start_round'})
    result=x.run_turn(ROLES[0]);receipt=x.receipt()
    assert result['leaderReaped'] and result['status']=='completed_unverified'
    assert receipt['receiptComplete'] and receipt['realDeepSeekExecuted'] is False
    assert len(receipt['providerReceipt']['attempts'])==3
    assert all(a['worker']['leaderReaped'] for a in receipt['providerReceipt']['attempts'])


def test_worker_deadline_cleanup_regression(monkeypatch):
    monkeypatch.setattr(isolated,'_command',lambda mocked:[sys.executable,'-c','import time;time.sleep(60)'])
    before=len(os.listdir('/proc/self/fd'));start=time.monotonic()
    with pytest.raises(TransportError) as error:asyncio.run(isolated.request([],[],key='SYNTHETIC',deadline=start+.12,mocked=True))
    assert error.value.worker['leaderReaped'] and error.value.dispatched
    assert time.monotonic()-start<2 and len(os.listdir('/proc/self/fd'))==before


def test_actual_sigign_host_blocks_before_child_creation():
    script='''import asyncio,signal,time,subprocess
from research.expert_remote.isolated import request
from research.expert_remote.transport import TransportError
signal.signal(signal.SIGCHLD,signal.SIG_IGN)
subprocess.Popen=lambda *a,**k:(_ for _ in ()).throw(AssertionError("spawn"))
try:asyncio.run(request([],[],key="SYNTHETIC",deadline=time.monotonic()+1,mocked=True))
except TransportError as e:assert not e.dispatched and not e.worker["processStarted"]
else:raise AssertionError("accepted")
'''
    out=subprocess.run([sys.executable,'-c',script],capture_output=True,timeout=3)
    assert out.returncode==0,out.stderr.decode()


def test_provider_external_reap_propagates_to_composite_incomplete(monkeypatch):
    original=subprocess.Popen;kill=os.killpg;worker_pids=[];signals=[];workers=[]
    monkeypatch.setattr(isolated,'_command',lambda mocked:[sys.executable,'-c','pass'])
    def spawn(command,*args,**kwargs):
        p=original(command,*args,**kwargs)
        if command==[sys.executable,'-c','pass']:
            os.waitpid(p.pid,0);worker_pids.append(p.pid);workers.append(p)
        return p
    def guarded_kill(pid,sig):
        signals.append(pid)
        assert pid not in worker_pids,'signalled a reaped worker PID'
        return kill(pid,sig)
    monkeypatch.setattr(subprocess,'Popen',spawn);monkeypatch.setattr(os,'killpg',guarded_kill)
    m=Meeting(provider_mode='remote');b=Bridge(m);x=ex.Executor(b,provider_mode='remote_mock');m.act({'type':'start_round'})
    with pytest.raises(ex.ExecutionError):x.run_turn(ROLES[0])
    receipt=x.receipt();attempt=receipt['providerReceipt']['attempts'][0]
    assert attempt['status']=='unknown' and attempt['worker']['processStarted'] and not attempt['worker']['leaderReaped']
    assert not receipt['receiptComplete'] and receipt['runs'][0]['status']=='unknown'
    assert receipt['runs'][0]['leaderReaped'] and receipt['runs'][0]['pid'] in signals
    assert not set(worker_pids)&set(signals)
    for p in workers:p.returncode=0


@pytest.mark.parametrize('failure',[NotImplementedError(),OSError(38,'SYNTHETIC_ENOSYS')])
def test_unimplemented_waitid_refused_before_spawn(monkeypatch,failure):
    calls=[]
    monkeypatch.setattr(os,'waitid',lambda *a:(_ for _ in ()).throw(failure))
    def spawn(*a,**kw):calls.append(True);raise RuntimeError('no actual child in this fault test')
    monkeypatch.setattr(subprocess,'Popen',spawn)
    with pytest.raises(TransportError):asyncio.run(isolated.request([],[],key='SYNTHETIC',deadline=time.monotonic()+1,mocked=True))
    assert calls==[], 'waitid exists but is unsupported: child spawn was attempted'


def test_probe_unexpected_return_refuses_spawn(monkeypatch):
    seen=[]
    monkeypatch.setattr(os,'waitid',lambda *args:seen.append(args))
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**kw:pytest.fail('spawn after failed probe'))
    with pytest.raises(TransportError):asyncio.run(isolated.request([],[],key='SYNTHETIC',deadline=time.monotonic()+1,mocked=True))
    assert seen==[(os.P_PID,os.getpid(),os.WEXITED|os.WNOHANG|os.WNOWAIT)]


def test_self_probe_does_not_consume_existing_child():
    p=subprocess.Popen([sys.executable,'-c','pass'],start_new_session=True)
    end=time.monotonic()+2
    while os.waitid(os.P_PID,p.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT) is None:
        assert time.monotonic()<end;time.sleep(.01)
    own.require_support()
    assert os.waitid(os.P_PID,p.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT).si_pid==p.pid
    assert own.cleanup(p)==0
