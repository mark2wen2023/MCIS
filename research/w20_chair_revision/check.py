"""Pure-memory FourChair method regression; mocked storage and packet loader only."""
import argparse, copy, hashlib, importlib.util, json, sys
from pathlib import Path
from unittest.mock import Mock, patch
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.expert_budget import four_chair as chair
from research.expert_group import packet

def load_locator(path):
    raw=path.read_bytes()
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()=='44fc5d82279db5fa3a3c748161f3122708e85668'
    spec=importlib.util.spec_from_file_location('fixed_locator',path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--ecfc-package',type=Path,required=True)
    p.add_argument('--locator',type=Path,required=True)
    args=p.parse_args()
    raw=(ROOT/'research/expert_group/packet.py').read_bytes()
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()=='ff2018dad2d58e9fe158f503ecd71a004c20e226'
    manifest=(args.ecfc_package/'FROZEN.sha256').read_bytes()
    assert hashlib.sha256(manifest).hexdigest()=='e91d31f34678ee2af880fb9931813677b93706332a03e96a0846943ef50235dd'
    for row in manifest.decode().splitlines():
        sha,name=row.split('  ')
        assert hashlib.sha256((args.ecfc_package/name).read_bytes()).hexdigest()==sha
    locator=load_locator(args.locator)
    data=json.loads((args.ecfc_package/'sample.json').read_text())
    registry={}
    for source in data['sources']:
        card=source['card'];locator.ROOT=args.ecfc_package/source['directory']
        assert locator.locate(card)=='LOCATED'
        b=card['sourceBinding']
        registry[b['recordId']]={'sha256':b['sha256'],'line':b['line'],
            'excerpt':card['content']['source']['excerpt']}
    draft={'caseId':data['caseId'],'version':'synthetic-draft-v1',
           'event':data['eventClaim'],'candidateLink':data['linkClaim']}
    binding={'caseId':data['caseId'],'version':draft['version'],
             'draftDigest':packet._digest(draft),'sourceSetDigest':packet._digest(registry)}
    assert binding['draftDigest']=='213b8bd46acf49a489bfc46523449d83a75751f5c714b925b10810d3e2765959'
    # Test-only synthetic packet injection. Never read the default public original.
    synthetic={'items':[{'itemId':key,'sourceText':src['excerpt'],
               'citation':{'quote':src['excerpt']}} for key,src in registry.items()]}
    def owner():
        ledger=Mock()
        with patch.object(chair,'load_packet',return_value=b'synthetic-test-only'), \
             patch.object(chair,'_packet',return_value=copy.deepcopy(synthetic)), \
             patch.object(chair,'Ledger',return_value=ledger), \
             patch.object(chair.os,'open',return_value=101), patch.object(chair.os,'close'):
            gate=chair.FourChair('never-created',clock=lambda:0)
        return gate,ledger
    def reviews(ticket,label='insufficient'):
        return [{'itemId':i['itemId'],'label':label,'rationale':'纯合成意见，非专业裁定',
          'uncertainty':'矛盾陈述与因果待人工复核','quote':i['citation']['quote']}
          for i in ticket['context']['packet']['items']]
    def reject(code,call):
        try:call()
        except chair.ChairError as exc:assert str(exc)==code
        else:raise AssertionError(code)
    # Existing issue and submit methods, with actual generated active attempt IDs.
    gate,ledger=owner();gate.bind_draft_simulated(binding);old=gate.issue()
    frozen=copy.deepcopy(old)
    revised=copy.deepcopy(binding);revised['version']='synthetic-draft-v2'
    revised_draft=dict(draft,version=revised['version']);revised['draftDigest']=packet._digest(revised_draft)
    gate.bind_draft_simulated(revised)
    reject('stale_draft_binding',lambda:gate.submit_simulated(old['attemptId'],old['contextDigest'],reviews(old)))
    assert gate._active==frozen and gate.receipt()['opinions']==[]
    assert ledger.settle.call_count==0
    # No automatic restart/reassignment after stale input; original ticket is retained.
    reject('not_ready',gate.issue);gate.stop()
    # A same-version changed source set is also stale.
    gate,ledger=owner();gate.bind_draft_simulated(binding);ticket=gate.issue()
    changed=dict(binding,sourceSetDigest='0'*64);gate.bind_draft_simulated(changed)
    reject('stale_draft_binding',lambda:gate.submit_simulated(ticket['attemptId'],ticket['contextDigest'],reviews(ticket)))
    assert ledger.settle.call_count==0;gate.stop()
    # Actual A -> B -> A: equal final fields do not revive the issued ticket.
    gate,ledger=owner();gate.bind_draft_simulated(binding);ticket=gate.issue()
    frozen=copy.deepcopy(ticket)
    gate.bind_draft_simulated(revised);gate.bind_draft_simulated(copy.deepcopy(binding))
    reject('stale_draft_binding',lambda:gate.submit_simulated(ticket['attemptId'],ticket['contextDigest'],reviews(ticket)))
    assert gate._active==frozen and gate.receipt()['opinions']==[]
    assert ledger.settle.call_count==0 and ledger.reserve.call_count==1
    assert ticket['context']['draftBindingGeneration']==1 and gate._draft_generation==3
    reject('not_ready',gate.issue)
    stopped=gate.stop();assert stopped['phase']=='stopped_by_operator'
    assert stopped['opinions']==[] and gate._active is None and ledger.stop.call_count==1
    # Positive idempotence: equal fields before/after issue retain the issued generation.
    gate,ledger=owner();gate.bind_draft_simulated(binding)
    gate.bind_draft_simulated(copy.deepcopy(binding));ticket=gate.issue()
    frozen=copy.deepcopy(ticket);gate.bind_draft_simulated(copy.deepcopy(binding))
    assert gate._active==frozen and gate._draft_generation==1
    state=gate.submit_simulated(ticket['attemptId'],ticket['contextDigest'],reviews(ticket))
    assert ledger.settle.call_count==1 and len(state['opinions'])==1
    assert state['opinions'][0]['attemptId']==ticket['attemptId']
    assert state['opinions'][0]['draftBinding']==binding
    assert state['opinions'][0]['draftBindingGeneration']==1
    gate.stop()
    # Current-version opinions preserve both opposite synthetic statements separately.
    gate,ledger=owner();binding=copy.deepcopy(revised)
    original=copy.deepcopy(binding);gate.bind_draft_simulated(binding)
    binding['version']='caller-mutated'
    for n in range(4):
        ticket=gate.issue()
        assert ticket['context']['draftBinding']==original
        assert ticket['context']['role']==chair.ROLES[n]
        reject('ticket_binding',lambda:gate.submit_simulated('not-issued',ticket['contextDigest'],reviews(ticket)))
        before=ledger.settle.call_count
        wrong=reviews(ticket);wrong[1]['quote']=registry['STB-1']['excerpt']
        try:gate.submit_simulated(ticket['attemptId'],ticket['contextDigest'],wrong)
        except packet.GroupError as exc:assert exc.code=='review_quote'
        else:raise AssertionError('cross-source quote accepted')
        assert ledger.settle.call_count==before
        state=gate.submit_simulated(ticket['attemptId'],ticket['contextDigest'],reviews(ticket,'supported' if n==0 else 'conflicted'))
        assert state['opinions'][-1]['attemptId']==ticket['attemptId']
        assert state['opinions'][-1]['draftBinding']==original
    assert len(state['opinions'])==4 and ledger.settle.call_count==4
    assert all(not s['factVerified'] for s in state['summary'])
    assert all(s['disputedLabels'] for s in state['summary'] if s['round']==1)
    quotes={r['itemId']:r['quote'] for r in state['opinions'][0]['reviews']}
    assert quotes['STA-1']==registry['STA-1']['excerpt'] and quotes['STB-1']==registry['STB-1']['excerpt']
    assert quotes['STA-1']!=quotes['STB-1']
    assert len({(s['sha256'],s['line']) for s in registry.values()})==3
    reject('draft_binding_phase',lambda:gate.bind_draft_simulated(revised))
    assert not state['modelExecuted'] and not state['opinionsPersisted']
    gate.stop()
    # Optional binding leaves legacy context/opinion shape unchanged.
    gate,ledger=owner();ticket=gate.issue();assert 'draftBinding' not in ticket['context'] and 'draftBindingGeneration' not in ticket['context']
    state=gate.submit_simulated(ticket['attemptId'],ticket['contextDigest'],reviews(ticket))
    assert 'draftBinding' not in state['opinions'][0] and 'draftBindingGeneration' not in state['opinions'][0];gate.stop()
    print(json.dumps({'scope':'actual FourChair methods with mocked storage and synthetic packet loader',
      'aba_rejected_without_settlement_or_migration':True,'identical_rebind_accepted':True,
      'stale_draft_rejected_before_settle':True,'changed_source_set_rejected':True,
      'current_attributed_opinions':4,'located_byte_positions':3,
      'opposed_excerpts_preserved':True,'wrong_ticket_and_cross_source_quote_rejected':True,
      'default_binding_absent':True,'source_independence':'NOT_ASSESSED',
      'causal_judgment':'NOT_RUN','real_ledger':'NOT_RUN','human_confirmation':'NOT_RUN'}))
if __name__=='__main__':main()
