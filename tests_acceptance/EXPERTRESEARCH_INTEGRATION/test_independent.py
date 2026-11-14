"""Independent integration audit. No remote transport, old-engine execution, or merge."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
from copy import deepcopy
import pytest
from research.expert_meeting.machine import Meeting, canonical, digest, verify_snapshot
from research.expert_bridge.protocol import Bridge
from research.expert_executor.executor import Executor
from research.expert_group import engine

ROOT=Path(__file__).resolve().parents[2]
BASE='a686c851333428d35374fb1596b6772a1cc6e9a8'
WORKBENCH='872815c240b6b709d8a1b1182d252ffe28ceca92'
EXECUTOR='3125eaf4745cf4b2f83944a56a049823c032f436'

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)


def test_exact_parent_chain_and_no_preview_dependency():
    expected=[EXECUTOR,'0a4bf2224fc29afe08df9231aa0aad23dffca72f','649d8656c5f5b3aca93751468c108edd73f5ce61',BASE,'178c998aa6d0181985e686d4d0161a33728fa167','3aba2bf03e393909c611489ae573a887087637ac']
    for child,parent in zip(expected,expected[1:]):assert git('rev-parse',child+'^').decode().strip()==parent
    assert git('merge-base',EXECUTOR,WORKBENCH).decode().strip()==BASE
    assert git('rev-list','--count',BASE+'..'+EXECUTOR).strip()==b'3'
    assert git('rev-list','--count',BASE+'..'+WORKBENCH).strip()==b'2'


def test_patch_conflicts_really_limited_to_documentation():
    delta=git('diff','--binary',BASE,WORKBENCH)
    full=subprocess.run(['git','apply','--check'],cwd=ROOT,input=delta,capture_output=True)
    assert full.returncode!=0
    errors=full.stderr.decode().splitlines()
    assert errors and all('REQUESTS.md' in line or 'ROADMAP.md' in line for line in errors)
    code=git('diff','--binary',BASE,WORKBENCH,'--','.',':(exclude)REQUESTS.md',':(exclude)ROADMAP.md')
    check=subprocess.run(['git','apply','--check'],cwd=ROOT,input=code,capture_output=True)
    assert check.returncode==0,check.stderr.decode()
    assert not (ROOT/'research/expert_workbench').exists()


def test_frozen_packet_engine_runner_and_tools_have_no_answer_patch():
    for name in ['public-packet.json','engine.py','pi-runner.mjs']:
        path='research/expert_group/'+name
        assert (ROOT/path).read_bytes()==git('show',BASE+':'+path)
    packet=json.loads(engine.load_packet())
    assert hashlib.sha256(engine.load_packet()).hexdigest()=='1dc5f6ccd93da013863abfd399b8e3f8682d2532e62d335eaa23cd5e18d8790e'
    for item in packet['items']:
        assert set(item)=={'itemId','claim','sourceText','sourceSha256','sourceLocator','citation'}
    assert len({(i['sourceLocator']['url'],i['sourceLocator']['pdfPage'],i['sourceLocator']['printedPage']) for i in packet['items']})==1
    assert len({i['sourceText'] for i in packet['items']})==1


@pytest.fixture(scope='module')
def observed():
    import socket
    patch=pytest.MonkeyPatch();requests=[]
    def deny(*a,**k):raise AssertionError('forbidden provider/network/legacy runtime')
    patch.setattr(engine,'run_group',deny);patch.setattr(engine,'_remote',deny);patch.setattr(socket.socket,'connect',deny)
    meeting=Meeting();bridge=Bridge(meeting);executor=Executor(bridge)
    dispatch=bridge.from_runner
    def inspect(ticket,request):
        response=dispatch(ticket,request)
        if response.get('kind')=='scripted_model_request':requests.append(deepcopy(response))
        return response
    patch.setattr(bridge,'from_runner',inspect)
    try:
        for _ in range(2):
            meeting.act({'type':'start_round'})
            for role in engine.ROLES:executor.run_turn(role)
        yield executor.receipt(),requests
    finally:patch.undo()


def test_actual_four_pi_processes_and_scripted_only_counts(observed):
    receipt,requests=observed
    assert len(receipt['runs'])==4 and len({r['pid'] for r in receipt['runs']})==4
    assert all(r['processStarted'] and r['exitObserved']==0 and r['leaderReaped'] and r['groupKillSent'] and r['providerMode']=='scripted' for r in receipt['runs'])
    assert all(not Path('/proc/'+str(r['pid'])).exists() for r in receipt['runs'])
    assert len(requests)==sum(s['modelAttempts'] for s in receipt['bridgeAudit']['sessions'])==12
    assert sum(s['toolCalls'] for s in receipt['bridgeAudit']['sessions'])==8
    assert all(r['realProviderInvoked'] is False for r in requests)
    assert receipt['realDeepSeekExecuted'] is False and receipt['authenticityVerified'] is False
    assert verify_snapshot(canonical(receipt['meetingSnapshot']))['phase']=='completed_unverified'


def test_actual_context_and_input_messages_contain_no_reference_answers(observed):
    receipt,requests=observed
    groups=[requests[i:i+3] for i in range(0,12,3)]
    contexts=[]
    packet=json.loads(engine.load_packet())
    for group in groups:
        assert len(group[0]['messages'])==2
        tools=[json.loads(message['content']) for message in group[1]['messages'] if message['role']=='tool']
        assert len(tools)==1 and tools[0]['packet']==packet
        assert set(tools[0])=={'packet','meetingContext','contextDigest'}
        context=tools[0]['meetingContext'];contexts.append(context)
        assert context['opinionsAreUntrustedData'] is True and context['factActivated'] is False
        assert tools[0]['contextDigest']==digest(context)
        assert 'SYNTHETIC LEGACY UI SHAPE ONLY' not in canonical(group).decode()
        for forbidden in ['referenceAnswers','expectedLabel','goldLabel','counterexample']:
            assert forbidden not in canonical(group).decode()
    assert [len(c['previousRoundOpinions']) for c in contexts]==[0,0,2,2]
    assert contexts[0]==contexts[1] and contexts[2]==contexts[3]
    previous=receipt['meetingSnapshot']['state']['rounds'][0]['responses']
    assert contexts[2]['previousRoundOpinions']==previous
    for opinion in previous.values():
        assert opinion['source']=='scripted_simulation'
        assert all('SCRIPTED FIXTURE' in row['rationale'] for row in opinion['reviews'])


def legacy():
    packet=json.loads(engine.load_packet())
    return {'runId':'00000000-0000-0000-0000-000000000021','status':'completed_unverified','outcome':'completed','packetSha256':engine.PACKET_SHA256,'manifestDigest':'71cd8de0fdf4a9e9137db32e7a299b125f7ad107b1c9d8073c34c31ee70c4052','transportMocked':True,'realPi':True,'realModel':False,'provider':'deepseek','configuredModel':'deepseek-v4-pro','piVersion':'1.5.2','modelIdentityVerified':False,'sourceLocatorVerified':False,'factActivated':False,'consensusComputed':False,'providerRequests':0,'artifactPolicy':'incomplete_without_valid_completion_manifest','roles':[{'roleId':role,'runId':f'00000000-0000-0000-0000-00000000002{i+2}','status':'completed_unverified','modelCalls':3,'toolCalls':2,'reviews':[{'itemId':item['itemId'],'label':'insufficient','quote':item['citation']['quote'],'rationale':'INDEPENDENT SYNTHETIC UI ONLY','uncertainty':'未核实，非模型运行记录'} for item in packet['items']]} for i,role in enumerate(engine.ROLES)]}


def test_frozen_workbench_rejects_new_receipt_without_adapting_or_overwriting(observed):
    receipt,_=observed;old=legacy();contradiction=deepcopy(old);contradiction.update(realModel=False,transportMocked=False)
    out=subprocess.run(['node','tests_integration/EXPERTRESEARCH/workbench_probe.mjs'],cwd=ROOT,input=canonical({'receipt':receipt,'legacy':old,'contradiction':contradiction}),capture_output=True,check=True)
    report=json.loads(out.stdout)
    assert report['legacyAccepted'] and report['legacyWasVisible'] and report['failedMeetingLoadPreservesLegacy']
    assert not any(report[k] for k in ['newReceiptAccepted','meetingAccepted','bridgeAccepted','contradictoryRemotePartialAccepted'])
    assert report['networkCalls']==0 and report['workbenchCommit']==WORKBENCH
    for path,sha in report['blobs'].items():assert hashlib.sha256(git('show',WORKBENCH+':'+path)).hexdigest()==sha
    assert report['constructedClaimLabelPresent'] is False


def test_oracle_is_test_only_and_remote_adapter_is_unimplemented_design():
    source=(ROOT/'tests_integration/EXPERTRESEARCH/test_integration.py').read_text()
    tree=ast.parse(source)
    helper=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='shared_receipt_checks')
    assert 'not arbitrary-import acceptance' in ast.get_docstring(helper)
    for path in (ROOT/'research').rglob('*.py'):
        if 'node_modules' not in path.parts:assert 'shared_receipt_checks' not in path.read_text()
    design=(ROOT/'tests_integration/EXPERTRESEARCH/REMOTE_ADAPTER_DESIGN.md').read_text()
    for text in ['尚未实现','不授权网络调用','不得调用旧engine._remote','usage缺失标unknown','不可声称真实DeepSeek会议通过']:assert text in design
    readme=(ROOT/'tests_integration/EXPERTRESEARCH/README.md').read_text()
    assert '不是生产导入校验器' in readme and '不是已接通的真实专家会议' in readme
