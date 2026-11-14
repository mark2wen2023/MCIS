"""Pinned branch integration evidence, not a production receipt importer or model test."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import pytest
from research.expert_meeting.machine import Meeting, canonical, digest, verify_snapshot
from research.expert_bridge.protocol import Bridge
from research.expert_executor.executor import Executor
from research.expert_group.engine import ROLES, load_packet

ROOT=Path(__file__).resolve().parents[2]
BASE='a686c851333428d35374fb1596b6772a1cc6e9a8'
MEETING='649d8656c5f5b3aca93751468c108edd73f5ce61'
BRIDGE='0a4bf2224fc29afe08df9231aa0aad23dffca72f'
EXECUTOR='3125eaf4745cf4b2f83944a56a049823c032f436'
WORKBENCH='872815c240b6b709d8a1b1182d252ffe28ceca92'


def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()


def chain(rows):
    previous='0'*64
    for seq,row in enumerate(rows,1):
        assert row['seq']==seq and row['previousSha256']==previous
        assert digest({k:v for k,v in row.items() if k!='sha256'})==row['sha256']
        previous=row['sha256']


def shared_receipt_checks(r):
    """Test oracle for a complete known scripted run, not arbitrary-import acceptance."""
    assert r['receiptComplete'] and not r['realDeepSeekExecuted'] and not r['authenticityVerified']
    assert verify_snapshot(canonical(r['meetingSnapshot']))['localConsistencyVerified']
    state=r['meetingSnapshot']['state'];bridge=r['bridgeAudit']
    assert state['phase']=='completed_unverified' and state['mode']=='simulation_only'
    assert state['allocatedTurns']==4 and state['allocatedModelAllowance']==16 and state['allocatedToolAllowance']==32
    assert bridge['auditComplete'] and bridge['realModel'] is False and bridge['realPi'] is False
    chain(bridge['events']);chain(r['runtimeEvents'])
    accepted={v['ticketId']:v for round_ in state['rounds'] for v in round_['responses'].values()}
    sessions={s['ticketId']:s for s in bridge['sessions']};runs={x['ticketId']:x for x in r['runs']}
    assert len(accepted)==len(sessions)==len(runs)==4 and accepted.keys()==sessions.keys()==runs.keys()
    for ticket,session in sessions.items():
        assert session['phase']=='completed_unverified' and session['contextDigest']==accepted[ticket]['contextDigest']
        assert 0<=session['modelAttempts']<=4 and 0<=session['toolCalls']<=8
        events=[e for e in bridge['events'] if e['ticketId']==ticket]
        assert session['modelAttempts']==sum(e['phase']=='scripted_model_requested' for e in events)
        assert session['toolCalls']==sum(e['phase']=='tool_completed' for e in events)
        run=runs[ticket]
        assert run['status']=='completed_unverified' and run['exitObserved']==0 and run['leaderReaped'] and run['processStarted']
        assert run['receiptComplete'] and run['providerMode']=='scripted' and run['realDeepSeekExecuted'] is False
        delivered=[e for e in r['runtimeEvents'] if e['ticketId']==ticket and e['phase']=='context_written_to_pipe']
        assert len(delivered)==1 and delivered[0]['contextDigest']==accepted[ticket]['contextDigest']
    assert sum(s['modelAttempts'] for s in sessions.values())<=16
    assert sum(s['toolCalls'] for s in sessions.values())<=32
    return {'meetingId':state['meetingId'],'rounds':len(state['rounds']),'turns':len(runs),
            'allocatedModelAllowance':16,'modelProtocolAttempts':sum(s['modelAttempts'] for s in sessions.values()),
            'allocatedToolAllowance':32,'toolCalls':sum(s['toolCalls'] for s in sessions.values()),'realDeepSeekExecuted':False}


@pytest.fixture(scope='module')
def artifacts(tmp_path_factory, prohibit_real_transport):
    m=Meeting();b=Bridge(m);x=Executor(b)
    for _ in range(2):
        m.act({'type':'start_round'})
        for role in ROLES:x.run_turn(role)
    receipt=x.receipt()
    # Synthetic shape-only legacy UI control, never an old-engine execution path.
    packet=json.loads(load_packet())
    legacy={'runId':'00000000-0000-0000-0000-000000000001','status':'completed_unverified','outcome':'completed',
        'packetSha256':hashlib.sha256(load_packet()).hexdigest(),'manifestDigest':'71cd8de0fdf4a9e9137db32e7a299b125f7ad107b1c9d8073c34c31ee70c4052',
        'transportMocked':True,'realPi':True,'realModel':False,'provider':'deepseek','configuredModel':'deepseek-v4-pro','piVersion':'1.5.2',
        'modelIdentityVerified':False,'sourceLocatorVerified':False,'factActivated':False,'consensusComputed':False,'providerRequests':0,
        'artifactPolicy':'incomplete_without_valid_completion_manifest',
        'roles':[{'roleId':role,'runId':f'00000000-0000-0000-0000-00000000000{index+2}',
                  'status':'completed_unverified','modelCalls':3,'toolCalls':2,
                  'reviews':[{'itemId':item['itemId'],'label':'insufficient','quote':item['citation']['quote'],
                              'rationale':'SYNTHETIC LEGACY UI SHAPE ONLY, NOT RUNTIME OR MODEL EVIDENCE',
                              'uncertainty':'合成兼容性测试，不是真实模型意见。'} for item in packet['items']]}
                 for index,role in enumerate(ROLES)]}
    contradiction=deepcopy(legacy);contradiction.update(status='not_accepted',outcome='failed',transportMocked=False,realModel=False,providerRequests=0)
    contradiction['roles'][1].update(status='not_started',reviews=[],modelCalls=0,toolCalls=0)
    probe=subprocess.run(['node','tests_integration/EXPERTRESEARCH/workbench_probe.mjs'],cwd=ROOT,input=canonical({'receipt':receipt,'legacy':legacy,'contradiction':contradiction}),capture_output=True,check=True)
    observed=json.loads(probe.stdout)
    directory=tmp_path_factory.mktemp('expert-integration')
    (directory/'receipt.json').write_bytes(canonical(receipt))
    (directory/'observed.json').write_bytes(canonical(observed))
    (directory/'summary.json').write_bytes(canonical(shared_receipt_checks(receipt)))
    return receipt,legacy,observed,directory


@pytest.fixture(scope='module',autouse=True)
def prohibit_real_transport():
    monkeypatch=pytest.MonkeyPatch()
    import socket
    import research.expert_group.engine as engine
    def no(*a,**kw):raise AssertionError('real provider/network forbidden')
    monkeypatch.setattr(engine,'_remote',no);monkeypatch.setattr(engine,'run_group',no);monkeypatch.setattr(socket.socket,'connect',no)
    monkeypatch.setenv('DEEPSEEK_API_KEY','SYNTHETIC_TEST_NO_CREDENTIAL')
    yield
    monkeypatch.undo()


def test_pinned_dependency_chain_and_no_preview_stack():
    assert git('rev-parse',BASE+'^')=='178c998aa6d0181985e686d4d0161a33728fa167'
    assert git('rev-parse','178c998^')=='3aba2bf03e393909c611489ae573a887087637ac'
    assert git('rev-parse',EXECUTOR+'^')==BRIDGE
    assert git('rev-parse',BRIDGE+'^')==MEETING
    assert git('rev-parse',MEETING+'^')==BASE
    assert git('merge-base',EXECUTOR,WORKBENCH)==BASE
    assert git('rev-list','--count',BASE+'..'+EXECUTOR)=='3'
    assert git('rev-list','--count',BASE+'..'+WORKBENCH)=='2'


def test_only_shared_document_files_overlap():
    a=set(git('diff','--name-only',BASE,EXECUTOR).splitlines());b=set(git('diff','--name-only',BASE,WORKBENCH).splitlines())
    assert a&b=={'REQUESTS.md','ROADMAP.md'}


def test_workbench_patch_applicability_without_applying():
    delta=subprocess.check_output(['git','diff','--binary',BASE,WORKBENCH],cwd=ROOT)
    checked=subprocess.run(['git','apply','--check'],cwd=ROOT,input=delta,capture_output=True)
    # Documentation append context is reported separately; no actual patch is applied.
    print('WORKBENCH_PATCH_CHECK',checked.returncode,checked.stderr.decode().strip())
    for name in ['research/expert_workbench/model.ts','research/expert_workbench/app.ts']:
        delta=subprocess.check_output(['git','diff','--binary',BASE,WORKBENCH,'--',name],cwd=ROOT)
        subprocess.run(['git','apply','--check'],cwd=ROOT,input=delta,check=True,capture_output=True)


def test_shared_meeting_ticket_budget_and_runtime_binding(artifacts):
    receipt,_,_,_=artifacts
    summary=shared_receipt_checks(receipt)
    assert summary['modelProtocolAttempts']==12 and summary['toolCalls']==8


def test_previous_complete_round_visible_to_both_roles(artifacts):
    receipt,_,_,_=artifacts
    rows=[e for e in receipt['runtimeEvents'] if e['phase']=='context_written_to_pipe']
    assert [e['previousOpinionCount'] for e in rows]==[0,0,2,2]
    assert rows[0]['contextDigest']==rows[1]['contextDigest'] and rows[2]['contextDigest']==rows[3]['contextDigest']
    assert rows[0]['contextDigest']!=rows[2]['contextDigest']


def test_known_workbench_integration_gap_is_fail_closed(artifacts):
    _,_,probe,_=artifacts
    assert probe['legacyAccepted'] and probe['legacyWasVisible']
    assert not any(probe[k] for k in ['newReceiptAccepted','meetingAccepted','bridgeAccepted','contradictoryRemotePartialAccepted'])
    assert probe['failedMeetingLoadPreservesLegacy'] and probe['networkCalls']==0
    print('INTEGRATION_BLOCKED: frozen workbench has no meeting/budget/runtime receipt contract')


@pytest.mark.parametrize('change',[
    lambda r:r['bridgeAudit']['sessions'][0].update(modelAttempts=4),
    lambda r:r['bridgeAudit']['sessions'][0].update(contextDigest='f'*64),
    lambda r:r['runs'][0].update(ticketId='foreign-meeting-ticket'),
    lambda r:r['runs'][0].update(exitObserved=7),
    lambda r:r['bridgeAudit'].update(auditComplete=False),
    lambda r:r['runtimeEvents'][0].update(ticketId='foreign'),
    lambda r:r['meetingSnapshot']['state'].update(factActivated=True),
])
def test_cross_layer_inconsistency_detected_by_test_oracle(artifacts,change):
    receipt,_,_,_=artifacts;r=deepcopy(receipt);change(r)
    with pytest.raises((AssertionError,ValueError)):shared_receipt_checks(r)


def test_old_provider_budget_is_not_meeting_budget(artifacts):
    from research.expert_group.engine import LIMITS as OLD
    receipt,_,_,_=artifacts
    assert OLD['groupModelCalls']==8
    assert receipt['meetingSnapshot']['state']['limits']['modelAllowanceTotal']==16
    assert sum(s['modelAttempts'] for s in receipt['bridgeAudit']['sessions'])==12
    assert receipt['realDeepSeekExecuted'] is False
    assert all(r['providerMode']=='scripted' for r in receipt['runs'])
    assert not any('usage' in r for r in receipt['runs'])


def test_public_claims_are_not_reference_answer_labels(artifacts):
    packet=json.loads(load_packet())
    assert len(packet['items'])==3
    assert len({(i['sourceLocator']['url'],i['sourceLocator']['pdfPage'],i['sourceLocator']['printedPage']) for i in packet['items']})==1
    for item in packet['items']:
        assert set(item)=={'itemId','claim','sourceText','sourceSha256','sourceLocator','citation'}
        assert item['citation']['quote'] in item['sourceText']
        assert not ({'label','expectedLabel','goldLabel','rationale','counterexample'} & set(item))
    # Frozen 872815c lacks explicit human-written/counterexample labelling: known display gap.
    assert artifacts[2]['constructedClaimLabelPresent'] is False
