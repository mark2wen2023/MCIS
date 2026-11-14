"""Linux Pi supervisor with explicit scripted or isolated provider modes."""
from copy import deepcopy
import asyncio
import hashlib
import json
import os
from pathlib import Path
import select
import selectors
import shutil
import signal
import subprocess
import threading

from research.expert_bridge.protocol import Bridge, ProtocolError, MAX_WIRE
from research.expert_group.engine import _fixture, _packet, load_packet
from research.expert_meeting.machine import canonical, digest

ROOT = Path(__file__).resolve().parents[1] / 'expert_group'
RUNNER = ROOT / 'pi-runner.mjs'
RUNNER_SHA = 'c826f7ac90fdb997c416505b67e9ee143cdcc56b9f32b0898eca2d7e5b7a5511'
MAX_STDOUT = 2 * 1024 * 1024
ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}


class ExecutionError(RuntimeError):
    pass


def _command():
    if os.name != 'posix' or not hasattr(os, 'WNOWAIT'): raise ExecutionError('linux_waitid_required')
    if hashlib.sha256(RUNNER.read_bytes()).hexdigest() != RUNNER_SHA: raise ExecutionError('runner_pin')
    for package in ['pi-agent-core', 'pi-ai']:
        manifest = ROOT / 'node_modules' / '@earendil-works' / package / 'package.json'
        if json.loads(manifest.read_text())['version'] != '1.5.2': raise ExecutionError('pi_version')
    node = shutil.which('node')
    if not node: raise ExecutionError('node_unavailable')
    return [node, str(RUNNER)]


def _status(proc):
    # Keep the leader unreaped, reserving its PID/PGID until owned-group cleanup.
    observed = os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
    if observed is None: return None
    if observed.si_code == os.CLD_EXITED: return observed.si_status
    return -observed.si_status


def _cleanup(proc):
    # start_new_session guarantees this is our group, not the shell's process group.
    try: os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError: pass
    code = proc.wait(timeout=5)
    return code


