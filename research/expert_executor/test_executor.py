import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import pytest
from research.expert_meeting.machine import Meeting, canonical, digest, verify_snapshot
from research.expert_bridge.protocol import Bridge
from research.expert_group.engine import ROLES
import research.expert_executor.executor as module
from research.expert_executor.executor import Executor, ExecutionError


def setup(clock=None):
    kw={} if clock is None else {'clock':clock}
    m=Meeting(**kw);b=Bridge(m,**kw);x=Executor(b);m.act({'type':'start_round'});return m,b,x


def fake(monkeypatch, script):
    monkeypatch.setattr(module,'_command',lambda:[sys.executable,'-c',script])


def threaded(fn):
    errors=[]
    def run():
        try:fn()
        except BaseException as e:errors.append(e)
    t=threading.Thread(target=run);t.start();return t,errors


def wait_until(predicate):
    deadline=time.monotonic()+4
    while not predicate():
        if time.monotonic()>deadline:raise AssertionError('test condition timed out')
        time.sleep(.01)


def stopped(pid):
    p=Path(f'/proc/{pid}/stat')
    return not p.exists() or p.read_text().split()[2]=='Z'


def test_actual_pi_two_rounds_with_scripted_provider_and_shared_receipt(monkeypatch):
    import socket
    import research.expert_group.engine as engine
    def forbidden(*a,**kw):raise AssertionError('real network/provider forbidden')
    monkeypatch.setattr(socket.socket,'connect',forbidden);monkeypatch.setattr(engine,'_remote',forbidden)
    m,b,x=setup()
    for round_ in range(2):
        if round_:m.act({'type':'start_round'})
        for role in ROLES:
            out=x.run_turn(role)
            assert out['status']=='completed_unverified' and out['processStarted']
            assert out['exitObserved']==0 and out['leaderReaped'] and not out['realDeepSeekExecuted']
            assert stopped(out['pid'])
    r=x.receipt()
    assert r['realDeepSeekExecuted'] is False and len(r['runs'])==4
    assert r['meetingSnapshot']['state']['mode']=='simulation_only'
    assert verify_snapshot(canonical(r['meetingSnapshot']))['phase']=='completed_unverified'
    sessions=r['bridgeAudit']['sessions']
    assert sum(s['modelAttempts'] for s in sessions)==12 and sum(s['toolCalls'] for s in sessions)==8
    contexts=[e for e in r['runtimeEvents'] if e['phase']=='context_written_to_pipe']
    assert [e['previousOpinionCount'] for e in contexts]==[0,0,2,2]
    assert contexts[0]['contextDigest']==contexts[1]['contextDigest']
    assert contexts[2]['contextDigest']==contexts[3]['contextDigest']
    previous='0'*64
    for seq,e in enumerate(r['runtimeEvents'],1):
        assert e['seq']==seq and e['previousSha256']==previous
        assert e['sha256']==digest({k:v for k,v in e.items() if k!='sha256'});previous=e['sha256']


@pytest.mark.parametrize('script',[
    'import sys;sys.exit(7)',
    'print("not-json",flush=True)',
    'print(\'{"op":"done","text":"COMPLETED:fake"}\',flush=True)',
    'print(\'{"op":"model","op":"done"}\',flush=True)',
    'import os;os.write(1,b"x"*300000)',
    'import os;os.write(1,b"\\xff\\n")',
])
def test_fake_child_bad_output_or_exit_cannot_complete(monkeypatch,script):
    fake(monkeypatch,script);m,b,x=setup()
    with pytest.raises(ExecutionError):x.run_turn(ROLES[0])
    r=x.receipt();assert not m.snapshot()['rounds'][0]['responses']
    assert r['runs'][0]['status']=='not_accepted' and r['runs'][0]['leaderReaped']
    assert stopped(r['runs'][0]['pid'])


def test_operator_cancel_kills_owned_process_group(monkeypatch,tmp_path):
    pidfile=tmp_path/'descendant.pid'
    script=f'import subprocess,sys,time,pathlib; p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"]);pathlib.Path({str(pidfile)!r}).write_text(str(p.pid));time.sleep(60)'
    fake(monkeypatch,script);m,b,x=setup();t,errors=threaded(lambda:x.run_turn(ROLES[0]))
    wait_until(pidfile.exists)
    with pytest.raises(ExecutionError,match='receipt_while_running'):x.receipt()
    with pytest.raises(ExecutionError,match='another_turn_running'):x.run_turn(ROLES[1])
    x.cancel();t.join(4);assert not t.is_alive() and errors
    child=int(pidfile.read_text());wait_until(lambda:stopped(child))
    r=x.receipt();assert r['runs'][0]['leaderReaped'] and stopped(r['runs'][0]['pid'])
    assert m.snapshot()['phase']=='stopped_by_operator'
    with pytest.raises(ExecutionError):x.run_turn(ROLES[0])


