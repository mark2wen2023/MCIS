"""Same-case synthetic FourChair -> projection; storage/packet loader mocked."""
import argparse, copy, hashlib, importlib.util, json, sys
from pathlib import Path
from unittest.mock import Mock, patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from research.expert_budget import four_chair as chair
from research.expert_group import packet
from research.w20_four_review.project import project, ProjectionError

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--ecfc-package',type=Path,required=True)
    p.add_argument('--locator',type=Path,required=True)
    p.add_argument('--view',action='store_true',help='Print the synthetic pending projection instead of the check summary')
    args=p.parse_args()
    pins={"research/expert_budget/four_chair.py":"b428bff809cabf7d8eec700bd2e499d86da1c553","research/expert_budget/ledger.py":"cd25595ac5d04055008282ecb26a937035ab4581","research/expert_group/packet.py":"ff2018dad2d58e9fe158f503ecd71a004c20e226"}
    for name,expected in pins.items():
        raw=(ROOT/name).read_bytes()
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==expected
    raw=args.locator.read_bytes()
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()=='44fc5d82279db5fa3a3c748161f3122708e85668'
    spec=importlib.util.spec_from_file_location('locator',args.locator)
    locator=importlib.util.module_from_spec(spec);spec.loader.exec_module(locator)
    manifest=(args.ecfc_package/'FROZEN.sha256').read_bytes()
    assert hashlib.sha256(manifest).hexdigest()=='e91d31f34678ee2af880fb9931813677b93706332a03e96a0846943ef50235dd'
    for line in manifest.decode().splitlines():
        sha,name=line.split('  ')
        assert hashlib.sha256((args.ecfc_package/name).read_bytes()).hexdigest()==sha
    data=json.loads((args.ecfc_package/'sample.json').read_text())
    registry={}
    for source in data['sources']:
        locator.ROOT=args.ecfc_package/source['directory']
        card=source['card'];assert locator.locate(card)=='LOCATED'
        b=card['sourceBinding']
        assert json.loads(card['content']['source']['excerpt'])['caseId']==data['caseId']
        registry[b['recordId']]={'sha256':b['sha256'],'line':b['line'],
          'locator':source['directory']+'/'+card['content']['source']['locator'],
          'excerpt':card['content']['source']['excerpt']}
    synthetic={'items':[{'itemId':key,'sourceText':src['excerpt'],
      'citation':{'quote':src['excerpt']}} for key,src in registry.items()]}
    ledger=Mock()
    with patch.object(chair,'load_packet',return_value=b'synthetic-test-only'), \
         patch.object(chair,'_packet',return_value=copy.deepcopy(synthetic)), \
         patch.object(chair,'Ledger',return_value=ledger), \
         patch.object(chair.os,'open',return_value=101),patch.object(chair.os,'close'):
        gate=chair.FourChair('never-created',clock=lambda:0)
    binding={'caseId':data['caseId'],'version':'synthetic-draft-v1',
      'draftDigest':packet._digest({'caseId':data['caseId'],'version':'synthetic-draft-v1',
        'event':data['eventClaim'],'candidateLink':data['linkClaim']}),
      'sourceSetDigest':packet._digest(registry)}
    gate.bind_draft_simulated(binding)
    gate._select_review_sources_simulated(registry,{key:key for key in registry})
    tickets=[]
    for n,role in enumerate(chair.ROLES):
        ticket=gate.issue();tickets.append(copy.deepcopy(ticket))
        reviews=[{'itemId':key,'label':['supported','conflicted','insufficient','conflicted'][n],
          'quote':src['excerpt'],'rationale':'开发可见合成意见，不是专业裁定',
          'uncertainty':role+'：因果与矛盾待人工复核'} for key,src in registry.items()]
        gate.submit_simulated(ticket['attemptId'],ticket['contextDigest'],reviews)
    receipt=gate.receipt()
    host={'meetingId':receipt['meetingId'],'binding':binding,'generation':1,
          'tickets':tickets,'registry':registry}
    frozen=copy.deepcopy((receipt,host))
    view=project(receipt,host)
    assert (receipt,host)==frozen and ledger.settle.call_count==4
    assert len(view['rows'])==12
    assert {x['role'] for x in view['rows']}==set(chair.ROLES)
    assert all(x['disputedLabels'] and not x['factVerified'] for x in view['comparison'])
    assert all(x['uncertainty'].startswith(x['role']) and x['status']=='pending_human_review'
               and not x['semanticSupportVerified'] for x in view['rows'])
    assert not view['consensusComputed'] and not view['stopRequested']
    assert view['hostEvidenceAvailability']=='BLOCKED_NO_INTERFACE'
    assert view['rows'][0]['declaredLabel']=='supported' and view['rows'][3]['declaredLabel']=='conflicted'
    assert view['rows'][0]['source']==receipt['opinions'][0]['locatedReviewSources'][view['rows'][0]['itemId']]
    checks=['actual_four_chair_same_case','opposed_seats_and_uncertainty_retained',
      'exact_sources_and_binding_retained','pending_without_fabricated_stop','no_input_or_ledger_mutation']
    mutations=[
      ('packet_identity',lambda r,h:r.update(packetSha256='0'*64)),
      ('duplicate_seat',lambda r,h:r['opinions'][1].update(role=r['opinions'][0]['role'])),
      ('schema',lambda r,h:r.update(schema='two-seat')),
      ('wrong_case',lambda r,h:r['opinions'][0]['draftBinding'].update(caseId='OTHER')),
      ('old_generation',lambda r,h:r['opinions'][0].update(draftBindingGeneration=0)),
      ('wrong_evidence_digest',lambda r,h:r['opinions'][0]['locatedReviewSources']['OBS-1'].update(sha256='0'*64)),
      ('wrong_locator',lambda r,h:r['opinions'][0]['locatedReviewSources']['OBS-1'].update(locator='wrong#L1')),
      ('unknown_source',lambda r,h:r['opinions'][0]['locatedReviewSources']['OBS-1'].update(sourceId='UNKNOWN')),
      ('wrong_round',lambda r,h:r['opinions'][0].update(round=2)),
      ('wrong_ticket',lambda r,h:r['opinions'][0].update(attemptId='UNKNOWN')),
      ('borrowed_quote',lambda r,h:r['opinions'][0]['reviews'][0].update(quote=registry['STA-1']['excerpt'])),
      ('fact_upgrade',lambda r,h:r['summary'][0].update(factVerified=True)),
      ('invented_unavailable',lambda r,h:r.update(evidenceUnavailable=True)),
      ('invented_host_signal',lambda r,h:h.update(evidenceUnavailable=True)),
      ('missing_opinion',lambda r,h:r['opinions'].pop()),
    ]
    for name,mutate in mutations:
        r,h=copy.deepcopy(frozen);mutate(r,h)
        try:project(r,h)
        except ProjectionError:checks.append('rejected_'+name)
        else:raise AssertionError(name)
    view['rows'][0]['source']['excerpt']='changed display copy'
    assert project(receipt,host)['rows'][0]['source']['excerpt']!='changed display copy'
    checks.append('projection_copy_isolation')
    bad={key:key for key in registry};bad['OBS-1']='UNKNOWN'
    try:gate._select_review_sources_simulated(registry,bad)
    except chair.ChairError as e:assert str(e)=='source_selection_unknown'
    else:raise AssertionError('unknown source accepted by chair')
    assert gate.receipt()==receipt and ledger.settle.call_count==4
    checks.append('chair_unknown_source_still_rejected')
    if args.view:
        print(json.dumps(project(receipt,host),ensure_ascii=False,indent=2));return
    print(json.dumps({'scope':'pure synthetic first-round read-only projection',
      'passed':len(checks),'checks':checks,'roles':list(chair.ROLES),'rows':12,
      'status':project(receipt,host)['status'],'hostEvidenceAvailability':'BLOCKED_NO_INTERFACE',
      'stopRequested':False,'realLedger':False,'modelExecuted':False,'humanReviewPerformed':False},
      ensure_ascii=False,indent=2))

if __name__=='__main__':main()