class Executor:
    """One active turn; cancel() is nonblocking and may be called by another thread."""
    def __init__(self, bridge: Bridge, *, provider_mode="scripted", key=None):
        if type(bridge) is not Bridge: raise ExecutionError('bridge_type')
        if provider_mode not in {'scripted','remote','remote_mock'}: raise ExecutionError('provider_mode')
        if (provider_mode == 'scripted') != (bridge.provider_mode == 'scripted'): raise ExecutionError('provider_mode_mismatch')
        self.provider_mode = provider_mode
        self._adapter = None
        if provider_mode != 'scripted':
            from research.expert_remote.adapter import Adapter
            self._adapter = Adapter(bridge,key=key if provider_mode=='remote' else 'synthetic-offline-placeholder',enabled=True,transport_mode=provider_mode)
        self.bridge = bridge
        self._cancelled = threading.Event()
        self._run_lock = threading.Lock()
        self._receipt_lock = threading.RLock()
        self._runs = []
        self._events = []
        self._packet = _packet(load_packet())
        self._receipt_complete = True

    def cancel(self):
        self._cancelled.set()
        if self._adapter is not None: self._adapter.cancel()
        return self.bridge.stop()

    def _record(self, run, phase, **values):
        with self._receipt_lock:
            if len(self._events) >= 128: raise ExecutionError('receipt_budget')
            row = {'seq': len(self._events) + 1,
                   'previousSha256': self._events[-1]['sha256'] if self._events else '0' * 64,
                   'ticketId': run['ticketId'], 'phase': phase, **values}
            row['sha256'] = digest(row)
            self._events.append(row)

    def _log(self, run, phase, **values):
        try:
            self._record(run, phase, **values)
        except Exception:
            self._receipt_complete = False
            run['receiptComplete'] = False
            raise

    def _check(self, ticket):
        if self._cancelled.is_set(): raise ExecutionError('operator_cancelled')
        self.bridge.poll(ticket)

    def _write(self, proc, ticket, value):
        raw = canonical(value) + b'\n'
        if len(raw) > MAX_WIRE: raise ExecutionError('stdin_budget')
        sent = 0
        while sent < len(raw):
            self._check(ticket)
            if _status(proc) is not None: raise ExecutionError('child_exited_before_reply')
            if not select.select([], [proc.stdin], [], .05)[1]: continue
            try: count = os.write(proc.stdin.fileno(), raw[sent:sent + 65536])
            except BlockingIOError: continue
            if count <= 0: raise ExecutionError('stdin_failed')
            sent += count

    def run_turn(self, role):
        if not self._run_lock.acquire(blocking=False): raise ExecutionError('another_turn_running')
        proc = None
        selector = None
        ticket = None
        run = None
        reaped = False
        try:
            if self._cancelled.is_set(): raise ExecutionError('operator_cancelled')
            issued = self.bridge.issue(role)
            ticket = issued['ticketId']
            run = {'ticketId': ticket, 'status': 'not_accepted', 'processStarted': False,
                   'exitObserved': None, 'groupKillSent': False, 'leaderReaped': False, 'runnerSha256': RUNNER_SHA,
                   'runtime': 'Pi1.5.2', 'providerMode': self.provider_mode, 'realDeepSeekExecuted': False, 'receiptComplete': True}
            with self._receipt_lock: self._runs.append(run)
            self._check(ticket)
            command = _command()
            self._log(run, 'spawn_attempt')
            proc = subprocess.Popen(command, cwd=ROOT, env=dict(ENV), stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                    start_new_session=True, bufsize=0)
            run.update(processStarted=True, pid=proc.pid)
            os.set_blocking(proc.stdin.fileno(), False)
            os.set_blocking(proc.stdout.fileno(), False)
            selector = selectors.DefaultSelector()
            selector.register(proc.stdout, selectors.EVENT_READ)
            self._log(run, 'process_started', pid=proc.pid)
            self._write(proc, ticket, issued['config'])
            buffer = b''
            total = 0
            messages = 0
            model_step = 0
            candidate = None
            done = False
            while True:
                self._check(ticket)
                if b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    if done: raise ExecutionError('output_after_done')
                    messages += 1
                    if messages > 32: raise ExecutionError('message_budget')
                    answer = self.bridge.from_runner(ticket, line + b'\n')
                    if answer.get('kind') in {'scripted_model_request','remote_model_request'}:
                        model_step += 1
                        if self.provider_mode == 'scripted':
                            model = _fixture(model_step, self._packet, candidate)
                            reply = self.bridge.scripted_response(ticket, answer['requestId'], model)
                        else:
                            result = asyncio.run(self._adapter.dispatch(ticket,reserved_request=answer))
                            self._check(ticket)
                            run['realDeepSeekExecuted'] = self.provider_mode == 'remote'
                            self._log(run,'provider_response_received',requestId=answer['requestId'],
                                      responseDigest=digest(result['assistant']),transportMocked=self.provider_mode=='remote_mock')
                            reply = self.bridge.provider_response(ticket,answer['requestId'],result['assistant'])
                        self._write(proc, ticket, reply)
                    elif answer.get('awaitingExit') is True:
                        done = True
                        proc.stdin.close()
                        self._log(run, 'done_received')
                    else:
                        result = answer['result']
                        if 'candidateId' in result: candidate = result['candidateId']
                        self._write(proc, ticket, answer)
                        if 'meetingContext' in result:
                            self._log(run, 'context_written_to_pipe', contextDigest=result['contextDigest'],
                                         previousOpinionCount=len(result['meetingContext']['previousRoundOpinions']))
                    continue
                # Non-reaping status check preserves ownership until killpg+wait.
                status = _status(proc)
                if status is not None:
                    code = _cleanup(proc)
                    reaped = True
                    run.update(exitObserved=code, groupKillSent=True, leaderReaped=True)
                    # Drain after group cleanup; trailing data is not silently discarded.
                    while True:
                        try: tail = os.read(proc.stdout.fileno(), 65536)
                        except BlockingIOError: break
                        if not tail: break
                        total += len(tail)
                        buffer += tail
                        if total > MAX_STDOUT or len(buffer) > MAX_WIRE: raise ExecutionError('stdout_budget')
                    if buffer:
                        if not done and b'\n' in buffer:
                            # The final done line can arrive just before process exit.
                            line, rest = buffer.split(b'\n', 1)
                            answer = self.bridge.from_runner(ticket, line + b'\n')
                            if answer != {'accepted': False, 'awaitingExit': True} or rest:
                                raise ExecutionError('unconsumed_exit_output')
                            done = True
                        else: raise ExecutionError('unconsumed_exit_output')
                    if not done or code != 0: raise ExecutionError('child_not_completed')
                    selector.close()
                    selector = None
                    if not proc.stdin.closed: proc.stdin.close()
                    proc.stdout.close()
                    self._log(run, 'exit_zero_observed', returncode=code)
                    self._check(ticket)
                    accepted = self.bridge.exited(ticket, code)
                    run['status'] = accepted['status']
                    return deepcopy(run)
                if not selector.select(.05): continue
                try: chunk = os.read(proc.stdout.fileno(), 65536)
                except BlockingIOError: continue
                if not chunk:
                    # Avoid a busy loop on persistent EOF while the child is still alive.
                    selector.unregister(proc.stdout)
                    continue
                total += len(chunk)
                buffer += chunk
                if total > MAX_STDOUT or len(buffer) > MAX_WIRE: raise ExecutionError('stdout_budget')
        except BaseException as exc:
            if isinstance(exc, KeyboardInterrupt): self._cancelled.set()
            if run is not None:
                run['errorCode'] = str(exc) if isinstance(exc, ExecutionError) else 'protocol_or_process_rejected'
                try: self._log(run, 'not_accepted', errorCode=run['errorCode'])
                except Exception: run['receiptComplete'] = False
            if ticket is not None:
                try:
                    if self._cancelled.is_set(): self.bridge.stop()
                    else: self.bridge.exited(ticket, -1)
                except Exception: pass
            if run is not None and self._adapter is not None:
                try:
                    audit=self._adapter.receipt()
                    if any(r['ticketId']==ticket and r['status']=='unknown' for r in audit['attempts']):run['status']='unknown'
                except Exception:
                    self._receipt_complete=False;run['receiptComplete']=False
            raise ExecutionError('turn_not_accepted') from None
        finally:
            try:
                try:
                    if selector is not None: selector.close()
                finally:
                    if proc is not None:
                        try:
                            if not reaped:
                                code = _cleanup(proc)
                                if run is not None: run.update(exitObserved=code, groupKillSent=True, leaderReaped=True)
                        finally:
                            if proc.stdin and not proc.stdin.closed: proc.stdin.close()
                            if proc.stdout and not proc.stdout.closed: proc.stdout.close()
            finally:
                self._run_lock.release()

    def receipt(self):
        if not self._run_lock.acquire(blocking=False): raise ExecutionError('receipt_while_running')
        try:
            with self._receipt_lock:
                bridge_audit = self.bridge.audit()
                # A composite receipt cannot be complete when its shared budget trace is not.
                if bridge_audit['auditComplete'] is not True:
                    self._receipt_complete = False
                    for run in self._runs: run['receiptComplete'] = False
                output = {'schemaVersion': 1, 'kind': 'actual_pi_scripted_provider_protocol_receipt',
                    'authenticityVerified': False, 'realDeepSeekExecuted': False,
                    'receiptComplete': self._receipt_complete,
                    'stateScope': 'meeting_and_bridge_are_scripted_protocol_state_not_process_observation',
                    'snapshotStatus': 'volatile_protocol_record_not_capability_acceptance',
                    'runs': self._runs, 'runtimeEvents': self._events, 'bridgeAudit': bridge_audit,
                    'meetingSnapshot': json.loads(self.bridge.meeting.export())}
                if self._adapter is not None:
                    provider=self._adapter.receipt()
                    if any(a['worker']['processStarted'] and not a['worker']['leaderReaped'] for a in provider['attempts']):
                        self._receipt_complete=False
                        for run in self._runs: run['receiptComplete']=False
                    for run in self._runs:
                        attempts=[r for r in provider['attempts'] if r['ticketId']==run['ticketId']]
                        run['realDeepSeekExecuted']=self.provider_mode=='remote' and any(r['status']=='received_unverified' for r in attempts)
                        sessions=[s for s in bridge_audit['sessions'] if s['ticketId']==run['ticketId']]
                        if run['status']=='completed_unverified' and (len(sessions)!=1 or len(attempts)!=sessions[0]['modelAttempts'] or not attempts or any(r['status']!='received_unverified' for r in attempts)):
                            self._receipt_complete=False;run['receiptComplete']=False
                    output.update(schemaVersion=2,kind='actual_pi_provider_protocol_receipt',
                        providerMode=self.provider_mode,transportMocked=self.provider_mode=='remote_mock',
                        realDeepSeekExecuted=any(r['realDeepSeekExecuted'] for r in self._runs),
                        receiptComplete=self._receipt_complete,providerReceipt=provider,
                        stateScope='remote_protocol_state_plus_local_process_and_transport_observations_not_identity_proof')
                return deepcopy(output)
        finally:
            self._run_lock.release()
