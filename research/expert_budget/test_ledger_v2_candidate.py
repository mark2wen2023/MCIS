"""New ordinary synthetic ledger workflows. No write-refusal or safety probes."""
import sqlite3
import uuid
from research.expert_budget.ledger_v2 import NewMeetingLedger, inspect_v2

MEETING='00000000-0000-4000-8000-000000000001'


def create(tmp_path):
    path=tmp_path/'new-v2.sqlite'
    return NewMeetingLedger(path,MEETING),path


def apply(h,action):
    return h.apply(str(uuid.uuid4()),action)['recordedResult']


def issue(h,role='regulations',number=1):
    return apply(h,{'type':'issue','role':role,'round':number,'contextDigest':'a'*64})['ticketId']


def receive(h,ticket,n):
    r=apply(h,{'type':'request','ticketId':ticket,'ordinal':n})
    apply(h,{'type':'result','ticketId':ticket,'requestId':r['requestId'],'outcome':'received_unverified'})


def test_new_meeting_operation_state_audit_visible_together(tmp_path):
    h,path=create(tmp_path); issue(h)
    with sqlite3.connect(path) as reader:
        assert reader.execute('SELECT revision FROM current').fetchone()==(1,)
        assert reader.execute('SELECT COUNT(*) FROM operations').fetchone()==(1,)
        assert reader.execute('SELECT COUNT(*) FROM audit').fetchone()==(1,)
    view=inspect_v2(path,MEETING)
    assert view['revision']==1 and view['state']['turns'][0]['status']=='active'
    assert not view['dispatchAllowed'] and not view['restoreReady']


def test_same_operation_returns_recorded_result_without_new_audit(tmp_path):
    h,path=create(tmp_path); op=str(uuid.uuid4())
    action={'type':'issue','role':'regulations','round':1,'contextDigest':'a'*64}
    first=h.apply(op,action); second=h.apply(op,action)
    assert not first['duplicate'] and second['duplicate']
    assert first['recordedResult']==second['recordedResult']
    assert inspect_v2(path,MEETING)['revision']==1


def test_stop_persists_progress_and_unresolved_request(tmp_path):
    h,path=create(tmp_path); ticket=issue(h)
    apply(h,{'type':'request','ticketId':ticket,'ordinal':1})
    apply(h,{'type':'stop','reason':'operator_stop'})
    view=inspect_v2(path,MEETING)
    assert view['classification']=='blocked_unknown'
    assert view['state']['status']=='stopped_declared'
    assert view['state']['turns'][0]['status']=='incomplete_stopped'
    assert view['state']['turns'][0]['requests'][0]['outcome']=='unknown'
    assert not view['dispatchAllowed']


def test_partial_budget_retains_prior_declared_role(tmp_path):
    h,path=create(tmp_path); first=issue(h)
    receive(h,first,1)
    apply(h,{'type':'complete','ticketId':first})
    second=issue(h,'navigation'); receive(h,second,1); receive(h,second,2)
    denied=apply(h,{'type':'request','ticketId':second,'ordinal':3})
    assert not denied['newReservation']
    view=inspect_v2(path,MEETING)
    assert view['classification']=='recorded_terminal_only'
    assert view['state']['status']=='partial_budget_exhausted'
    assert [t['status'] for t in view['state']['turns']]==['completed_declared','incomplete_budget']
    assert not view['restoreReady']


def test_synthetic_unknown_remains_blocked_on_readonly_reopen(tmp_path):
    h,path=create(tmp_path); ticket=issue(h)
    r=apply(h,{'type':'request','ticketId':ticket,'ordinal':1})
    apply(h,{'type':'result','ticketId':ticket,'requestId':r['requestId'],'outcome':'unknown'})
    before=path.read_bytes()
    view=inspect_v2(path,MEETING)
    assert view['state']['status']=='stopped_unknown'
    assert view['classification']=='blocked_unknown' and not view['dispatchAllowed']
    assert path.read_bytes()==before


def test_v1_remains_unmodified_and_not_migrated(tmp_path):
    path=tmp_path/'synthetic-v1.sqlite'
    with sqlite3.connect(path) as db:
        db.execute('PRAGMA user_version=1')
        db.execute('CREATE TABLE sessions (id TEXT)')
    before=path.read_bytes()
    view=inspect_v2(path,MEETING)
    assert view['classification']=='blocked_unverified'
    assert not view['restoreReady'] and path.read_bytes()==before
