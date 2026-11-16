"""Isolated v2 new-meeting ledger. No transport, resume or execution authority."""
from contextlib import closing
from copy import deepcopy
import hashlib
import json
import re
from pathlib import Path
import sqlite3
import uuid
from research.expert_budget.stable_protocol import initial, step
from research.expert_group.packet import PACKET_SHA256, GroupError

MAX_OPERATIONS = 128


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def require(ok, reason):
    if not ok: raise ValueError(reason)


def operation_id(value):
    require(type(value) is str and str(uuid.UUID(value))==value,'operation_id')


def event(seq, op, action, before, after, result, previous):
    return {'seq':seq,'operationId':op,'action':action,'beforeDigest':digest(before),
            'afterDigest':digest(after),'result':result,'previousDigest':previous}


def legacy_advance(state, action):
    if type(action) is dict and action.get('type')=='stop':
        require(set(action)=={'type','reason'} and action['reason']=='operator_stop','stop_action')
        require(state['status']=='open','meeting_closed')
        after=deepcopy(state)
        after['status']='stopped_declared'
        for turn in after['turns']:
            if turn['status']=='active': turn['status']='incomplete_stopped'
            for request in turn['requests']:
                if request['outcome']=='pending': request['outcome']='unknown'
        return after, {'status':'stopped_declared','dispatchAuthorized':False}
    return step(state,action)


def advance(state, action):
    """Receipt contract revision 3; legacy revision 2 replay remains unchanged."""
    require(type(action) is dict,'action')
    kind=action.get('type')
    if kind=='stop':
        require(set(action)=={'type','reason'} and action['reason'] in
                ('operator_stop','protocol_duplicate','protocol_unknown'),'stop_action')
        if state['status']!='open':
            return deepcopy(state), {'status':state['status'],'stopReason':state.get('stopReason'),
                                     'dispatchAuthorized':False}
        after,result=legacy_advance(state,{'type':'stop','reason':'operator_stop'})
        after['stopReason']=action['reason']
        return after,{**result,'stopReason':action['reason']}
    if kind=='result':
        require(set(action)=={'type','ticketId','requestId','outcome','receiptDigest'},'result_shape')
        receipt=action['receiptDigest']
        require((type(receipt) is str and re.fullmatch('[a-f0-9]{64}',receipt) is not None)
                if action['outcome']=='received_unverified' else receipt is None,'receipt_digest')
        reduced={k:v for k,v in action.items() if k!='receiptDigest'}
        old=[r for t in state['turns'] if t['ticketId']==action['ticketId']
             for r in t['requests'] if r['requestId']==action['requestId']]
        if old and old[0]['outcome']!='pending':
            require(old[0].get('receiptDigest')==receipt,'receipt_changed')
        after,result=step(state,reduced)
        for t in after['turns']:
            if t['ticketId']==action['ticketId']:
                for r in t['requests']:
                    if r['requestId']==action['requestId']: r['receiptDigest']=receipt
        if state['status']=='open' and after['status']=='stopped_unknown':
            after['stopReason']='request_unknown'
        return after,result
    after,result=step(state,action)
    if kind=='request' and result.get('status')=='existing_no_redispatch':
        if state['status']=='open':
            after,_=advance(after,{'type':'stop','reason':'protocol_duplicate'})
        result={**result,'newReservation':False,'stopReason':after.get('stopReason')}
    if state['status']=='open' and after['status']=='partial_budget_exhausted':
        after['stopReason']='budget_exhausted'
    return after,result


