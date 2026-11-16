"""New ordinary synthetic classification tests. No write-refusal probes.
Fixture setup writes a temporary DB; inspection only reads it. No processes.
"""
import sqlite3
from research.expert_budget.readonly_inspection import inspect_ledger
from research.expert_budget.stable_protocol import _ticket
from research.expert_group.packet import PACKET_SHA256

MEETING='00000000-0000-4000-8000-000000000001'
TICKET=_ticket(MEETING,'regulations',1)


def fixture(tmp_path, outcomes=(), state='open', ticket=TICKET):
    path=tmp_path/'synthetic.sqlite'
    with sqlite3.connect(path) as db:
        db.executescript('''
        PRAGMA user_version=1;
        CREATE TABLE sessions(id TEXT, packet TEXT, state TEXT);
        CREATE TABLE tickets(id TEXT, meeting TEXT, role TEXT, round INTEGER, context TEXT);
        CREATE TABLE requests(id TEXT, ticket TEXT, ordinal INTEGER, outcome TEXT, receipt TEXT);
        ''')
        db.execute('INSERT INTO sessions VALUES(?,?,?)',(MEETING,PACKET_SHA256,state))
        db.execute('INSERT INTO tickets VALUES(?,?,?,?,?)',(ticket,MEETING,'regulations',1,'a'*64))
        for n,outcome in enumerate(outcomes,1):
            db.execute('INSERT INTO requests VALUES(?,?,?,?,?)',
                       (f'{ticket}:model:{n}',ticket,n,outcome,'b'*64 if outcome=='received_unverified' else None))
    return path


def inspect(path, meeting=MEETING):
    answer=inspect_ledger(path,meeting,PACKET_SHA256)
    assert not answer['dispatchAllowed'] and not answer['restoreReady']
    assert not answer['databaseIdentityVerified']
    assert answer['roleProgress']=='unknown_legacy_v1'
    return answer


def test_open_received_does_not_infer_role_completion(tmp_path):
    path=fixture(tmp_path,('received_unverified',))
    before=path.read_bytes()
    answer=inspect(path)
    assert answer['reason']=='open_without_durable_role_progress'
    assert answer['requestCount']==1
    assert path.read_bytes()==before


def test_pending_and_unknown_are_blocked(tmp_path):
    # Separate temporary fixture names, never a write attempt on inspector connection.
    for outcome in ('reserved','unknown'):
        directory=tmp_path/outcome; directory.mkdir()
        answer=inspect(fixture(directory,(outcome,), 'open' if outcome=='reserved' else 'stopped_unknown'))
        assert answer['classification']=='blocked_unknown'
        assert answer['reason']=='unresolved_or_stopped_request'


def test_recorded_budget_stop_is_not_resume_permission(tmp_path):
    answer=inspect(fixture(tmp_path,('received_unverified','received_unverified'),'partial_budget_exhausted'))
    assert answer['classification']=='recorded_stopped'
    assert answer['remainingRecordedAllowance']==14


def test_expected_meeting_mismatch_is_blocked(tmp_path):
    answer=inspect(fixture(tmp_path),'00000000-0000-4000-8000-000000000002')
    assert answer['classification']=='blocked_inconsistent'
    assert answer['reason']=='session_binding'


def test_older_ticket_mapping_is_unknown(tmp_path):
    answer=inspect(fixture(tmp_path,ticket='00000000-0000-4000-8000-000000000003'))
    assert answer['classification']=='blocked_unknown'
    assert answer['reason']=='unrecognized_ticket_mapping'


def test_three_requests_exceed_turn_budget(tmp_path):
    answer=inspect(fixture(tmp_path,('received_unverified',)*3))
    assert answer['classification']=='blocked_inconsistent'
    assert answer['reason']=='request_binding'


def test_orphan_request_is_inconsistent(tmp_path):
    path=tmp_path/'synthetic.sqlite'
    with sqlite3.connect(path) as db:
        db.executescript('''
        PRAGMA user_version=1;
        CREATE TABLE sessions(id TEXT, packet TEXT, state TEXT);
        CREATE TABLE tickets(id TEXT, meeting TEXT, role TEXT, round INTEGER, context TEXT);
        CREATE TABLE requests(id TEXT, ticket TEXT, ordinal INTEGER, outcome TEXT, receipt TEXT);
        ''')
        db.execute('INSERT INTO sessions VALUES(?,?,?)',(MEETING,PACKET_SHA256,'open'))
        db.execute('INSERT INTO requests VALUES(?,?,?,?,?)',(TICKET+':model:1',TICKET,1,'reserved',None))
    answer=inspect(path)
    assert answer['classification']=='blocked_inconsistent' and answer['reason']=='request_binding'


def test_wrong_expected_material_is_blocked(tmp_path):
    answer=inspect_ledger(fixture(tmp_path),MEETING,'c'*64)
    assert answer['reason']=='expected_binding'
    assert not answer['dispatchAllowed'] and not answer['restoreReady']
