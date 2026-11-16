"""New ordinary synthetic messages. No processes/network or write-refusal probes."""
import sqlite3
import uuid
import pytest
from research.expert_budget.v2_host_protocol import V2HostProtocol

M='00000000-0000-4000-8000-000000000001'


def setup(tmp_path):
    p=tmp_path/'host.sqlite'; h=V2HostProtocol(p,M)
    t=send(h,{'op':'issue','role':'regulations','round':1,'contextDigest':'a'*64})['recordedResult']['ticketId']
    return h,p,t


def send(h,message): return h.handle(str(uuid.uuid4()),message)


def model(t,n): return {'op':'model','ticketId':t,'requestId':f'{t}:model:{n}'}


def received(h,t,n):
    send(h,model(t,n))
    return send(h,{'op':'result','ticketId':t,'requestId':f'{t}:model:{n}',
                   'outcome':'received_unverified','receiptDigest':'b'*64})


def test_only_new_ledger_and_receipt_path(tmp_path):
    h,p,t=setup(tmp_path); received(h,t,1)
    with sqlite3.connect(p) as db:
        assert {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}=={'meta','current','operations','audit'}
    view=h.inspect()
    assert view['revision']==3
    assert view['state']['turns'][0]['requests'][0]['receiptDigest']=='b'*64
    assert not view['dispatchAllowed']


def test_outer_duplicate_blocks_historical_reservation(tmp_path):
    h,p,t=setup(tmp_path); op=str(uuid.uuid4())
    first=h.handle(op,model(t,1)); duplicate=h.handle(op,model(t,1))
    assert first['simulatedReservationCommitted']
    assert duplicate['recordedResult']['newReservation'] is True
    assert duplicate['duplicate'] and not duplicate['simulatedReservationCommitted']
    assert not duplicate['newDispatchGrant'] and h.blocked
    assert h.inspect()['revision']==2


def test_new_operation_duplicate_preserves_receipt_and_stop_reason(tmp_path):
    h,p,t=setup(tmp_path); received(h,t,1)
    duplicate=send(h,model(t,1)); view=h.inspect()
    assert not duplicate['simulatedReservationCommitted'] and h.blocked
    assert view['state']['stopReason']=='protocol_duplicate'
    assert view['state']['turns'][0]['requests'][0]['receiptDigest']=='b'*64


def test_budget_stop_retains_reason_and_prior_progress(tmp_path):
    h,p,t=setup(tmp_path); received(h,t,1); received(h,t,2)
    send(h,model(t,3)); view=h.inspect()
    assert view['state']['stopReason']=='budget_exhausted' and h.blocked
    assert len(view['state']['turns'][0]['requests'])==2
    with pytest.raises(ValueError,match='host_blocked'):
        send(h,{'op':'stop','reason':'operator_stop'})
    assert h.inspect()['state']['stopReason']=='budget_exhausted'


def test_unknown_message_stops_without_retry(tmp_path):
    h,p,t=setup(tmp_path); send(h,model(t,1))
    send(h,{'op':'result','ticketId':t,'requestId':f'{t}:model:1',
            'outcome':'unknown','receiptDigest':None})
    assert h.blocked and h.inspect()['state']['stopReason']=='request_unknown'
    with pytest.raises(ValueError,match='host_blocked'): send(h,model(t,2))
    assert h.inspect()['revision']==3


def test_malformed_message_blocks_without_added_operation(tmp_path):
    h,p,t=setup(tmp_path)
    with pytest.raises(ValueError,match='model_shape'):
        send(h,{'op':'model','ticketId':t})
    assert h.blocked and h.inspect()['revision']==1
