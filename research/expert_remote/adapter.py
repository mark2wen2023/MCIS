"""Isolated provider boundary; never submits real responses as simulated turns."""
import asyncio
from copy import deepcopy
import threading
import time
import weakref
import uuid
from research.expert_bridge.protocol import Bridge
from research.expert_group.engine import TOOLS, PACKET_SHA256
from research.expert_meeting.machine import canonical, digest, strict, verify_snapshot
from research.expert_remote import transport

_owners = weakref.WeakKeyDictionary()
_owner_lock = threading.Lock()
SCHEMA = 'mcis.public-expert-provider-receipt.v1'
SCHEMA2 = 'mcis.public-expert-provider-receipt.v2'


class AdapterError(ValueError):
    pass


def _check(condition):
    if not condition: raise AdapterError('receipt_invalid')


def validate_receipt(raw):
    """Local consistency only; never author/provider authentication or meeting completion."""
    _check(type(raw) is bytes and len(raw) <= 2 * 1024 * 1024)
    try:
        r = strict(raw)
        v2 = r.get('schema') == SCHEMA2
        _check(set(r) == {'schema','packetSha256','meetingId','attempts','halted','authenticityVerified','meetingCompleted','receiptSha256'} | ({'transportMode'} if v2 else set()))
        if v2: _check(r['transportMode'] in {'remote','remote_mock'})
        _check(r['schema'] in {SCHEMA,SCHEMA2} and r['packetSha256'] == PACKET_SHA256)
        _check(r['authenticityVerified'] is False and r['meetingCompleted'] is False and type(r['halted']) is bool)
        _check(r['receiptSha256'] == digest({k:v for k,v in r.items() if k != 'receiptSha256'}))
        _check(type(r['attempts']) is list and len(r['attempts']) <= 16)
        _check(type(r['meetingId']) is str and str(uuid.UUID(r['meetingId'])) == r['meetingId'])
        counts = {}; ids = set(); previous = '0'*64; prior_events = []
        for row in r['attempts']:
            _check(set(row) == {'seq','requestId','ticketId','contextDigest','inputDigest','snapshot','status','responseDigest','responseMeta','previousSha256','sha256'} | ({'worker'} if v2 else set()))
            _check(type(row['seq']) is int and row['seq'] == len(ids)+1)
            _check(row['previousSha256'] == previous and row['sha256'] == digest({k:v for k,v in row.items() if k != 'sha256'}))
            previous = row['sha256']
            verify_snapshot(canonical(row['snapshot']))
            events = row['snapshot']['events']
            _check(events[:len(prior_events)] == prior_events)
            prior_events = events
            state = row['snapshot']['state']; turn = state['activeTurn']
            _check(state['meetingId'] == r['meetingId'] and state['phase'] == 'round_open' and turn is not None)
            _check(turn['ticketId'] == row['ticketId'] and turn['contextDigest'] == row['contextDigest'])
            _check(type(row['inputDigest']) is str and len(row['inputDigest']) == 64 and all(c in '0123456789abcdef' for c in row['inputDigest']))
            counts[row['ticketId']] = counts.get(row['ticketId'],0)+1
            _check(counts[row['ticketId']] <= 4 and row['requestId'] == row['ticketId']+':model:'+str(counts[row['ticketId']]))
            _check(row['requestId'] not in ids); ids.add(row['requestId'])
            _check(row['status'] in {'received_unverified','unknown','not_dispatched'})
            if v2:
                _check(state['mode'] == 'remote_protocol_declared')
                w = row['worker']
                _check(type(w) is dict and set(w) == {'processStarted','leaderReaped','exitObserved','transportMocked'})
                _check(w['transportMocked'] is (r['transportMode']=='remote_mock'))
                _check(type(w['processStarted']) is bool and type(w['leaderReaped']) is bool)
                _check(w['exitObserved'] is None or type(w['exitObserved']) is int)
                if not w['processStarted']: _check(not w['leaderReaped'] and w['exitObserved'] is None)
                if row['status']=='received_unverified': _check(w['processStarted'] and w['leaderReaped'] and w['exitObserved']==0)
            if row['status'] == 'received_unverified':
                _check(type(row['responseDigest']) is str and len(row['responseDigest']) == 64 and all(c in '0123456789abcdef' for c in row['responseDigest']))
                transport.validate_meta(row['responseMeta'])
            else:
                _check(row['responseDigest'] is None and row['responseMeta'] is None)
                _check(r['halted'] and row is r['attempts'][-1])
        return deepcopy(r)
    except (TypeError, KeyError, ValueError, AttributeError, RecursionError):
        raise AdapterError('receipt_invalid') from None


