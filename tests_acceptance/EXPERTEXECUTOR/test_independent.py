"""Independent subprocess supervision tests; all providers scripted, never remote."""
import json
import os
from pathlib import Path
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from research.expert_executor import executor as e
from research.expert_bridge.protocol import Bridge
from research.expert_meeting.machine import Meeting, canonical, digest, verify_snapshot
from research.expert_group.engine import ROLES


def setup(clock=None):
    kw={} if clock is None else {'clock':clock}
    meeting=Meeting(**kw);bridge=Bridge(meeting,**kw);executor=e.Executor(bridge)
    meeting.act({'type':'start_round'})
    return meeting,bridge,executor


def fake(monkeypatch,script):
    monkeypatch.setattr(e,'_command',lambda:[sys.executable,'-c',script])


def launch(executor):
    errors=[]
    def work():
        try:executor.run_turn(ROLES[0])
        except BaseException as exc:errors.append(exc)
    thread=threading.Thread(target=work);thread.start();return thread,errors


def wait(predicate):
    end=time.monotonic()+5
    while not predicate():
        if time.monotonic()>end:raise AssertionError('bounded test wait exceeded')
        time.sleep(.01)


def stopped(pid):
    try:return Path(f'/proc/{pid}/stat').read_text().split()[2]=='Z'
    except FileNotFoundError:return True


def chain(events):
    previous='0'*64
    for index,event in enumerate(events,1):
        assert event['seq']==index and event['previousSha256']==previous
        assert digest({k:v for k,v in event.items() if k!='sha256'})==event['sha256']
        previous=event['sha256']


@pytest.mark.parametrize('fault_phase',['issued','scripted_model_requested','scripted_model_response','tool_completed','done_awaiting_exit','exit_zero_acceptance_attempt'])
def test_bridge_audit_failure_marks_executor_receipt_incomplete(monkeypatch,fault_phase):
    meeting,bridge,executor=setup()
    record=bridge._record
    def broken(session,phase,**fields):
        if phase==fault_phase:raise OSError('SYNTHETIC_BRIDGE_AUDIT_FAILURE')
        return record(session,phase,**fields)
    monkeypatch.setattr(bridge,'_record',broken)
    with pytest.raises(e.ExecutionError):executor.run_turn(ROLES[0])
    receipt=executor.receipt()
    assert receipt['bridgeAudit']['auditComplete'] is False
    assert receipt['receiptComplete'] is False, 'top receipt completeness masks Bridge audit failure'
    assert all(run['receiptComplete'] is False for run in receipt['runs'])
    assert not meeting.snapshot()['rounds'][0]['responses']


def test_actual_pi_four_processes_keep_layers_and_shared_budget(monkeypatch):
    import socket
    import research.expert_group.engine as engine
    def forbidden(*args,**kwargs):pytest.fail('network/provider forbidden')
    monkeypatch.setattr(socket.socket,'connect',forbidden);monkeypatch.setattr(engine,'_remote',forbidden)
    meeting,bridge,executor=setup()
    for round_ in range(2):
        if round_:meeting.act({'type':'start_round'})
        for role in ROLES:assert executor.run_turn(role)['status']=='completed_unverified'
    receipt=executor.receipt()
    assert len(receipt['runs'])==4 and len({r['pid'] for r in receipt['runs']})==4
    assert all(r['leaderReaped'] and r['groupKillSent'] and r['exitObserved']==0 and stopped(r['pid']) for r in receipt['runs'])
    assert sum(s['modelAttempts'] for s in receipt['bridgeAudit']['sessions'])==12
    assert sum(s['toolCalls'] for s in receipt['bridgeAudit']['sessions'])==8
    assert receipt['realDeepSeekExecuted'] is False and receipt['authenticityVerified'] is False
    assert receipt['bridgeAudit']['realPi'] is False
    contexts=[r for r in receipt['runtimeEvents'] if r['phase']=='context_written_to_pipe']
    assert [r['previousOpinionCount'] for r in contexts]==[0,0,2,2]
    assert contexts[2]['contextDigest']==contexts[3]['contextDigest']!=contexts[0]['contextDigest']
    chain(receipt['runtimeEvents']);chain(receipt['bridgeAudit']['events'])
    assert verify_snapshot(canonical(receipt['meetingSnapshot']))['phase']=='completed_unverified'
    receipt['runs'].clear();assert len(executor.receipt()['runs'])==4


