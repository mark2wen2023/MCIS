"""Actual fixed-worker handshake through RequestBudget, never real provider dispatch."""
import copy
import hashlib
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import uuid
from . import ownership
from research.expert_budget.request_budget import RequestBudget
from research.expert_budget.host_protocol import HostModelProtocol
from research.expert_budget.ledger import ROLES
from research.expert_group.packet import PACKET_SHA256, _digest

FIXTURE = Path(__file__).with_name('request_fixture.py')
PIN = '5b4d4ccdef9770e79be6c4ddbf5569aa60602a7fc5fc9150f2f86055251b88f1'


class HandshakeError(ValueError):
    pass


class RequestWorker:
    def __init__(self, path):
        ownership.require_support()
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        self.budget = RequestBudget(path)
        self.meeting = str(uuid.uuid4())
        self.budget.create(self.meeting, PACKET_SHA256)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._blocked = False
        self._runs = []
        self._unresolved = None

    def cancel(self):
        self._stop.set()
        return {'stopRequested': True, 'terminationConfirmed': False}

    def run_role(self, role, *, mode='two', timeout=1.0):
        if role not in ROLES or mode not in ('two','three','duplicate','unknown') or type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0 < timeout <= 5:
            raise HandshakeError('configuration')
        if not self._lock.acquire(False): raise HandshakeError('busy')
        proc = None
        try:
            if self._blocked or self._stop.is_set(): raise HandshakeError('blocked')
            if any(r['role']==role for r in self._runs): raise HandshakeError('role_already_attempted')
            ownership.require_support()
            if hashlib.sha256(FIXTURE.read_bytes()).hexdigest()!=PIN: raise HandshakeError('fixture_pin')
            ticket = str(uuid.uuid4())
            context = _digest({'packet':PACKET_SHA256,'role':role,'round':1,'fixture':PIN})
            row = {'role':role,'ticketId':ticket,'contextDigest':context,'pid':None,'grants':0,
                   'responses':0,'leaderReaped':False,'exitObserved':None,'status':'unknown'}
            self._runs.append(row)
            pending = None; done = False; buf = b''; total = 0; db_unknown = False
            deadline = time.monotonic()+timeout
            reason = 'unknown'
            try:
                protocol = HostModelProtocol(self.budget,self.meeting,ticket,role,1,context)
                proc = subprocess.Popen([sys.executable,'-I',str(FIXTURE),mode],cwd=FIXTURE.parent,
                                        env={'LANG':'C.UTF-8'},stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL,start_new_session=True,bufsize=0)
                row['pid']=proc.pid
                os.set_blocking(proc.stdout.fileno(),False)
                while True:
                    if self._stop.is_set(): reason='stopped'; break
                    if time.monotonic()>=deadline: reason='timed_out'; break
                    try: chunk=os.read(proc.stdout.fileno(),1024)
                    except BlockingIOError: chunk=b''
                    buf+=chunk; total+=len(chunk)
                    if total>2048: raise HandshakeError('output_budget')
                    while b'\n' in buf:
                        line,buf=buf.split(b'\n',1)
                        if done: raise HandshakeError('after_done')
                        if re.fullmatch(rb'REQUEST [1-3]',line):
                            if pending: raise HandshakeError('pending')
                            n=int(line[-1:]); request=f'{ticket}:model:{n}'
                            try: reservation=protocol.request({'op':'model','requestId':request})
                            except Exception: db_unknown=True; raise
                            if not reservation['newReservation']:
                                reason=reservation['status']; raise HandshakeError(reason)
                            pending=request
                            if self._stop.is_set() or time.monotonic()>=deadline:
                                reason='stopped_before_grant'; raise HandshakeError(reason)
                            # Fixed tiny message, at most two grants. No unbounded pipe write.
                            if os.write(proc.stdin.fileno(),f'GRANT {n}\n'.encode())!=8:
                                raise HandshakeError('grant_write')
                            row['grants']+=1
                        elif re.fullmatch(rb'RESPONSE [1-3]',line):
                            request=f'{ticket}:model:{int(line[-1:])}'
                            if pending!=request: raise HandshakeError('response_binding')
                            try: protocol.received(request,hashlib.sha256(line).hexdigest())
                            except Exception: db_unknown=True; raise
                            pending=None; row['responses']+=1
                        elif line==b'DONE' and pending is None and row['responses']==2:
                            done=True
                        else: raise HandshakeError('protocol')
                    if ownership.observe(proc) is not None:
                        # Process exit alone is insufficient; drain EOF before accepting DONE.
                        if not chunk:
                            reason='exited'; break
                    time.sleep(.005)
            except Exception:
                if db_unknown: reason='persistence_unknown'
                elif reason=='unknown': reason='protocol_or_process_unknown'
            finally:
                if proc:
                    try:
                        row['exitObserved']=ownership.cleanup(proc); row['leaderReaped']=True
                    except Exception:
                        reason='ownership_or_cleanup_unknown'; self._unresolved=proc
                    finally: proc.stdin.close(); proc.stdout.close()
            if self._stop.is_set() and reason=='exited': reason='stopped'
            if time.monotonic()>=deadline and reason=='exited': reason='timed_out'
            success=reason=='exited' and done and not buf and row['leaderReaped'] and row['exitObserved']==0
            row['status']='completed_local_role_fixture' if success else reason
            if not success:
                self._blocked=True
                if not db_unknown and reason!='partial_budget_exhausted':
                    try: self.budget.stop(self.meeting)
                    except Exception: row['status']='persistence_unknown'
            return self._summary()
        finally: self._lock.release()

    def _summary(self):
        completed=[r['role'] for r in self._runs if r['status']=='completed_local_role_fixture']
        return copy.deepcopy({'meetingId':self.meeting,'runs':self._runs,'completedRoles':completed,
                              'unfinishedRoles':[r for r in ROLES if r not in completed],
                              'scope':'first_round_fixed_local_fixture_only','realModelExecuted':False,
                              'piExecuted':False,'groupTerminationVerified':False,'opinionsProduced':False})
