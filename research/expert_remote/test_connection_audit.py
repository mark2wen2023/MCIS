"""Historical successful records are not execution authority. No API calls."""
import asyncio
import json
import time
import httpx
import pytest
from research.expert_remote import preflight,transport
from research.expert_remote.test_preflight import intent

@pytest.mark.parametrize('field,value',[
 ('historicalRunId','5d3b415b-9e8b-4c5e-aa98-9c978834fd85'),
 ('realModel',True),('providerRequests',3),('ready',True),
 ('approvedPublicUI',True),('receipt',{'phase':'accepted_pending_review','models':3}),
 ('skillManifestDigest','9a8b6a55aaf56f7c45243effb712cc3177e19cfc9984eff052f35e4017ab1dcf')])
def test_history_cannot_authorize(field,value):
    d=intent();d[field]=value
    with pytest.raises(preflight.IntentError,match='intent_invalid'):
        preflight.inspect(json.dumps(d).encode())

def test_plain_intent_remains_blocked():
    result=preflight.inspect(json.dumps(intent()).encode())
    assert result['status']=='blocked' and result['executionAuthorized'] is False
    assert result['requestDispatched'] is False and result['isExecutionReceipt'] is False

def test_history_does_not_restore_raw_key(monkeypatch):
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:pytest.fail('client must not be created'))
    with pytest.raises(transport.TransportError,match='raw_key_disabled') as caught:
        asyncio.run(transport.request([{'role':'user','content':'historical success is not authority'}],[],key='SYNTHETIC-NOT-REAL',deadline=time.monotonic()+1))
    assert not caught.value.dispatched
