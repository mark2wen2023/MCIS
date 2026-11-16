"""Read-only v1 ledger inspection, never resume or execution authorization."""
from contextlib import closing
from pathlib import Path
import re
import sqlite3
import uuid

from research.expert_budget.stable_protocol import ROLES, _ticket
from research.expert_group.packet import PACKET_SHA256


def _uuid(value):
    try:
        return type(value) is str and str(uuid.UUID(value)) == value
    except ValueError:
        return False


def _sha(value):
    return type(value) is str and re.fullmatch('[a-f0-9]{64}', value) is not None


def inspect_ledger(path, expected_meeting, expected_packet):
    """Observe one SQLite snapshot. Path/contents do not prove trusted DB identity.

    Only the stable-host v1 subset is recognized. Unknown older ticket mappings
    remain blocked. No rows, schema, pragmas or journal settings are modified.
    """
    base = {'dispatchAllowed':False, 'restoreReady':False,
            'roleProgress':'unknown_legacy_v1', 'databaseIdentityVerified':False}
    def result(category, reason, **fields):
        return {**base, 'classification':category, 'reason':reason, **fields}
    if not _uuid(expected_meeting) or expected_packet != PACKET_SHA256:
        return result('blocked_inconsistent','expected_binding')
    try:
        uri = Path(path).absolute().as_uri() + '?mode=ro'
        with closing(sqlite3.connect(uri, uri=True, timeout=1)) as db:
            db.row_factory = sqlite3.Row
            db.execute('BEGIN')
            version = db.execute('PRAGMA user_version').fetchone()[0]
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
            if version != 1 or tables != {'sessions','tickets','requests'}:
                return result('blocked_inconsistent','schema')
            columns = {'sessions':['id','packet','state'],
                       'tickets':['id','meeting','role','round','context'],
                       'requests':['id','ticket','ordinal','outcome','receipt']}
            for table, names in columns.items():
                if [r[1] for r in db.execute(f'PRAGMA table_info({table})')] != names:
                    return result('blocked_inconsistent','columns')
            # One host ledger contains one meeting; do not silently ignore extra rows.
            sessions = [dict(r) for r in db.execute('SELECT * FROM sessions LIMIT 2')]
            tickets = [dict(r) for r in db.execute('SELECT * FROM tickets LIMIT 9')]
            requests = [dict(r) for r in db.execute('SELECT * FROM requests LIMIT 17')]
            if len(sessions)!=1 or len(tickets)>8 or len(requests)>16:
                return result('blocked_inconsistent','cardinality')
            session=sessions[0]
            if session['id']!=expected_meeting or session['packet']!=expected_packet:
                return result('blocked_inconsistent','session_binding')
            if session['state'] not in ('open','stopped_unknown','partial_budget_exhausted'):
                return result('blocked_inconsistent','session_state')
            by_ticket={}
            positions=set()
            for t in tickets:
                if (t['meeting']!=expected_meeting or t['role'] not in ROLES or
                    type(t['round']) is not int or t['round'] not in (1,2) or not _sha(t['context'])):
                    return result('blocked_inconsistent','ticket_binding')
                position=(t['round']-1)*4+ROLES.index(t['role'])
                if position in positions or t['id'] in by_ticket:
                    return result('blocked_inconsistent','duplicate_ticket')
                if t['id'] != _ticket(expected_meeting,t['role'],t['round']):
                    return result('blocked_unknown','unrecognized_ticket_mapping')
                positions.add(position); by_ticket[t['id']]=t
            if positions != set(range(len(tickets))):
                return result('blocked_inconsistent','ticket_sequence')
            grouped={ticket:[] for ticket in by_ticket}
            ids=set()
            for r in requests:
                if r['ticket'] not in by_ticket or type(r['ordinal']) is not int or r['ordinal'] not in (1,2):
                    return result('blocked_inconsistent','request_binding')
                if r['id'] != f"{r['ticket']}:model:{r['ordinal']}" or r['id'] in ids:
                    return result('blocked_inconsistent','request_id')
                if r['outcome'] not in ('reserved','received_unverified','unknown','not_dispatched'):
                    return result('blocked_inconsistent','request_outcome')
                if (_sha(r['receipt']) if r['outcome']=='received_unverified' else r['receipt'] is None) is not True:
                    return result('blocked_inconsistent','receipt')
                ids.add(r['id']); grouped[r['ticket']].append(r)
            for rows in grouped.values():
                if sorted(r['ordinal'] for r in rows) != list(range(1,len(rows)+1)):
                    return result('blocked_inconsistent','request_sequence')
            if session['state']=='partial_budget_exhausted' and not (
                len(requests)==16 or any(len(rows)==2 for rows in grouped.values())):
                return result('blocked_inconsistent','budget_state')
            fields={'recordedSessionState':session['state'], 'requestCount':len(requests),
                    'ticketCount':len(tickets), 'remainingRecordedAllowance':16-len(requests)}
            if any(r['outcome'] in ('reserved','unknown','not_dispatched') for r in requests):
                return result('blocked_unknown','unresolved_or_stopped_request',**fields)
            if session['state'] in ('stopped_unknown','partial_budget_exhausted'):
                return result('recorded_stopped','recorded_terminal_state_only',**fields)
            return result('blocked_unknown','open_without_durable_role_progress',**fields)
    except (sqlite3.Error, OSError, ValueError):
        return result('blocked_unknown','unreadable_snapshot')