class NewMeetingLedger:
    """One serialized owner; existing files cannot be opened for further writes."""
    contract_version = 3
    reducer = staticmethod(advance)

    def __init__(self, path, meeting_id):
        state=initial(meeting_id)
        with open(path,'xb'): pass
        self.path=Path(path)
        self.blocked=False
        self.meeting=meeting_id
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('PRAGMA synchronous=FULL')
            db.execute('BEGIN IMMEDIATE')
            db.execute('CREATE TABLE meta (id INTEGER PRIMARY KEY, ledger TEXT NOT NULL, meeting TEXT NOT NULL, packet TEXT NOT NULL)')
            db.execute('CREATE TABLE current (id INTEGER PRIMARY KEY, revision INTEGER NOT NULL, state TEXT NOT NULL)')
            db.execute('CREATE TABLE operations (op TEXT PRIMARY KEY, input_digest TEXT NOT NULL, seq INTEGER UNIQUE NOT NULL, result TEXT NOT NULL)')
            db.execute('CREATE TABLE audit (seq INTEGER PRIMARY KEY, op TEXT UNIQUE NOT NULL, body TEXT NOT NULL, digest TEXT NOT NULL)')
            db.execute(f'PRAGMA user_version={self.contract_version}')
            db.execute('INSERT INTO meta VALUES(1,?,?,?)',(str(uuid.uuid4()),meeting_id,PACKET_SHA256))
            db.execute('INSERT INTO current VALUES(1,0,?)',(canonical(state),))
            db.commit()

    def apply(self, op, action):
        require(not self.blocked,'owner_blocked')
        operation_id(op)
        raw=canonical(action)
        require(len(raw)<=4096,'action_size')
        with closing(sqlite3.connect(self.path,timeout=1)) as db:
            try:
                db.execute('PRAGMA synchronous=FULL')
                db.execute('BEGIN IMMEDIATE')
                old=db.execute('SELECT input_digest,result FROM operations WHERE op=?',(op,)).fetchone()
                if old:
                    require(old[0]==digest(action),'operation_changed')
                    db.rollback()
                    return {'duplicate':True,'recordedResult':json.loads(old[1]),'dispatchAllowed':False,'newDispatchGrant':False}
                revision,raw_state=db.execute('SELECT revision,state FROM current WHERE id=1').fetchone()
                require(revision<MAX_OPERATIONS,'operation_limit')
                before=json.loads(raw_state)
                after,result=self.reducer(before,action)
                # A pure reducer reservation is only a declaration until this commit.
                result={**result,'dispatchAllowed':False,'executionVerified':False}
                seq=revision+1
                previous=db.execute('SELECT digest FROM audit ORDER BY seq DESC LIMIT 1').fetchone()
                body=event(seq,op,action,before,after,result,previous[0] if previous else '0'*64)
                db.execute('INSERT INTO operations VALUES(?,?,?,?)',(op,digest(action),seq,canonical(result)))
                db.execute('INSERT INTO audit VALUES(?,?,?,?)',(seq,op,canonical(body),digest(body)))
                db.execute('UPDATE current SET revision=?,state=? WHERE id=1',(seq,canonical(after)))
                db.commit()
                return {'duplicate':False,'recordedResult':result,'dispatchAllowed':False,'newDispatchGrant':False}
            except BaseException:
                self.blocked=True
                # Closing rolls back if possible. No compensating write or retry.
                raise


def inspect_v2(path, expected_meeting, expected_ledger=None):
    """Read-only replay/consistency check; all outcomes forbid dispatch and resume."""
    base={'dispatchAllowed':False,'restoreReady':False,'executionVerified':False,
          'databaseIdentityVerified':False}
    try:
        with closing(sqlite3.connect(Path(path).absolute().as_uri()+'?mode=ro',uri=True,timeout=1)) as db:
            db.execute('BEGIN')
            version=db.execute('PRAGMA user_version').fetchone()[0]
            require(version in (2,3,4),'version_not_v2_family')
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            require(tables=={'meta','current','operations','audit'},'tables')
            meta=db.execute('SELECT id,ledger,meeting,packet FROM meta LIMIT 2').fetchall()
            require(len(meta)==1 and meta[0][0]==1,'meta')
            _,ledger,meeting,packet=meta[0]
            operation_id(ledger)
            require(meeting==expected_meeting and packet==PACKET_SHA256,'binding')
            require(expected_ledger is None or ledger==expected_ledger,'ledger_binding')
            current=db.execute('SELECT id,revision,state FROM current LIMIT 2').fetchall()
            require(len(current)==1 and current[0][0]==1,'current')
            _,revision,raw_state=current[0]
            require(type(revision) is int and 0<=revision<=MAX_OPERATIONS,'revision')
            ops=db.execute('SELECT op,input_digest,seq,result FROM operations ORDER BY seq LIMIT 129').fetchall()
            audits=db.execute('SELECT seq,op,body,digest FROM audit ORDER BY seq LIMIT 129').fetchall()
            require(len(ops)==len(audits)==revision,'counts')
            reducer = legacy_advance if version == 2 else advance
            if version == 4:
                from research.expert_budget.single_seat_transcript import advance_transcript
                reducer = advance_transcript
            state=initial(meeting); previous='0'*64; seen=set()
            for index,(operation,audit) in enumerate(zip(ops,audits),1):
                op,input_digest,seq,raw_result=operation
                aseq,aop,raw_body,body_digest=audit
                operation_id(op)
                require(op not in seen and seq==aseq==index and op==aop,'operation_link')
                seen.add(op)
                body=json.loads(raw_body); action=body['action']
                require(len(canonical(action))<=4096,'action_size')
                after,result=reducer(state,action)
                result={**result,'dispatchAllowed':False,'executionVerified':False}
                expected=event(index,op,action,state,after,result,previous)
                require(body==expected and digest(body)==body_digest and digest(action)==input_digest and
                        json.loads(raw_result)==result,'audit_consistency')
                state=after; previous=body_digest
            require(json.loads(raw_state)==state,'state_consistency')
            pending=any(r['outcome'] in ('pending','unknown') for t in state['turns'] for r in t['requests'])
            return {**base,'classification':'blocked_unknown' if pending or state['status']=='open' else 'recorded_terminal_only',
                    'ledgerId':ledger,'revision':revision,'state':state,'contractRevision':version,
                    'receiptCoverage':('unknown_legacy' if version==2 else 'recorded_digests_not_response_verification'),
                    'transcriptCoverage':('recorded_synthetic_only' if version==4 else 'unknown_legacy'),
                    'reason':'no_execution_resume','roleProgress':'recorded_declarations_only'}
    except (sqlite3.Error,ValueError,TypeError,KeyError,OSError,GroupError):
        return {**base,'classification':'blocked_unverified','reason':'snapshot_not_verified'}
