"""Request-level durable declarations; no transport, credentials or execution permit."""
import re
import sqlite3
from contextlib import contextmanager
from research.expert_budget.ledger import ROLES, PER_TURN, TOTAL, ident
from research.expert_group.packet import PACKET_SHA256


class RequestBudgetError(ValueError):
    pass


def require(ok, code):
    if not ok: raise RequestBudgetError(code)


def sha(value):
    require(type(value) is str and re.fullmatch('[a-f0-9]{64}', value) is not None, 'digest')


class RequestBudget:
    def __init__(self, path):
        self.path = path
        self._uncertain = False
        with self._tx() as db:
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
            require(not tables or tables == {'sessions', 'tickets', 'requests'}, 'foreign_database')
            if tables: require(db.execute('PRAGMA user_version').fetchone()[0] == 1, 'schema_version')
            db.execute('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, packet TEXT NOT NULL, state TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS tickets (id TEXT PRIMARY KEY, meeting TEXT NOT NULL REFERENCES sessions(id), role TEXT NOT NULL, round INTEGER NOT NULL, context TEXT NOT NULL, UNIQUE(meeting,role,round))')
            db.execute('CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, ticket TEXT NOT NULL REFERENCES tickets(id), ordinal INTEGER NOT NULL, outcome TEXT NOT NULL, receipt TEXT, UNIQUE(ticket,ordinal))')
            db.execute('PRAGMA user_version=1')

    @contextmanager
    def _tx(self, *, inspect=False):
        require(inspect or not self._uncertain, 'database_uncertain_no_retry')
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            db.execute('PRAGMA foreign_keys=ON'); db.execute('PRAGMA synchronous=FULL')
            db.execute('BEGIN IMMEDIATE')
            yield db
            try:
                db.commit()
            except BaseException:
                self._uncertain = True
                raise
        except Exception as exc:
            if isinstance(exc, sqlite3.Error): self._uncertain = True
            db.rollback(); raise
        finally: db.close()

    def create(self, meeting, packet):
        ident(meeting); require(packet == PACKET_SHA256, 'packet')
        with self._tx() as db:
            old = db.execute('SELECT * FROM sessions WHERE id=?', (meeting,)).fetchone()
            if old: require(old['packet'] == packet, 'binding')
            else: db.execute('INSERT INTO sessions VALUES(?,?,?)', (meeting, packet, 'open'))

    def bind_ticket(self, meeting, ticket, role, round_number, context):
        ident(meeting); ident(ticket); sha(context)
        require(role in ROLES and type(round_number) is int and round_number in (1,2), 'role_round')
        with self._tx() as db:
            old = db.execute('SELECT * FROM tickets WHERE id=?', (ticket,)).fetchone()
            if old:
                require((old['meeting'],old['role'],old['round'],old['context']) == (meeting,role,round_number,context), 'changed_ticket')
                return
            require(db.execute("SELECT 1 FROM sessions WHERE id=? AND state='open'", (meeting,)).fetchone(), 'session_not_open')
            require(not db.execute('SELECT 1 FROM tickets WHERE meeting=? AND role=? AND round=?', (meeting,role,round_number)).fetchone(), 'duplicate_role_ticket')
            db.execute('INSERT INTO tickets VALUES(?,?,?,?,?)', (ticket,meeting,role,round_number,context))

    def reserve(self, meeting, ticket, context, request_id):
        ident(meeting); ident(ticket); sha(context)
        require(type(request_id) is str and re.fullmatch(re.escape(ticket)+r':model:[1-9][0-9]{0,2}', request_id) is not None, 'request_id')
        ordinal = int(request_id.rsplit(':',1)[1])
        with self._tx() as db:
            bound = db.execute('SELECT * FROM tickets WHERE id=? AND meeting=? AND context=?', (ticket,meeting,context)).fetchone()
            require(bound is not None, 'ticket_binding')
            old = db.execute('SELECT * FROM requests WHERE id=?', (request_id,)).fetchone()
            if old: return self._view(request_id, old['outcome'], False, 'existing_no_redispatch')
            state = db.execute('SELECT state FROM sessions WHERE id=?', (meeting,)).fetchone()['state']
            require(state == 'open', 'session_not_open')
            rows = db.execute('SELECT r.*,t.role,t.round FROM requests r JOIN tickets t ON t.id=r.ticket WHERE t.meeting=?', (meeting,)).fetchall()
            require(not any(r['outcome']=='reserved' for r in rows), 'pending_unknown_no_dispatch')
            own = [r for r in rows if r['ticket']==ticket]
            require(ordinal == len(own)+1, 'request_sequence')
            if len(rows)>=TOTAL or len(own)>=PER_TURN:
                db.execute("UPDATE sessions SET state='partial_budget_exhausted' WHERE id=?", (meeting,))
                result = self._view(request_id, 'not_reserved', False, 'partial_budget_exhausted')
            else:
                if bound['round']==2:
                    require(all(any(r['role']==role and r['round']==1 and r['outcome']=='received_unverified' for r in rows) for role in ROLES), 'first_round_incomplete')
                require(not any(r['round']>bound['round'] for r in rows), 'round_regression')
                db.execute('INSERT INTO requests VALUES(?,?,?,?,NULL)', (request_id,ticket,ordinal,'reserved'))
                result = self._view(request_id, 'reserved', True, 'committed_reservation')
        return result  # No caller receives a new reservation before commit.

    @staticmethod
    def _view(request_id, outcome, new, status):
        return {'requestId': request_id, 'outcome': outcome, 'newReservation': new, 'status': status,
                'dispatchAuthorized': False, 'providerExecutionVerified': False}

    def settle(self, meeting, ticket, context, request_id, outcome, receipt_digest=None):
        ident(meeting); ident(ticket); sha(context)
        require(outcome in ('received_unverified','unknown','not_dispatched'), 'outcome')
        if outcome == 'received_unverified': sha(receipt_digest)
        else: require(receipt_digest is None, 'unexpected_receipt')
        with self._tx() as db:
            row = db.execute('SELECT r.*,t.meeting,t.context FROM requests r JOIN tickets t ON t.id=r.ticket WHERE r.id=?', (request_id,)).fetchone()
            require(row and (row['meeting'],row['ticket'],row['context']) == (meeting,ticket,context), 'receipt_binding')
            if row['outcome'] != 'reserved':
                require(row['outcome']==outcome and row['receipt']==receipt_digest, 'changed_receipt')
                return self._view(request_id, outcome, False, 'existing_receipt')
            require(db.execute('SELECT state FROM sessions WHERE id=?', (meeting,)).fetchone()['state']=='open', 'session_not_open')
            db.execute('UPDATE requests SET outcome=?,receipt=? WHERE id=?', (outcome,receipt_digest,request_id))
            if outcome != 'received_unverified':
                db.execute("UPDATE sessions SET state='stopped_unknown' WHERE id=?", (meeting,))
        return self._view(request_id, outcome, False, 'receipt_committed')

    def stop(self, meeting):
        ident(meeting)
        with self._tx() as db:
            require(db.execute('SELECT 1 FROM sessions WHERE id=?', (meeting,)).fetchone(), 'meeting')
            db.execute("UPDATE sessions SET state='stopped_unknown' WHERE id=?", (meeting,))
            db.execute("UPDATE requests SET outcome='unknown' WHERE outcome='reserved' AND ticket IN (SELECT id FROM tickets WHERE meeting=?)", (meeting,))

    def snapshot(self, meeting):
        ident(meeting)
        with self._tx(inspect=True) as db:
            session = db.execute('SELECT * FROM sessions WHERE id=?', (meeting,)).fetchone()
            require(session is not None, 'meeting')
            rows = [dict(r) for r in db.execute('SELECT r.* FROM requests r JOIN tickets t ON t.id=r.ticket WHERE t.meeting=? ORDER BY t.round,t.role,r.ordinal', (meeting,))]
            return {'meetingId': meeting, 'state': session['state'], 'requests': rows,
                    'remaining': TOTAL-len(rows), 'pendingOutcomeUnknown': any(r['outcome']=='reserved' for r in rows),
                    'executionAuthorized': False, 'providerExecutionVerified': False}
