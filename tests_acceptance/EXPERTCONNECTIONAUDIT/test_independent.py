import asyncio,json,hashlib,subprocess,time
from pathlib import Path
import httpx,pytest
from research.expert_remote import preflight,transport,managed
AUDIT=json.loads(Path('research/expert_remote/connection-audit.json').read_bytes())
REPO='/workspace/mcis-expert-offline-audit-20261114'
def source(item):return subprocess.check_output(['git','-C',REPO,'show',item['commit']+':'+item['path']])
@pytest.mark.parametrize('item',AUDIT['sourceFiles'],ids=lambda x:x['path'])
def test_exact_source_hash(item):assert hashlib.sha256(source(item)).hexdigest()==item['sha256']
def test_receipt_actual_counts_and_contiguous_run():
    rows=[json.loads(x) for x in source(AUDIT['sourceFiles'][2]).splitlines()]
    expected=AUDIT['historicalRecordedRun']
    assert len(rows)==expected['events']==15
    assert [r['sequence'] for r in rows]==list(range(1,16))
    assert {r['runId'] for r in rows}=={expected['runId']}
    assert sum(r['phase']=='model_request_started' for r in rows)==expected['modelRequestStartedEvents']==3
    assert sum(r['phase']=='model_request_returned' for r in rows)==expected['modelRequestReturnedEvents']==3
    last=rows[-1];assert last['phase']==expected['terminalPhase']=='accepted_pending_review'
    for key,n in [('models',3),('tools',2),('proposals',6),('citations',6)]:assert last[key]==n
    assert not expected['rerunThisAudit'] and not expected['providerIdentityAuthenticatedByThisAudit']
def test_new_skill_explicitly_mock_and_no_inherited_validation():
    text=source(AUDIT['sourceFiles'][3]).decode()
    assert '7dac16e4' in text and 'providerRequests=0' in text
    assert 'not for this new Skill version' in text and 'NOT a real-model run' in text

def intent():return dict(schema=preflight.SCHEMA,intentId='22222222-2222-4222-8222-222222222222',operation='prepare_public_two_round_review',packetSha256=preflight.PACKET_SHA)
@pytest.mark.parametrize('field',['historicalRecordedRun','currentSafeMetadataObservation','sourceFiles'])
def test_audit_cannot_be_attached_as_authority(field):
    d=intent();d[field]=AUDIT[field]
    with pytest.raises(preflight.IntentError):preflight.inspect(json.dumps(d).encode())
def test_valid_intent_stays_blocked_and_history_does_not_unblock_transports(monkeypatch):
    r=preflight.inspect(json.dumps(intent()).encode());assert r['status']=='blocked' and not r['executionAuthorized']
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:pytest.fail('client forbidden'))
    with pytest.raises(transport.TransportError,match='raw_key_disabled') as e:
        asyncio.run(transport.request([{'role':'user','content':json.dumps(AUDIT['historicalRecordedRun'])}],[],key='SYNTHETIC',deadline=time.monotonic()+1))
    assert not e.value.dispatched
    with pytest.raises(managed.ManagedError,match='platform_binding_unavailable'):managed.resolve(AUDIT['historicalRecordedRun']['runId'])

CHAIN=json.loads(Path('research/expert_remote/historical-chain.json').read_bytes())
@pytest.mark.parametrize('run',CHAIN['runs'],ids=lambda x:x['runId'])
def test_additional_historical_chain(run):
    raw=subprocess.check_output(['git','-C',REPO,'show',run['sourceCommit']+':'+run['path']])
    assert hashlib.sha256(raw).hexdigest()==run['sha256']
    rows=[json.loads(line) for line in raw.splitlines()]
    assert len(rows)==run['events'] and {row['runId'] for row in rows}=={run['runId']}
    assert rows[-1]['phase']==run['terminalPhase']
    assert sum(row['phase']=='model_request_started' for row in rows)==run['modelRequestsRecorded']
    assert rows[-1].get('tools')==run['toolsAtTerminal']
    assert rows[-1].get('proposals')==run['proposalsAtTerminal']
    assert run['rerunThisAudit'] is False
    assert CHAIN['historicalLostFourthRunRemainsUnknown'] is True and CHAIN['providerIdentityAuthenticated'] is False
