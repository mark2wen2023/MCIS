import io
import json
import socket
import pytest
from research.expert_remote import preflight as p

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(socket.socket,'connect',lambda *a:pytest.fail('network forbidden'))

def intent():return {'schema':p.SCHEMA,'intentId':'00000000-0000-4000-8000-000000000001','operation':'prepare_public_two_round_review','packetSha256':p.PACKET_SHA}
def raw(d=None):return json.dumps(intent() if d is None else d).encode()

def test_valid_intent_is_blocked_and_not_receipt():
    r=p.inspect(raw());assert r['status']=='blocked' and not r['executionAuthorized'] and not r['requestDispatched']
    assert not r['authenticityVerified'] and not r['isExecutionReceipt'] and not r['limitsReserved']
    assert len(r['blockers'])==5 and r['proposedLimits']['modelAttempts']==16
    r['blockers'].clear();assert len(p.inspect(raw())['blockers'])==5

def test_repeats_and_canonical_digest_do_not_execute():
    assert p.inspect(raw())==p.inspect(json.dumps(intent(),indent=2).encode())
    d=intent();d['intentId']='00000000-0000-4000-8000-000000000002'
    assert p.inspect(raw(d))['intentSha256']!=p.inspect(raw())['intentSha256']

@pytest.mark.parametrize('field',['key','apiKey','proxy','endpoint','ready','approved','budget','caseId','receipt','sourceText'])
def test_no_browser_authority_or_private_payload(field):
    d=intent();d[field]='SYNTHETIC-NOT-A-SECRET'
    with pytest.raises(p.IntentError,match='^intent_invalid$'):p.inspect(raw(d))

@pytest.mark.parametrize('field,value',[('schema','other'),('operation','execute'),('packetSha256','f'*64),('intentId','bad'),('intentId',True)])
def test_binding_rejected(field,value):
    d=intent();d[field]=value
    with pytest.raises(p.IntentError):p.inspect(raw(d))

@pytest.mark.parametrize('data',[b'{}',b'[]',b'null',b'\xff',b'{"schema":1,"schema":2}',b'{"x":NaN}',b'x'*4097])
def test_malformed(data):
    with pytest.raises(p.IntentError):p.inspect(data)

@pytest.mark.parametrize('valid',[True,False])
def test_cli_never_returns_execution_success(monkeypatch,capsys,valid):
    class Input:
        buffer=io.BytesIO(raw() if valid else b'{"apiKey":"SYNTHETIC"}')
    monkeypatch.setattr(p.sys,'stdin',Input())
    assert p.main(['--check-stdin'])==2
    output=capsys.readouterr().out
    assert 'SYNTHETIC' not in output and json.loads(output)['requestDispatched'] is False
