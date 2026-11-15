"""Real fixed local fixture processes; never Pi/provider dispatch authorization."""
import hashlib
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid
from research.expert_budget.ledger import Ledger
from research.expert_group.packet import PACKET_SHA256
from . import ownership

FIXTURE = Path(__file__).with_name('fixture.py')
FIXTURE_SHA256 = 'cf22222c56c619a5db44fda83e1a93df8fe1822dcecb602e7a8c378ce545db8c'


class WorkerError(ValueError):
    pass


class LocalWorker:
    def __init__(self, path):
        ownership.require_support()
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise WorkerError('existing_ledger_no_resume') from None
        os.close(fd)
        self.ledger = Ledger(path)
        self.meeting = str(uuid.uuid4())
        self.ledger.create(self.meeting, packet_sha256=PACKET_SHA256)
        self._run_lock = threading.Lock()
        self._cancel = threading.Event()
        self._blocked = False
        self._unresolved_process = None

    def cancel(self):
        # Request only: caller cannot claim termination until run returns observations.
        self._cancel.set()
        return {'stopRequested': True, 'terminationConfirmed': False}

    def run(self, role, round_number, *, fixture='ok', timeout=1.0):
        if fixture not in ('ok', 'fail', 'wait') or type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 5:
            raise WorkerError('fixture_or_timeout')
        if not self._run_lock.acquire(blocking=False):
            raise WorkerError('another_run_active')
        proc = None
        report = {'attemptId': str(uuid.uuid4()), 'pid': None, 'processStarted': False,
                  'exitObserved': None, 'leaderReaped': False, 'groupTerminationVerified': False,
                  'status': 'unknown', 'ledgerOutcome': 'unresolved', 'realModelExecuted': False,
                  'piExecuted': False, 'fixtureSha256': FIXTURE_SHA256}
        try:
            if self._blocked or self._cancel.is_set():
                raise WorkerError('blocked')
            ownership.require_support()
            if hashlib.sha256(FIXTURE.read_bytes()).hexdigest() != FIXTURE_SHA256:
                raise WorkerError('fixture_pin')
            # A failed/unknown reservation never reaches Popen and is never retried.
            try:
                self.ledger.reserve(self.meeting, report['attemptId'], role=role, round_number=round_number)
            except Exception:
                self._blocked = True
                raise WorkerError('reservation_unresolved_no_spawn') from None
            deadline = time.monotonic() + timeout
            reason = 'unknown'
            data = b''
            try:
                if self._cancel.is_set():
                    reason = 'cancelled'
                else:
                    proc = subprocess.Popen([sys.executable, '-I', str(FIXTURE), fixture],
                                            env={'LANG': 'C.UTF-8'}, cwd=FIXTURE.parent,
                                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                            stderr=subprocess.DEVNULL, start_new_session=True, bufsize=0)
                    report.update(pid=proc.pid, processStarted=True)
                    os.set_blocking(proc.stdout.fileno(), False)
                    while True:
                        if self._cancel.is_set():
                            reason = 'cancelled'; break
                        if time.monotonic() >= deadline:
                            reason = 'timed_out'; break
                        try: chunk = os.read(proc.stdout.fileno(), 128)
                        except BlockingIOError: chunk = b''
                        data += chunk
                        if len(data) > 128:
                            reason = 'output_limit'; break
                        if ownership.observe(proc) is not None:
                            reason = 'exited'; break
                        time.sleep(.005)
            except Exception:
                reason = 'process_unknown'
            finally:
                if proc is not None:
                    try:
                        # Exactly one cleanup attempt. No poll/wait/communicate competing reaper.
                        code = ownership.cleanup(proc)
                        report.update(exitObserved=code, leaderReaped=True)
                        try: data += os.read(proc.stdout.fileno(), 129)
                        except BlockingIOError: pass
                    except Exception:
                        reason = 'ownership_or_cleanup_unknown'
                        # Retain object; do not trigger Popen destructor's competing reap.
                        self._unresolved_process = proc
                    finally:
                        proc.stdout.close()
            if self._cancel.is_set(): reason = 'cancelled'
            elif time.monotonic() >= deadline and reason == 'exited': reason = 'timed_out'
            accepted = (reason == 'exited' and report['leaderReaped'] and
                        report['exitObserved'] == 0 and data == b'MCIS_LOCAL_FIXTURE_OK\n')
            try:
                if accepted:
                    self.ledger.settle(self.meeting, report['attemptId'], outcome='received_unverified')
                    report.update(status='completed_local_fixture', ledgerOutcome='received_unverified')
                else:
                    self._blocked = True
                    self.ledger.stop(self.meeting)
                    report.update(status=reason if reason != 'exited' else 'rejected_exit_or_output', ledgerOutcome='unknown')
            except Exception:
                self._blocked = True
                report.update(status='persistence_unknown', ledgerOutcome='unresolved')
                # Do not retry or stop-write after uncertain commit.
            if self._cancel.is_set() and report['status'] == 'completed_local_fixture':
                self._blocked = True
                # Process completion observed but caller stopped while settlement committed.
                report['status'] = 'stopped_after_local_completion'
            return report
        finally:
            self._run_lock.release()
