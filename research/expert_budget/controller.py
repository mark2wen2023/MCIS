"""Durable observations around the existing TWO-role offline controller; never execution."""
import json
import sqlite3
import threading
from research.expert_meeting.coordination import Coordination
from research.expert_meeting.machine import digest

MAX_OBSERVATIONS=256


class ControllerError(ValueError):
    pass


class DurableCoordination:
    def __init__(self,path,*,clock):
        self.path=path;self._lock=threading.RLock();self._blocked=False
        self._gate=Coordination(clock=clock)
        # Fresh single-owner recording only. No reattach/resume API.
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
            if tables and tables!={'controller_observations'}:raise ControllerError('foreign_database')
            db.execute('CREATE TABLE IF NOT EXISTS controller_observations (seq INTEGER PRIMARY KEY, previous TEXT NOT NULL, digest TEXT NOT NULL, metadata TEXT NOT NULL)')
            if db.execute('SELECT 1 FROM controller_observations').fetchone():raise ControllerError('existing_controller_no_resume')
            self._write(db,self._metadata(self._gate.receipt()))

    def _connect(self):
        # sqlite connection context handles commit/rollback; explicit close via wrapper.
        from contextlib import contextmanager
        @contextmanager
        def connection():
            db=sqlite3.connect(self.path,timeout=5)
            try:
                db.execute('PRAGMA synchronous=FULL')
                yield db;db.commit()
            except Exception:
                db.rollback();raise
            finally:db.close()
        return connection()

    @staticmethod
    def _metadata(receipt):
        state=receipt['state']
        return {'schema':'mcis.two-role-controller-observation.v1','meetingId':state['meetingId'],
                'phase':state['phase'],'stateDigest':digest(state),
                'attempts':receipt['attempts'],'blockedReason':receipt['blockedReason'],
                'executionAuthorized':False,'modelExecutionVerified':False,
                'identityAuthenticated':False,'hardCancellationImplemented':False}

    def _write(self,db,metadata):
        previous=db.execute('SELECT seq,digest,metadata FROM controller_observations ORDER BY seq DESC LIMIT 1').fetchone()
        encoded=json.dumps(metadata,ensure_ascii=False,sort_keys=True,separators=(',',':'))
        if previous and previous[2]==encoded:return
        seq=previous[0]+1 if previous else 1
        if seq>MAX_OBSERVATIONS:raise ControllerError('observation_budget')
        prev=previous[1] if previous else '0'*64
        sha=digest({'seq':seq,'previous':prev,'metadata':metadata})
        db.execute('INSERT INTO controller_observations VALUES(?,?,?,?)',(seq,prev,sha,encoded))

    def _checkpoint(self):
        receipt=self._gate.receipt()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self._write(db,self._metadata(receipt))
        return receipt

    def _block(self):
        self._blocked=True
        try:self._gate.action({'type':'stop'})
        except Exception:pass
        # No second write/retry after an uncertain storage exception. Restart also
        # refuses the existing recording; previously saved metadata may be stale.

    def _call(self,method,*args):
        with self._lock:
            if self._blocked:raise ControllerError('controller_blocked')
            try:
                result=getattr(self._gate,method)(*args)
                receipt=self._checkpoint()
                if method=='reserve':
                    turn=receipt['state']['activeTurn']
                    current=next((r for r in receipt['attempts'] if r['attemptId']==result['attemptId']),None)
                    if receipt['blockedReason'] or not turn or turn['ticketId']!=result['ticketId'] or not current or current['outcome']!='pending':
                        raise ControllerError('reservation_expired_before_return')
                if method=='action':return receipt['state']
                return result
            except Exception:
                self._block()
                raise ControllerError('controller_blocked') from None

    def action(self,action):return self._call('action',action)
    def reserve(self,ticket_id,kind):return self._call('reserve',ticket_id,kind)
    def settle(self,attempt_id,outcome):return self._call('settle',attempt_id,outcome)

    def receipt(self):
        with self._lock:
            if self._blocked:
                return {'kind':'blocked_controller','persistenceStatus':'unknown_or_stale',
                        'executionAuthorized':False,'modelExecutionVerified':False,
                        'identityAuthenticated':False,'hardCancellationImplemented':False}
            try:
                receipt=self._checkpoint()
                return {**receipt,'persistenceStatus':'checkpoint_committed_not_execution_proof'}
            except Exception:
                self._block()
                return self.receipt()


def inspect_recording(path):
    """Read-only metadata inspection; cannot resume a meeting or authorize dispatch."""
    from pathlib import Path
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
    try:
        rows=db.execute('SELECT seq,previous,digest,metadata FROM controller_observations ORDER BY seq').fetchall()
        if not rows or len(rows)>MAX_OBSERVATIONS:raise ControllerError('recording_invalid')
        previous='0'*64;result=[]
        for ordinal,(seq,prev,sha,encoded) in enumerate(rows,1):
            metadata=json.loads(encoded)
            if seq!=ordinal or prev!=previous or digest({'seq':seq,'previous':prev,'metadata':metadata})!=sha:
                raise ControllerError('recording_invalid')
            result.append(metadata);previous=sha
        return {'observations':result,'resumeAllowed':False,'executionAuthorized':False,
                'authenticityVerified':False,'currentRuntimeStateKnown':False}
    finally:db.close()
