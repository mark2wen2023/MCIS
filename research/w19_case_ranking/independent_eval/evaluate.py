"""Offline independent evaluation: executes pinned original rank.py, no algorithm copy."""
import hashlib, json, sys
from pathlib import Path
from fractions import Fraction
ROOT = Path(__file__).resolve().parent
FIXTURE_SHA = '98e01b4077e8827ad0678a58b4a32d71a8acda0aafca13a60a36bc8183d5a3ad'
LABEL_SHA = 'c5caeb0c763230512e4ff0460abe70c3a092974f3a2a7ddf3f7a0025121e6484'
BLOB = 'df014103e47dcb1bb4a1115c6d05e1d4d30385c5'
def canonical(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
def ratio(a,b):
    return None if not b else {'numerator':a,'denominator':b,'value':a/b}
def evaluate():
    raw=(ROOT/'fixtures.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==FIXTURE_SHA, 'fixture mismatch'
    f=json.loads(raw)
    labels={s['scenario_id']:s['gold_labels'] for s in f['scenarios']}
    assert hashlib.sha256(canonical(labels)).hexdigest()==LABEL_SHA, 'labels changed'
    source=(ROOT.parent/'rank.py').read_bytes()
    assert hashlib.sha1(b'blob '+str(len(source)).encode()+b'\0'+source).hexdigest()==BLOB, 'source blob mismatch'
    # Reviewed original source imports only fractions and re; no file/network operations.
    namespace={'__name__':'pinned_original_rank','__file__':str(ROOT.parent/'rank.py')}
    exec(compile(source,str(ROOT.parent/'rank.py'),'exec'),namespace)
    results=[]
    for s in f['scenarios']:
        gold={g['cardId']:g for g in s['gold_labels']}
        assert len(gold)==len(s['cards'])==len({c['cardId'] for c in s['cards']})
        assert set(gold)=={c['cardId'] for c in s['cards']}
        before=canonical(s)
        ranked=namespace['rank_cases'](s['query_tags'],s['cards'],reviewed_vocabulary=f['reviewed_vocabulary'])
        assert canonical(s)==before, 'input mutation'
        returned={r['cardId'] for r in ranked}
        assert len(returned)==len(ranked)<=5 and returned<=set(gold)
        for card in s['cards']:
            eligible=card['status']=='Published' and card['content']['kind']=='Case'
            assert eligible == (gold[card['cardId']]['label']!='excluded')
        def group(label, selected):
            return [g for k,g in gold.items() if g['label']==label and (k in returned)==selected]
        hits=group('relevant',True); misses=group('relevant',False)
        results.append(dict(query=s['scenario_id'],query_text=s['query_text'],query_tags=s['query_tags'],
            pool_size=len(s['cards']),ranked=[dict(r,**{k:gold[r['cardId']][k] for k in ('role','label','reason')}) for r in ranked],
            hits=hits,misses=misses,false_positive=group('not_relevant',True),
            insufficient_returned=group('insufficient_evidence',True),
            insufficient_not_returned=group('insufficient_evidence',False),
            excluded_filtered=group('excluded',False),eligibility_failures=group('excluded',True),
            confirmed_negative_not_returned=group('not_relevant',False),
            precision_at_5=ratio(len(hits),5),returned_correctness=ratio(len(hits),len(ranked)),
            recall=ratio(len(hits),len(hits)+len(misses))))
    total=lambda name:sum(len(r[name]) for r in results)
    return dict(source_commit='c1b988306a06e1d75f5b42c79fa1b50bd06ed596',source_blob=BLOB,
        source_sha256=hashlib.sha256(source).hexdigest(),fixture_sha256=FIXTURE_SHA,label_sha256=LABEL_SHA,
        scope='Six independent per-query pools, 27 synthetic cards; not global 27-card retrieval. query_text is not an input to rank_cases.',
        labels='Frozen author labels; root reviewed content legality, not expert-adjudicated relevance truth.',
        python=sys.version.split()[0],queries=results,
        aggregate=dict(hits=total('hits'),misses=total('misses'),returned=total('ranked'),
            false_positive=total('false_positive'),insufficient_returned=total('insufficient_returned'),
            excluded_filtered=total('excluded_filtered'),eligibility_failures=total('eligibility_failures'),
            precision_at_5=ratio(total('hits'),5*len(results)),returned_correctness=ratio(total('hits'),total('ranked')),
            micro_recall=ratio(total('hits'),total('hits')+total('misses'))))
if __name__=='__main__':
    print(json.dumps(evaluate(),ensure_ascii=False,indent=2))