@pytest.mark.parametrize('close_stdout',[False,True])
def test_silent_or_eof_child_is_stopped_at_deadline(monkeypatch,tmp_path,close_stdout):
    ready=tmp_path/'ready';now=[0.0]
    script=f'import os,time,pathlib;pathlib.Path({str(ready)!r}).write_text("ready");'+('os.close(1);' if close_stdout else '')+'time.sleep(60)'
    fake(monkeypatch,script);m,b,x=setup(clock=lambda:now[0]);t,errors=threaded(lambda:x.run_turn(ROLES[0]));wait_until(ready.exists);now[0]=120
    t.join(4);assert not t.is_alive() and errors
    r=x.receipt();assert r['runs'][0]['leaderReaped'] and not m.snapshot()['rounds'][0]['responses']


def test_child_environment_is_whitelisted(monkeypatch,tmp_path):
    output=tmp_path/'keys.json'
    fake(monkeypatch,f'import os,json,pathlib;pathlib.Path({str(output)!r}).write_text(json.dumps(sorted(os.environ)));raise SystemExit(3)')
    monkeypatch.setenv('DEEPSEEK_API_KEY','SYNTHETIC_NOT_A_CREDENTIAL');monkeypatch.setenv('NODE_OPTIONS','SYNTHETIC_UNSAFE_OPTION')
    m,b,x=setup()
    with pytest.raises(ExecutionError):x.run_turn(ROLES[0])
    assert set(json.loads(output.read_text())) <= {'PATH','LANG','LC_CTYPE'}


def test_spawn_failure_keeps_budget_and_no_completion(monkeypatch):
    monkeypatch.setattr(module,'_command',lambda: (_ for _ in ()).throw(ExecutionError('runtime_unavailable')))
    m,b,x=setup()
    with pytest.raises(ExecutionError):x.run_turn(ROLES[0])
    r=x.receipt();assert r['runs'][0]['processStarted'] is False
    assert m.snapshot()['allocatedTurns']==1 and not m.snapshot()['rounds'][0]['responses']


def test_repeated_failures_do_not_leak_fds(monkeypatch):
    fake(monkeypatch,'raise SystemExit(3)');before=len(os.listdir('/proc/self/fd'))
    for _ in range(6):
        m,b,x=setup()
        with pytest.raises(ExecutionError):x.run_turn(ROLES[0])
        assert not x._run_lock.locked()
    assert len(os.listdir('/proc/self/fd'))==before


def test_nonblocking_writer_cancels_when_pipe_backpressured(monkeypatch,tmp_path):
    ready=tmp_path/'ready';fake(monkeypatch,f'import pathlib,time;pathlib.Path({str(ready)!r}).write_text("r");time.sleep(60)')
    m,b,x=setup();original=x._write
    def flood(proc,ticket,value):return original(proc,ticket,{'padding':'x'*200000})
    monkeypatch.setattr(x,'_write',flood);t,errors=threaded(lambda:x.run_turn(ROLES[0]));wait_until(ready.exists);time.sleep(.05);x.cancel();t.join(4)
    assert not t.is_alive() and errors and x.receipt()['runs'][0]['leaderReaped']


def test_runtime_receipt_failure_before_parent_acceptance(monkeypatch):
    m,b,x=setup();original=x._record
    def fail(run,phase,**fields):
        if phase=='exit_zero_observed':raise OSError('simulated receipt failure')
        return original(run,phase,**fields)
    monkeypatch.setattr(x,'_record',fail)
    with pytest.raises(ExecutionError):x.run_turn(ROLES[0])
    assert not m.snapshot()['rounds'][0]['responses'] and x.receipt()['runs'][0]['status']=='not_accepted'


@pytest.mark.parametrize('extra,code',[(True,0),(False,7)])
def test_valid_pi_done_does_not_hide_extra_output_or_bad_exit(monkeypatch,extra,code):
    real=module._command()
    script=f'import subprocess,sys;p=subprocess.Popen({real!r},stdin=sys.stdin,stdout=subprocess.PIPE);\nfor line in p.stdout:\n sys.stdout.buffer.write(line);sys.stdout.buffer.flush()\np.wait()\n'+('print("unexpected trailing output",flush=True)\n' if extra else '')+f'raise SystemExit({code})'
    fake(monkeypatch,script);m,b,x=setup()
    with pytest.raises(ExecutionError):x.run_turn(ROLES[0])
    assert not m.snapshot()['rounds'][0]['responses'] and x.receipt()['runs'][0]['leaderReaped']


def test_receipt_failure_flag_stays_false_after_failure_record_succeeds(monkeypatch):
    m,b,x=setup();original=x._record
    def fail(run,phase,**fields):
        if phase=='exit_zero_observed':raise OSError('single simulated failure')
        return original(run,phase,**fields)
    monkeypatch.setattr(x,'_record',fail)
    with pytest.raises(ExecutionError):x.run_turn(ROLES[0])
    assert x.receipt()['receiptComplete'] is False


def test_upstream_bridge_audit_failure_invalidates_composite_receipt(monkeypatch):
    m,b,x=setup();original=b._record
    def fail(session,phase,**fields):
        if phase=='scripted_model_requested':raise OSError('synthetic upstream audit failure')
        return original(session,phase,**fields)
    monkeypatch.setattr(b,'_record',fail)
    with pytest.raises(ExecutionError):x.run_turn(ROLES[0])
    for _ in range(2):
        receipt=x.receipt()
        assert not receipt['bridgeAudit']['auditComplete'] and not receipt['receiptComplete']
        assert receipt['runs'] and all(not r['receiptComplete'] for r in receipt['runs'])
