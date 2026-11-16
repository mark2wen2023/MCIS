"""New ordinary synthetic contract tests; no write refusal, processes or models."""
import sqlite3
import uuid
import pytest
from research.expert_budget.ledger_v2 import NewMeetingLedger, inspect_v2, canonical, digest, event, legacy_advance
from research.expert_budget.stable_protocol import initial
from research.expert_group.packet import PACKET_SHA256
M='00000000-0000-4000-8000-000000000001'


def setup(tmp_path):
    p=tmp_path/'new.sqlite'; h=NewMeetingLedger(p,M)
    t=apply(h,{'type':'issue','role':'regulations','round':1,'contextDigest':'a'*64})['ticketId']
    return h,p,t


def apply(h,a): return h.apply(str(uuid.uuid4()),a)['recordedResult']


def received(h,t,n):
    r=apply(h,{'type':'request','ticketId':t,'ordinal':n})
    apply(h,{'type':'result','ticketId':t,'requestId':r['requestId'],
             'outcome':'received_unverified','receiptDigest':'b'*64})


def test_receipt_recorded_in_state_and_audit(tmp_path):
    h,p,t=setup(tmp_path); received(h,t,1)
    view=inspect_v2(p,M)
    assert view['contractRevision']==3
    assert view['state']['turns'][0]['requests'][0]['receiptDigest']=='b'*64
    with sqlite3.connect(p) as db:
        assert 'receiptDigest' in db.execute('SELECT body FROM audit ORDER BY seq DESC LIMIT 1').fetchone()[0]
    assert not view['dispatchAllowed']


def test_missing_new_receipt_rejects_without_added_operation(tmp_path):
    h,p,t=setup(tmp_path)
    r=apply(h,{'type':'request','ticketId':t,'ordinal':1})
    with pytest.raises(ValueError,match='result_shape'):
        apply(h,{'type':'result','ticketId':t,'requestId':r['requestId'],'outcome':'received_unverified'})
    assert inspect_v2(p,M)['revision']==2
    assert h.blocked


def test_duplicate_operation_is_historical_not_new_grant(tmp_path):
    h,p,t=setup(tmp_path); op=str(uuid.uuid4())
    action={'type':'request','ticketId':t,'ordinal':1}
    h.apply(op,action); repeated=h.apply(op,action)
    assert repeated['duplicate'] and not repeated['newDispatchGrant']
    assert not repeated['dispatchAllowed'] and inspect_v2(p,M)['revision']==2


def test_repeated_request_new_operation_stops_atomically(tmp_path):
    h,p,t=setup(tmp_path); received(h,t,1)
    duplicate=apply(h,{'type':'request','ticketId':t,'ordinal':1})
    view=inspect_v2(p,M)
    assert not duplicate['newReservation']
    assert view['state']['stopReason']=='protocol_duplicate'
    assert len(view['state']['turns'][0]['requests'])==1
    assert view['state']['turns'][0]['requests'][0]['receiptDigest']=='b'*64


def test_later_stop_preserves_budget_reason(tmp_path):
    h,p,t=setup(tmp_path); received(h,t,1); received(h,t,2)
    apply(h,{'type':'request','ticketId':t,'ordinal':3})
    apply(h,{'type':'stop','reason':'operator_stop'})
    view=inspect_v2(p,M)
    assert view['state']['status']=='partial_budget_exhausted'
    assert view['state']['stopReason']=='budget_exhausted'


def test_legacy_v2_receipt_absence_stays_unknown(tmp_path):
    p=tmp_path/'legacy.sqlite'; state=initial(M)
    action={'type':'issue','role':'regulations','round':1,'contextDigest':'a'*64}
    events=[]; previous='0'*64
    for seq in (1,2,3):
        after,result=legacy_advance(state,action)
        result={**result,'dispatchAllowed':False,'executionVerified':False}
        op=str(uuid.uuid4()); body=event(seq,op,action,state,after,result,previous)
        events.append((op,digest(action),seq,canonical(result),canonical(body),digest(body)))
        previous=digest(body); state=after
        if seq==1: action={'type':'request','ticketId':result['ticketId'],'ordinal':1}
        elif seq==2: action={'type':'result','ticketId':action['ticketId'],'requestId':result['requestId'],'outcome':'received_unverified'}
    with sqlite3.connect(p) as db:
        db.executescript('PRAGMA user_version=2; CREATE TABLE meta(id,ledger,meeting,packet); CREATE TABLE current(id,revision,state); CREATE TABLE operations(op,input_digest,seq,result); CREATE TABLE audit(seq,op,body,digest);')
        db.execute('INSERT INTO meta VALUES(1,?,?,?)',(str(uuid.uuid4()),M,PACKET_SHA256))
        db.execute('INSERT INTO current VALUES(1,3,?)',(canonical(state),))
        for op,inp,seq,res,body,sha in events:
            db.execute('INSERT INTO operations VALUES(?,?,?,?)',(op,inp,seq,res))
            db.execute('INSERT INTO audit VALUES(?,?,?,?)',(seq,op,body,sha))
    before=p.read_bytes(); view=inspect_v2(p,M)
    assert view['receiptCoverage']=='unknown_legacy' and view['contractRevision']==2
    assert 'receiptDigest' not in view['state']['turns'][0]['requests'][0]
    assert not view['dispatchAllowed'] and p.read_bytes()==before
