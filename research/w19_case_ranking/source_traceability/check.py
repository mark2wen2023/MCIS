"""Traceability only; runs original ranker. No automatic semantic adjudication."""
import hashlib,json,runpy,sys
from pathlib import Path
from copy import deepcopy
ROOT=Path(__file__).resolve().parent
def sha(raw):return hashlib.sha256(raw).hexdigest()
def locate(card):
    b=card['sourceBinding'];c=card['content'];name=b['file']
    # Fixed synthetic filenames only, not a general file-reading interface.
    if name not in ('source-records.txt','absent-records.txt'):return 'FILE_OUT_OF_SCOPE'
    path=ROOT/name
    if not path.is_file():return 'SOURCE_NOT_FOUND'
    raw=path.read_bytes()
    if sha(raw)!=b['sha256']:return 'SOURCE_HASH_MISMATCH'
    lines=raw.decode('utf-8').splitlines();line=b['line']
    if type(line) is not int or not 1<=line<=len(lines):return 'LINE_NOT_FOUND'
    fields=lines[line-1].split('\t',2)
    if len(fields)!=3 or fields[0]!=b['recordId']:return 'RECORD_ID_MISMATCH'
    if c['source']['locator']!=name+'#L'+str(line):return 'LOCATOR_MISMATCH'
    if c['source']['excerpt']!=fields[2] or c['body']!=fields[2]:return 'TEXT_MISMATCH'
    return 'LOCATED'
def main():
    for line in (ROOT/'FROZEN.sha256').read_text().splitlines():
        digest,name=line.split('  ');assert sha((ROOT/name).read_bytes())==digest,name
    path=Path(sys.argv[1]);raw=path.read_bytes()
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()=='df014103e47dcb1bb4a1115c6d05e1d4d30385c5'
    f=json.loads((ROOT/'sample.json').read_text())
    # sourceBinding is experiment metadata, not a new product schema field.
    rank_cards=[{k:c[k] for k in ('cardId','status','content')} for c in f['cards']]
    original=runpy.run_path(str(path))['rank_cases']
    ranked=original(f['query_tags'],rank_cards,reviewed_vocabulary=f['reviewed_vocabulary'])
    cards={c['cardId']:c for c in f['cards']}
    result=[dict(r,traceability=locate(cards[r['cardId']]),support='NOT_ASSESSED',causation='NOT_ASSESSED',review='PENDING') for r in ranked]
    assert [r['cardId'] for r in result]==[r['cardId'] for r in ranked]
    # Frozen expected outcomes enter only after predictions, never rank/locate.
    expected=json.loads((ROOT/'CRITERIA.json').read_text())['expected_traceability']
    assert {r['cardId']:r['traceability'] for r in result}==expected
    variants=[
        ('SOURCE_HASH_MISMATCH',lambda c:c['sourceBinding'].update(sha256='0'*64)),
        ('LINE_NOT_FOUND',lambda c:c['sourceBinding'].update(line=99)),
        ('RECORD_ID_MISMATCH',lambda c:c['sourceBinding'].update(recordId='SYN-OTHER')),
        ('LOCATOR_MISMATCH',lambda c:c['content']['source'].update(locator='source-records.txt#L3')),
        ('TEXT_MISMATCH',lambda c:c['content']['source'].update(excerpt='已证明原因')),
        ('TEXT_MISMATCH',lambda c:c['content'].update(body='已证明原因'))]
    for code,change in variants:
        card=deepcopy(f['cards'][1]);change(card);assert locate(card)==code,code
    print(json.dumps({'scope':'pure synthetic traceability; no recall improvement or semantic truth claim',
        'rank_source_blob':'df014103e47dcb1bb4a1115c6d05e1d4d30385c5','ranked':result,
        'checks':{'frozen_sample_cases':3,'mutations_rejected':6,'recall_and_order_preserved':True},
        'interpretation':'Two quotations resolve. Other-vessel/unconfirmed and observation-without-cause both remain pending.'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