@pytest.mark.parametrize('phase',['spawn_attempt','process_started','context_written_to_pipe','done_received','exit_zero_observed'])
def test_runtime_audit_faults_never_publish_opinion(monkeypatch,phase):
    meeting,bridge,executor=setup();record=executor._record
    def broken(run,current,**values):
        if current==phase:raise OSError('SYNTHETIC_RECEIPT_FAILURE')
        return record(run,current,**values)
    monkeypatch.setattr(executor,'_record',broken)
    with pytest.raises(e.ExecutionError):executor.run_turn(ROLES[0])
    receipt=executor.receipt();assert not meeting.snapshot()['rounds'][0]['responses']
    assert receipt['receiptComplete'] is False and receipt['runs'][0]['status']=='not_accepted'
    run=receipt['runs'][0]
    if run['processStarted']:assert run['leaderReaped'] and stopped(run['pid'])


@pytest.mark.parametrize('tail',['partial','\\x00','{"op":"model"}\\n'])
def test_done_plus_trailing_output_rejected(monkeypatch,tail):
    real=e._command()
    wrapper=f'import subprocess,sys;p=subprocess.Popen({real!r},stdin=sys.stdin,stdout=subprocess.PIPE)\nfor line in p.stdout:\n sys.stdout.buffer.write(line);sys.stdout.buffer.flush()\np.wait()\nsys.stdout.write({tail!r});sys.stdout.flush()'
    fake(monkeypatch,wrapper);meeting,bridge,executor=setup()
    with pytest.raises(e.ExecutionError):executor.run_turn(ROLES[0])
    assert not meeting.snapshot()['rounds'][0]['responses']
    assert executor.receipt()['runs'][0]['leaderReaped']


def test_done_without_exit_stays_pending_until_cancel(monkeypatch,tmp_path):
    real=e._command();ready=tmp_path/'done'
    wrapper=f'import subprocess,sys,time,pathlib;p=subprocess.Popen({real!r},stdin=sys.stdin,stdout=subprocess.PIPE)\nfor line in p.stdout:\n sys.stdout.buffer.write(line);sys.stdout.buffer.flush()\np.wait()\npathlib.Path({str(ready)!r}).write_text("done");time.sleep(60)'
    fake(monkeypatch,wrapper);meeting,bridge,executor=setup();thread,errors=launch(executor)
    try:
        wait(ready.exists);assert not meeting.snapshot()['rounds'][0]['responses']
        with pytest.raises(e.ExecutionError,match='receipt_while_running'):executor.receipt()
    finally:executor.cancel();thread.join(5)
    assert not thread.is_alive() and errors
    assert executor.receipt()['runs'][0]['leaderReaped']


def test_waitid_keeps_leader_owned_until_cleanup(monkeypatch):
    meeting,bridge,executor=setup();cleanup=e._cleanup;observed=[]
    def inspect(proc):
        status=os.waitid(os.P_PID,proc.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT)
        assert status is not None and status.si_pid==proc.pid
        assert Path(f'/proc/{proc.pid}').exists()
        observed.append(proc.pid)
        return cleanup(proc)
    monkeypatch.setattr(e,'_cleanup',inspect)
    result=executor.run_turn(ROLES[0])
    assert observed==[result['pid']]
    with pytest.raises(ChildProcessError):os.waitpid(result['pid'],os.WNOHANG)


