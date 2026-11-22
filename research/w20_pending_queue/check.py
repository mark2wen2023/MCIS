"""Real disposable SQLite queue regression; no HTTP/model/human review."""
import argparse,copy,hashlib,json,sys
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'service')]
from sqlalchemy import inspect
from research.expert_budget import four_chair
from research.expert_group.packet import _digest
from research.w20_pending_queue.adapter import FrozenSyntheticContext,TemporaryPendingQueue
from mcis_service.audit import service as audit

PINS={
 'research/expert_budget/four_chair.py':'b428bff809cabf7d8eec700bd2e499d86da1c553',
 'research/expert_group/packet.py':'ff2018dad2d58e9fe158f503ecd71a004c20e226',
 'service/mcis_service/db.py':'27daf52c0c6312495d03123f7c496bc688466a74',
 'service/mcis_service/agents/models.py':'298b2a58eb214d792fa6c36f99b4d17be2864a1f',
 'service/mcis_service/audit/service.py':'ef06ebec3b6b1f07fe748a6dc30eed2aa0453eeb',
 'service/mcis_service/audit/models.py':'8ab5d0dc9694281300affcb7d2d5ca04f5df5248',
 'service/mcis_service/common/timeutil.py':'73f85d80a0a514ea0b4b7adb597e03964862def2',
 'service/mcis_service/common/csjson.py':'08420730190b5711308f6b64ef142682e9009443',
}
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--ecfc-package',type=Path,required=True)
    p.add_argument('--locator',type=Path,required=True)
    p.add_argument('--temp-root',type=Path,required=True)
    args=p.parse_args()
    for name,expected in PINS.items():
        b=(ROOT/name).read_bytes()
        assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==expected,name
    context=FrozenSyntheticContext(args.ecfc_package,args.locator)
    synthetic={'items':[{'itemId':'draft','sourceText':context.registry['OBS-1']['excerpt'],
                        'citation':{'quote':context.registry['OBS-1']['excerpt']}}]}
    def host(binding=None, registry=None):
        registry=context.registry if registry is None else registry
        with patch.object(four_chair,'load_packet',return_value=b'synthetic'), \
             patch.object(four_chair,'_packet',return_value=copy.deepcopy(synthetic)), \
             patch.object(four_chair,'Ledger',return_value=Mock()), \
             patch.object(four_chair.os,'open',return_value=101),patch.object(four_chair.os,'close'):
            chair=four_chair.FourChair('never-created',clock=lambda:0)
        chair.bind_draft_simulated(context.binding if binding is None else binding)
        for n,alias in enumerate(['OBS-1','STA-1','STB-1','OBS-1']):
            chair._select_review_sources_simulated(registry,{'draft':alias})
            ticket=chair.issue()
            chair.submit_simulated(ticket['attemptId'],ticket['contextDigest'],[{
                'itemId':'draft','label':'supported' if n==1 else 'conflicted',
                'rationale':'SYNTHETIC_FREE_TEXT_NOT_FOR_PERSISTENCE',
                'uncertainty':'UNREVIEWED_SYNTHETIC_ONLY','quote':registry[alias]['excerpt']}])
        return chair
    case=context.binding['caseId']
    chair=host();receipt=chair.receipt()
    queue=TemporaryPendingQueue(context,chair,temp_root=args.temp_root)
    try:
        assert set(inspect(queue.db.engine).get_table_names())=={'agent_drafts','audit_events'}
        before=queue.reopen(case);assert before['drafts']==before['audit']==[]
        negatives={}
        for kind in ('wrong_case','old_version','old_generation','wrong_locator','wrong_quote','wrong_role'):
            incoming=copy.deepcopy(receipt);target=case
            if kind=='wrong_case':target='SYN-WRONG-CASE'
            elif kind=='old_version':incoming['opinions'][0]['draftBinding']['version']='old'
            elif kind=='old_generation':incoming['opinions'][0]['draftBindingGeneration']-=1
            elif kind=='wrong_locator':incoming['opinions'][0]['locatedReviewSources']['draft']['line']+=1
            elif kind=='wrong_quote':incoming['opinions'][0]['reviews'][0]['quote']='missing quote'
            else:incoming['opinions'][0]['role']='vessel'
            try:queue.enqueue(target,incoming)
            except ValueError as exc:negatives[kind]=str(exc)
            else:raise AssertionError(kind)
            assert queue.reopen(case)==before
            assert queue.reopen('SYN-WRONG-CASE')['drafts']==[]
        first=queue.enqueue(case,receipt);assert first['created']
        saved=queue.reopen(case);assert len(saved['drafts'])==len(saved['audit'])==1
        d=saved['drafts'][0]
        assert d['status']=='PendingReview' and d['reviewedBy'] is None and d['reviewedUtc'] is None
        assert d['caseId']==case and d['draftBinding']==context.binding and d['draftGeneration']==1
        assert len(d['opinions'])==4 and len(d['references'])==3 and d['locatedCitationPlaceCount']==3
        assert d['factVerified'] is False and d['sourceCountIsWeight'] is False
        assert saved['audit'][0]['entityId']==d['draftId'] and saved['audit'][0]['action']=='agent.synthetic_pending'
        assert saved['chain']['valid'] and saved['chain']['count']==1
        assert saved['audit'][0]['after']==d['handoffDigest']
        # Resolve every reference only using the trusted host's fixed original excerpt.
        for ref_id,ref in d['references'].items():
            matches=[s for s in context.registry.values() if s['sha256']==ref['sourceSha256']
                     and s['line']==ref['line'] and s['locator']==ref['locator']]
            assert len(matches)==1
            excerpt=matches[0]['excerpt'];quote=excerpt[ref['quoteStart']:ref['quoteStart']+ref['quoteLength']]
            assert hashlib.sha256(quote.encode()).hexdigest()==ref['quoteSha256']
            assert hashlib.sha256(excerpt.encode()).hexdigest()==ref['excerptSha256']
        def strings(v):
            if isinstance(v,str):yield v
            elif isinstance(v,dict):
                for item in v.values():yield from strings(item)
            elif isinstance(v,list):
                for item in v:yield from strings(item)
        stored=list(strings(saved))
        assert all('SYNTHETIC_FREE_TEXT_NOT_FOR_PERSISTENCE' not in v for v in stored)
        assert all('UNREVIEWED_SYNTHETIC_ONLY' not in v for v in stored)
        for src in context.registry.values():assert all(src['excerpt'] not in v for v in stored)
        assert 'payload' not in d and 'targetEntityType' not in d
        duplicate=queue.enqueue(case,receipt);assert duplicate=={'created':False,'draftId':first['draftId']}
        assert queue.reopen(case)==saved
        assert not hasattr(queue,'review') and not hasattr(queue,'confirm')
        assert not any(name in inspect(queue.db.engine).get_table_names() for name in ['cases','reports','ecfc_nodes'])
        success_path=str(queue.path)
    finally:queue.close()
    assert not Path(success_path).exists()
    # Current host at a different revision cannot enter the old-context queue.
    newer=dict(context.binding,version='synthetic-draft-v2')
    other=host(newer);queue=TemporaryPendingQueue(context,other,temp_root=args.temp_root)
    try:
        try:queue.enqueue(case,other.receipt())
        except ValueError as exc:assert str(exc)=='host_draft_binding'
        else:raise AssertionError('current different version')
        assert queue.reopen(case)['drafts']==queue.reopen(case)['audit']==[]
    finally:queue.close()
    # A genuine current chair receipt with an unverified host source set is not enough.
    unverified=copy.deepcopy(context.registry)
    unverified['STA-1']['line']+=1
    unverified['STA-1']['locator']=unverified['STA-1']['locator'].split('#L')[0]+'#L'+str(unverified['STA-1']['line'])
    bad_binding=dict(context.binding,sourceSetDigest=_digest(unverified))
    untrusted_host=host(bad_binding,unverified)
    edited_context=copy.deepcopy(context)
    edited_context.registry=unverified;edited_context.binding=bad_binding
    queue=TemporaryPendingQueue(edited_context,untrusted_host,temp_root=args.temp_root)
    try:
        try:queue.enqueue(case,untrusted_host.receipt())
        except ValueError as exc:assert str(exc)=='host_draft_binding'
        else:raise AssertionError('unverified current host source set')
        assert queue.reopen(case)['drafts']==queue.reopen(case)['audit']==[]
    finally:queue.close()
    # Actual append has flushed an audit row, then deterministic application failure.
    # No fake audit row, SQL trigger failure, or real-user confirmation is used.
    queue=TemporaryPendingQueue(context,chair,temp_root=args.temp_root)
    try:
        original_append=audit.append
        def fail_after_append(*a,**kw):
            original_append(*a,**kw)
            raise RuntimeError('synthetic failure after actual audit flush')
        with patch.object(audit,'append',side_effect=fail_after_append):
            try:queue.enqueue(case,receipt)
            except RuntimeError as exc:assert 'synthetic failure' in str(exc)
            else:raise AssertionError('missing failure')
        empty=queue.reopen(case);assert empty['drafts']==empty['audit']==[]
        assert empty['chain']['valid'] and empty['chain']['count']==0
        assert queue.enqueue(case,receipt)['created']
        retried=queue.reopen(case);assert len(retried['drafts'])==len(retried['audit'])==1
        assert retried['audit'][0]['seq']==1 and retried['chain']['valid']
    finally:queue.close()
    print(json.dumps({'scope':'real original DB/session/AgentDraftRow/audit in disposable SQLite',
      'fresh_connection_pending_and_audit':True,'duplicate_no_second_row':True,
      'rejections_without_success_rows':negatives,'current_host_revision_rejected':True,'current_unverified_source_host_rejected':True,
      'audit_flush_failure_full_rollback':True,'reference_resolution_count':3,
      'source_text_not_persisted':True,'business_tables_absent':True,
      'chair_storage_and_packet_loader':'MOCKED','queue_storage_and_audit':'REAL',
      'human_review':'NOT_RUN','production_identity':'NOT_RUN','models':'NOT_RUN'}))
if __name__=='__main__':main()
