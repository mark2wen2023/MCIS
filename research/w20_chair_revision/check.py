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
    def owner(packet_override=None):
        ledger=Mock()
        with patch.object(chair,'load_packet',return_value=b'synthetic-test-only'), \
             patch.object(chair,'_packet',return_value=copy.deepcopy(synthetic if packet_override is None else packet_override)), \
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
    # New internal source selection uses only the already located frozen originals.
    located={}
    for source in data['sources']:
        card=source['card'];key=card['sourceBinding']['recordId']
        assert json.loads(registry[key]['excerpt'])['caseId']==data['caseId']
        located[key]={**registry[key], 'locator':source['directory']+'/'+card['content']['source']['locator']}
    located['OBS-ALIAS']=copy.deepcopy(located['OBS-1'])
    source_binding={**original,'sourceSetDigest':packet._digest(located)}
    one_item={'items':[{'itemId':'draft','sourceText':located['OBS-1']['excerpt'],
                       'citation':{'quote':located['OBS-1']['excerpt']}}]}
    def selected_review(ticket,label='supported'):
        return [{'itemId':item_id,'label':label,'rationale':'纯合成席位意见，非专业判定',
                 'uncertainty':'因果待人工复核','quote':src['excerpt']}
                for item_id,src in ticket['context']['locatedReviewSources'].items()]
    def quote_reject(gate,ticket,quote):
        before=gate.receipt();settles=gate._ledger.settle.call_count
        rs=selected_review(ticket);rs[0]['quote']=quote
        try:gate.submit_simulated(ticket['attemptId'],ticket['contextDigest'],rs)
        except packet.GroupError as exc:assert exc.code=='review_quote'
        else:raise AssertionError('unselected or joined quote accepted')
        assert gate._ledger.settle.call_count==settles and gate.receipt()==before
    # Wrong registry digest/unknown reference are not silently accepted.
    gate,ledger=owner(one_item);gate.bind_draft_simulated(source_binding)
    changed=copy.deepcopy(located);changed['OBS-1']['locator']='changed#L1'
    reject('source_set_binding',lambda:gate._select_review_sources_simulated(changed,{'draft':'OBS-1'}))
    reject('source_selection_unknown',lambda:gate._select_review_sources_simulated(located,{'draft':'missing'}))
    assert ledger.reserve.call_count==ledger.settle.call_count==0;gate.stop()
    # Four unanimous opinions, one byte location even when the host selects an alias.
    gate,ledger=owner(one_item);gate.bind_draft_simulated(source_binding)
    for n in range(4):
        choice='OBS-ALIAS' if n==2 else 'OBS-1'
        gate._select_review_sources_simulated(located,{'draft':choice});ticket=gate.issue()
        assert ticket['context']['locatedReviewSources']['draft']['sourceId']==choice
        reject('source_selection_phase',lambda:gate._select_review_sources_simulated(located,{'draft':'STA-1'}))
        # Other registered text is not permitted merely because it is available.
        quote_reject(gate,ticket,located['STA-1']['excerpt'])
        boundary=located['OBS-1']['excerpt'][-24:]+'\n'+located['STA-1']['excerpt'][:24]
        assert boundary not in located['OBS-1']['excerpt']
        quote_reject(gate,ticket,boundary)
        state=gate.submit_simulated(ticket['attemptId'],ticket['contextDigest'],selected_review(ticket))
        op=state['opinions'][-1]
        assert op['role']==chair.ROLES[n] and op['attemptId']==ticket['attemptId']
        assert op['locatedReviewSources']==ticket['context']['locatedReviewSources']
    assert len(state['opinions'])==4 and state['locatedCitationPlaceCount']==1
    assert not state['sourceCountIsWeight'] and state['sourceIndependence']=='NOT_ASSESSED'
    assert all(not x['factVerified'] for x in state['summary'])
    assert not state['summary'][0]['disputedLabels'];gate.stop()
    # Opposite source statements/opinions remain separate, with no vote-to-cause.
    gate,ledger=owner(one_item);gate.bind_draft_simulated(source_binding)
    for n,choice in enumerate(['STA-1','STB-1','OBS-1','OBS-ALIAS']):
        gate._select_review_sources_simulated(located,{'draft':choice});ticket=gate.issue()
        correct=selected_review(ticket,'supported' if n==0 else 'conflicted')
        # Mutating the returned ticket cannot replace the host-frozen selection.
        frozen=copy.deepcopy(ticket['context']['locatedReviewSources'])
        ticket['context']['locatedReviewSources']['draft']['excerpt']='changed returned copy'
        state=gate.submit_simulated(ticket['attemptId'],ticket['contextDigest'],correct)
        assert state['opinions'][-1]['locatedReviewSources']==frozen
    assert state['locatedCitationPlaceCount']==3 and len(state['opinions'])==4
    assert state['summary'][0]['disputedLabels'] and not state['summary'][0]['factVerified']
    for n,key in [(0,'STA-1'),(1,'STB-1')]:
        src=state['opinions'][n]['locatedReviewSources']['draft']
        assert src['sourceId']==key and src['excerpt']==located[key]['excerpt']
        assert src['locator']==located[key]['locator']
    state['opinions'][0]['locatedReviewSources'].clear()
    assert gate.receipt()['opinions'][0]['locatedReviewSources'];gate.stop()
    # Two explicitly selected excerpts still cannot be borrowed or concatenated.
    two_items={'items':[{'itemId':key,'sourceText':located[src]['excerpt'],
                        'citation':{'quote':located[src]['excerpt']}}
                       for key,src in [('left','STA-1'),('right','STB-1')]]}
    gate,ledger=owner(two_items);gate.bind_draft_simulated(source_binding)
    gate._select_review_sources_simulated(located,{'left':'STA-1','right':'STB-1'})
    ticket=gate.issue()
    quote_reject(gate,ticket,located['STB-1']['excerpt'])
    boundary=located['STA-1']['excerpt'][-24:]+'\n'+located['STB-1']['excerpt'][:24]
    assert boundary in located['STA-1']['excerpt']+'\n'+located['STB-1']['excerpt']
    assert all(boundary not in located[k]['excerpt'] for k in ('STA-1','STB-1'))
    quote_reject(gate,ticket,boundary)
    state=gate.submit_simulated(ticket['attemptId'],ticket['contextDigest'],selected_review(ticket))
    assert ledger.settle.call_count==1 and state['locatedCitationPlaceCount']==2;gate.stop()
    # Revision invalidates selected-source ticket; no reassignment or acceptance.
    gate,ledger=owner(one_item);gate.bind_draft_simulated(source_binding)
    gate._select_review_sources_simulated(located,{'draft':'STA-1'});ticket=gate.issue()
    gate.bind_draft_simulated(dict(source_binding,version='synthetic-draft-v3'))
    assert gate._review_sources is None
    reject('stale_draft_binding',lambda:gate.submit_simulated(ticket['attemptId'],ticket['contextDigest'],selected_review(ticket)))
    assert ledger.settle.call_count==0 and gate.receipt()['opinions']==[];gate.stop()
    # Default path still emits no source-selection or count fields.
    gate,ledger=owner();ticket=gate.issue()
    assert 'locatedReviewSources' not in ticket['context']
    state=gate.submit_simulated(ticket['attemptId'],ticket['contextDigest'],reviews(ticket))
    assert 'locatedReviewSources' not in state['opinions'][0]
    assert 'locatedCitationPlaceCount' not in state;gate.stop()
    print(json.dumps({'scope':'actual FourChair methods with mocked storage and synthetic packet loader',
      'per_review_selected_excerpt_only':True,'four_opinions_one_citation_place':True,
      'opposed_sources_separate':True,'source_selection_revision_rejected':True,
      'aba_rejected_without_settlement_or_migration':True,'identical_rebind_accepted':True,
      'stale_draft_rejected_before_settle':True,'changed_source_set_rejected':True,
      'current_attributed_opinions':4,'located_byte_positions':3,
      'opposed_excerpts_preserved':True,'wrong_ticket_and_cross_source_quote_rejected':True,
      'default_binding_absent':True,'source_independence':'NOT_ASSESSED',
      'causal_judgment':'NOT_RUN','real_ledger':'NOT_RUN','human_confirmation':'NOT_RUN'}))
if __name__=='__main__':main()
