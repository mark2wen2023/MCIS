import io,json,hashlib
import pytest
from research.expert_remote import preflight as p

def value():return dict(schema=p.SCHEMA,intentId='11111111-1111-4111-8111-111111111111',operation='prepare_public_two_round_review',packetSha256=p.PACKET_SHA)
@pytest.mark.parametrize('field',['key','ready','executionAuthorized','proxy','endpoint','reviews','budget','caseId'])
def test_extra_fields_cannot_claim_authority(field):
    d=value();d[field]=True
    with pytest.raises(p.IntentError):p.inspect(json.dumps(d).encode())
@pytest.mark.parametrize('raw',[b'\xef\xbb\xbf{}',b'\xff',b'['*2000+b']'*2000,b' '*4097])
def test_invalid_bounded_input(raw):
    with pytest.raises(p.IntentError):p.inspect(raw)
def test_duplicate_and_escaped_duplicate():
    raw=json.dumps(value())
    for key in ['intentId',r'\u0069ntentId']:
        with pytest.raises(p.IntentError):p.inspect((raw[:-1]+',"'+key+'":"11111111-1111-4111-8111-111111111111"}').encode())
def test_repeated_and_reformatted_intent_always_blocked():
    a=p.inspect(json.dumps(value()).encode());b=p.inspect(json.dumps(value(),sort_keys=True,indent=2).encode())
    assert a==b and a['status']=='blocked'
    assert all(a[k] is False for k in ['executionAuthorized','requestDispatched','authenticityVerified','isExecutionReceipt','limitsReserved'])
    assert a['intentSha256']==hashlib.sha256(json.dumps(value(),sort_keys=True,separators=(',',':')).encode()).hexdigest()
@pytest.mark.parametrize('valid',[True,False])
def test_cli_bounded_read_and_exit2(monkeypatch,capsys,valid):
    class Reader:
        def read(self,n):assert n==4097;return json.dumps(value()).encode() if valid else b'[]'
    class Stream:buffer=Reader()
    monkeypatch.setattr(p.sys,'stdin',Stream())
    assert p.main(['--check-stdin'])==2
    r=json.loads(capsys.readouterr().out);assert r['status']==('blocked' if valid else 'invalid') and not r['requestDispatched']