def test_group_descendant_cleanup_after_normal_leader_exit(monkeypatch,tmp_path):
    real=e._command();pidfile=tmp_path/'descendant'
    wrapper=f'import subprocess,sys,pathlib;p=subprocess.Popen({real!r},stdin=sys.stdin,stdout=subprocess.PIPE)\nfor line in p.stdout:\n sys.stdout.buffer.write(line);sys.stdout.buffer.flush()\np.wait()\nchild=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"],stdout=subprocess.DEVNULL,stdin=subprocess.DEVNULL);pathlib.Path({str(pidfile)!r}).write_text(str(child.pid))'
    fake(monkeypatch,wrapper);meeting,bridge,executor=setup()
    result=executor.run_turn(ROLES[0]);child=int(pidfile.read_text());wait(lambda:stopped(child))
    assert result['groupKillSent'] and result['leaderReaped']


@pytest.mark.parametrize('mode',['silent','eof','backpressure'])
def test_deadline_cleans_process_and_fds(monkeypatch,tmp_path,mode):
    now=[0.0];ready=tmp_path/'ready'
    fake(monkeypatch,f'import os,time,pathlib;pathlib.Path({str(ready)!r}).write_text("ready");'+('os.close(1);' if mode=='eof' else '')+'time.sleep(60)')
    meeting,bridge,executor=setup(clock=lambda:now[0]);before=len(os.listdir('/proc/self/fd'))
    if mode=='backpressure':
        write=executor._write
        monkeypatch.setattr(executor,'_write',lambda proc,ticket,value:write(proc,ticket,{'padding':'x'*240000}))
    thread,errors=launch(executor)
    try:wait(ready.exists);now[0]=120;thread.join(5)
    finally:
        if thread.is_alive():executor.cancel();thread.join(5)
    assert not thread.is_alive() and errors
    assert len(os.listdir('/proc/self/fd'))==before
    assert executor.receipt()['runs'][0]['leaderReaped']


def test_synthetic_environment_secrets_do_not_reach_child(monkeypatch,tmp_path):
    target=tmp_path/'env.json'
    for name in ['DEEPSEEK_API_KEY','OPENAI_API_KEY','NODE_OPTIONS','HTTPS_PROXY','HOME']:monkeypatch.setenv(name,'SYNTHETIC_NO_REAL_SECRET')
    fake(monkeypatch,f'import os,json,pathlib;pathlib.Path({str(target)!r}).write_text(json.dumps(dict(os.environ)));raise SystemExit(9)')
    meeting,bridge,executor=setup()
    with pytest.raises(e.ExecutionError):executor.run_turn(ROLES[0])
    env=json.loads(target.read_text());assert set(env)<={'PATH','LANG','LC_CTYPE'}
    assert 'SYNTHETIC_NO_REAL_SECRET' not in target.read_text()


def test_scripted_model_budget_fails_before_fifth_response(monkeypatch):
    calls=[]
    def repeating(step,packet,candidate):
        calls.append(step)
        return {'role':'assistant','content':None,'tool_calls':[{'id':f'read_{step}','type':'function','function':{'name':'read_packet','arguments':'{}'}}]}
    monkeypatch.setattr(e,'_fixture',repeating)
    meeting,bridge,executor=setup()
    with pytest.raises(e.ExecutionError):executor.run_turn(ROLES[0])
    assert calls==[1,2,3,4]
    receipt=executor.receipt();assert receipt['bridgeAudit']['sessions'][0]['modelAttempts']==4
    assert not meeting.snapshot()['rounds'][0]['responses']
    assert receipt['runs'][0]['leaderReaped']


def test_receipt_failure_remains_sticky_across_repeated_reads(monkeypatch):
    meeting,bridge,executor=setup();original=bridge._record
    def broken(session,phase,**fields):
        if phase=='tool_completed':raise OSError('SYNTHETIC')
        return original(session,phase,**fields)
    monkeypatch.setattr(bridge,'_record',broken)
    with pytest.raises(e.ExecutionError):executor.run_turn(ROLES[0])
    monkeypatch.setattr(bridge,'_record',original)
    for _ in range(3):assert executor.receipt()['receiptComplete'] is False


def test_cancel_before_spawn_has_no_process_or_opinion():
    meeting,bridge,executor=setup();executor.cancel()
    with pytest.raises(e.ExecutionError):executor.run_turn(ROLES[0])
    assert executor.receipt()['runs']==[]
    assert not meeting.snapshot()['rounds'][0]['responses']
