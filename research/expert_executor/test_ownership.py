import asyncio
import os
import signal
import subprocess
import sys
import time
import pytest
from research.expert_executor import ownership
from research.expert_remote import isolated
from research.expert_remote.transport import TransportError
from research.expert_meeting.machine import Meeting
from research.expert_bridge.protocol import Bridge
from research.expert_executor.executor import Executor, ExecutionError
from research.expert_group.engine import ROLES


def test_ignored_sigchld_refuses_worker_before_spawn(monkeypatch):
    monkeypatch.setattr(signal,'getsignal',lambda _:signal.SIG_IGN)
    def no(*a,**k):raise AssertionError('must not spawn')
    monkeypatch.setattr(subprocess,'Popen',no)
    with pytest.raises(TransportError) as exc:asyncio.run(isolated.request([],[],key='synthetic',deadline=time.monotonic()+1,mocked=True))
    assert not exc.value.dispatched and not exc.value.worker['processStarted']


def test_ignored_sigchld_refuses_pi_before_spawn(monkeypatch):
    monkeypatch.setattr(signal,'getsignal',lambda _:signal.SIG_IGN)
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**k:pytest.fail('spawned'))
    m=Meeting();m.act({'type':'start_round'});x=Executor(Bridge(m))
    with pytest.raises(ExecutionError):x.run_turn(ROLES[0])
    assert not x.receipt()['runs'][0]['processStarted']


@pytest.mark.parametrize('field',['waitid','WNOWAIT','WEXITED','WNOHANG','P_PID'])
def test_missing_capability_rejects_before_spawn(monkeypatch,field):
    monkeypatch.delattr(os,field)
    with pytest.raises(ownership.OwnershipError):ownership.require_support()


def test_echild_sticky_never_kills_group(monkeypatch):
    class Proc:pid=12345;returncode=None
    p=Proc();kills=[]
    monkeypatch.setattr(os,'waitid',lambda *a:(_ for _ in ()).throw(ChildProcessError()))
    monkeypatch.setattr(os,'killpg',lambda *a:kills.append(a))
    with pytest.raises(ownership.OwnershipError):ownership.observe(p)
    with pytest.raises(ownership.OwnershipError):ownership.cleanup(p)
    assert kills==[] and p._mcis_ownership_lost


def test_external_reap_detected_before_cleanup(monkeypatch):
    p=subprocess.Popen([sys.executable,'-c','pass'],start_new_session=True)
    os.waitpid(p.pid,0) # Deliberately violate exclusive-reaper contract.
    kills=[];monkeypatch.setattr(os,'killpg',lambda *a:kills.append(a))
    with pytest.raises(ownership.OwnershipError):ownership.cleanup(p)
    assert kills==[] and p._mcis_ownership_lost
    p.returncode=0 # Test already reaped; prevent destructor probing.


def test_real_sigign_in_separate_host_rejects_before_spawn():
    code='''import asyncio,signal,time
from research.expert_remote.isolated import request
from research.expert_remote.transport import TransportError
signal.signal(signal.SIGCHLD,signal.SIG_IGN)
try: asyncio.run(request([],[],key="synthetic",deadline=time.monotonic()+1,mocked=True))
except TransportError as e:
 assert not e.dispatched and not e.worker["processStarted"]
else: raise AssertionError("spawn allowed")
'''
    result=subprocess.run([sys.executable,'-c',code],capture_output=True,timeout=3)
    assert result.returncode==0


@pytest.mark.parametrize('failure',[NotImplementedError(),OSError(38,'not implemented'),None])
def test_unusable_waitid_refuses_before_worker_spawn(monkeypatch,failure):
    def wait(*args):
        if failure is not None:raise failure
        return None
    monkeypatch.setattr(os,'waitid',wait)
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**k:pytest.fail('spawned without waitid'))
    with pytest.raises(TransportError) as exc:
        asyncio.run(isolated.request([],[],key='synthetic',deadline=time.monotonic()+1,mocked=True))
    assert not exc.value.dispatched and not exc.value.worker['processStarted']
