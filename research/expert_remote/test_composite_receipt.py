"""Actual Pi with explicit mock HTTP only; never real remote mode."""
from copy import deepcopy
import socket
import pytest
from research.expert_meeting.machine import Meeting,canonical,digest
from research.expert_bridge.protocol import Bridge
from research.expert_executor.executor import Executor,ExecutionError
from research.expert_remote.receipt import validate_receipt,ReceiptError

@pytest.fixture(scope='module')
def completed():
    m=Meeting(provider_mode='remote');b=Bridge(m);e=Executor(b,provider_mode='remote_mock')
    for _ in range(2):
        m.act({'type':'start_round'})
        for role in ('source_attribution','uncertainty_boundary'):e.run_turn(role)
    return e.receipt()

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*a,**kw):raise AssertionError('network not permitted')
    monkeypatch.setattr(socket.socket,'connect',deny)


def rechain(events):
    prev='0'*64
    for i,e in enumerate(events,1):
        e.update(seq=i,previousSha256=prev);e['sha256']=digest({k:v for k,v in e.items() if k!='sha256'});prev=e['sha256']


def test_actual_pi_mock_four_turn_composite(completed):
    r=validate_receipt(canonical(completed))
    assert len(r['runs'])==4 and len(r['providerReceipt']['attempts'])==12
    assert r['transportMocked'] and not r['realDeepSeekExecuted']
    assert all(x['exitObserved']==0 and x['leaderReaped'] for x in r['runs'])

@pytest.mark.parametrize('attack',['mock_real','run_real','exit_bool','not_reaped','tool_count','model_count','context','provider_mode','meeting_id','runtime_hash','bridge_hash','missing_response','response_digest','pending_provider','missing_run','false_complete'])
def test_mutations_rejected(completed,attack):
    r=deepcopy(completed)
    if attack=='mock_real':r['realDeepSeekExecuted']=True
    if attack=='run_real':r['runs'][0]['realDeepSeekExecuted']=True
    if attack=='exit_bool':r['runs'][0]['exitObserved']=False
    if attack=='not_reaped':r['runs'][0]['leaderReaped']=False
    if attack=='tool_count':r['bridgeAudit']['sessions'][0]['toolCalls']=3
    if attack=='model_count':r['bridgeAudit']['sessions'][0]['modelAttempts']=4
    if attack=='context':r['bridgeAudit']['sessions'][0]['contextDigest']='0'*64
    if attack=='provider_mode':r['providerMode']='remote'
    if attack=='meeting_id':r['providerReceipt']['meetingId']='00000000-0000-0000-0000-000000000000';r['providerReceipt']['receiptSha256']=digest({k:v for k,v in r['providerReceipt'].items() if k!='receiptSha256'})
    if attack=='runtime_hash':r['runtimeEvents'][0]['sha256']='0'*64
    if attack=='bridge_hash':r['bridgeAudit']['events'][0]['sha256']='0'*64
    if attack=='missing_response':r['runtimeEvents']=[e for e in r['runtimeEvents'] if e['phase']!='provider_response_received'];rechain(r['runtimeEvents'])
    if attack=='response_digest':
        next(e for e in r['runtimeEvents'] if e['phase']=='provider_response_received')['responseDigest']='0'*64;rechain(r['runtimeEvents'])
    if attack=='pending_provider':r['providerReceipt']['attempts'][-1]['status']='unknown';rechain(r['providerReceipt']['attempts']);r['providerReceipt']['receiptSha256']=digest({k:v for k,v in r['providerReceipt'].items() if k!='receiptSha256'})
    if attack=='missing_run':r['runs'].pop()
    if attack=='false_complete':r['runs'][0]['receiptComplete']=False
    with pytest.raises(ReceiptError):validate_receipt(canonical(r))


def test_partial_after_one_complete_turn():
    m=Meeting(provider_mode='remote');b=Bridge(m);e=Executor(b,provider_mode='remote_mock');m.act({'type':'start_round'})
    e.run_turn('source_attribution');e.cancel();r=validate_receipt(canonical(e.receipt()))
    assert r['meetingSnapshot']['state']['phase']=='stopped_by_operator'
    assert len(r['runs'])==1


def test_unknown_failure_preserved(monkeypatch):
    from research.expert_remote import isolated,transport
    async def fail(*a,**kw):raise transport.TransportError('synthetic_unknown',True)
    monkeypatch.setattr(isolated,'request',fail)
    m=Meeting(provider_mode='remote');b=Bridge(m);e=Executor(b,provider_mode='remote_mock');m.act({'type':'start_round'})
    with pytest.raises(ExecutionError):e.run_turn('source_attribution')
    r=validate_receipt(canonical(e.receipt()))
    assert r['runs'][0]['status']=='unknown'
    assert not r['meetingSnapshot']['state']['rounds'][0]['responses']


def test_incomplete_audit_not_upgraded(completed):
    r=deepcopy(completed);r['receiptComplete']=False;r['runs'][0]['receiptComplete']=False
    assert validate_receipt(canonical(r))['receiptComplete'] is False

@pytest.mark.parametrize('raw',[b'{}',b'\xff',b'{"schemaVersion":2,"schemaVersion":2}',b'x'*(8*1024*1024+1)])
def test_bad_input(raw):
    with pytest.raises(ReceiptError):validate_receipt(raw)