class Adapter:
    """Single-owner provider gate for an existing Bridge. No automatic retry.

    Remote Executor consumes reserved requests and uses the separate provider_response gate.
    This object is process-local and non-resumable; receipts are not restart checkpoints.
    """
    def __init__(self, bridge, *, key, enabled=False, clock=time.monotonic, transport_mode='direct'):
        if type(bridge) is not Bridge or enabled is not True or type(key) is not str or not key.strip():
            raise AdapterError('explicit_configuration_required')
        if transport_mode not in {'direct','remote','remote_mock'}: raise AdapterError('transport_mode')
        if transport_mode != 'direct' and bridge.provider_mode != 'remote': raise AdapterError('remote_bridge_required')
        if transport_mode == 'direct' and bridge.provider_mode != 'scripted': raise AdapterError('isolated_transport_required')
        self.transport_mode = transport_mode
        if any(s['modelAttempts'] or s['toolCalls'] for s in bridge.audit()['sessions']):
            raise AdapterError('bridge_already_used')
        with _owner_lock:
            if bridge in _owners: raise AdapterError('adapter_already_bound')
            _owners[bridge] = True
        self._bridge = bridge; self._key = key; self._clock = clock
        self._started = clock(); self._turn_started = {}; self._rows = []; self._halted = False
        self._running = False; self._lock = threading.Lock()
        self._cancel = threading.Event()

    def cancel(self):
        self._halted = True
        self._cancel.set()
        self._bridge.stop()

    async def dispatch(self, ticket, reserved_request=None):
        with self._lock:
            if self._running or self._halted: raise AdapterError('adapter_closed_or_busy')
            self._running = True
        row = None
        try:
            if self._cancel.is_set() or self._clock()-self._started >= 600:
                self._halted = True; raise AdapterError('cancelled_or_deadline')
            if len(self._rows) >= 16 or sum(r['ticketId']==ticket for r in self._rows) >= 4:
                raise AdapterError('provider_budget')
            # Bridge constructs messages from fixed prompts, packet and prior complete round.
            if reserved_request is None:
                request = self._bridge.from_runner(ticket, {'op':'model'})
            else:
                request = self._bridge.pending_request(ticket)
                if request is None or canonical(request) != canonical(reserved_request): raise AdapterError('reserved_request_mismatch')
            if any(r['requestId']==request['requestId'] for r in self._rows): raise AdapterError('request_already_dispatched')
            snapshot = strict(self._bridge.meeting.export())
            turn = snapshot['state']['activeTurn']
            started = self._turn_started.setdefault(ticket, self._clock())
            deadline = min(self._started+600, started+120)
            row = {'seq':len(self._rows)+1,'requestId':request['requestId'],'ticketId':ticket,
                   'contextDigest':turn['contextDigest'],'inputDigest':digest(request['messages']),
                   'snapshot':snapshot,'status':'unknown','responseDigest':None,'responseMeta':None,
                   'previousSha256':self._rows[-1]['sha256'] if self._rows else '0'*64}
            if self.transport_mode != 'direct':
                row['worker']={'processStarted':False,'leaderReaped':False,'exitObserved':None,'transportMocked':self.transport_mode=='remote_mock'}
            self._rows.append(row) # Consumes allowance before dispatch; never refunded.
            def cancelled():
                if self._cancel.is_set(): return True
                try: self._bridge.poll(ticket)
                except Exception: return True
                return False
            if self.transport_mode == 'direct':
                result = await transport.request(request['messages'], deepcopy(TOOLS), key=self._key,deadline=deadline,cancel=cancelled)
            else:
                from research.expert_remote.isolated import request as isolated_request
                result = await isolated_request(request['messages'],deepcopy(TOOLS),key=self._key,deadline=deadline,cancel=cancelled,mocked=self.transport_mode=='remote_mock')
                row['worker']=deepcopy(result['worker'])
            if self._cancel.is_set() or self._clock() >= deadline:
                raise AdapterError('cancelled_or_deadline')
            self._bridge.poll(ticket)
            transport.validate_meta(result['responseMeta'])
            row.update(status='received_unverified',responseDigest=digest(result['assistant']),responseMeta=deepcopy(result['responseMeta']))
            return deepcopy(result)
        except transport.TransportError as exc:
            if row is not None:
                row['status'] = 'unknown' if exc.dispatched else 'not_dispatched'
                if self.transport_mode!='direct' and hasattr(exc,'worker'): row['worker']=deepcopy(exc.worker)
            self._halted = True
            raise AdapterError('provider_unknown' if exc.dispatched else 'provider_not_dispatched') from None
        except asyncio.CancelledError:
            self._halted = True
            raise
        except Exception:
            self._halted = True
            raise AdapterError('adapter_rejected') from None
        finally:
            if row is not None:
                if row['status'] == 'unknown': self._halted = True
                row['sha256'] = digest({k:v for k,v in row.items() if k != 'sha256'})
            with self._lock: self._running = False

    def receipt(self):
        with self._lock:
            if self._running: raise AdapterError('receipt_while_running')
            r={'schema':SCHEMA,'packetSha256':PACKET_SHA256,'meetingId':self._bridge.meeting.snapshot()['meetingId'],
               'attempts':deepcopy(self._rows),'halted':self._halted,'authenticityVerified':False,'meetingCompleted':False}
            if self.transport_mode != 'direct':r.update(schema=SCHEMA2,transportMode=self.transport_mode)
            r['receiptSha256']=digest(r)
            return validate_receipt(canonical(r))
