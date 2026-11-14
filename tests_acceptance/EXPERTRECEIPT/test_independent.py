"""Independent synthetic local consistency tests, no provider execution."""
import hashlib,json,os
from pathlib import Path
import pytest
from research.expert_group import receipt as r

def sha(b):return hashlib.sha256(b).hexdigest()
def make(path,events=None,result_changes=None):
    result={'runId':'independent','status':'unknown','artifactPolicy':'incomplete_without_valid_completion_manifest','factActivated':False,'consensusComputed':False,'transportMocked':True}
    result.update(result_changes or {});raw=r.canonical(result)
    rows=[];previous='0'*64
    events=events if events is not None else [{'phase':'created'},{'phase':'artifacts_written','groupRunId':'independent','status':'unknown','outputDigest':sha(raw)}]
    for i,event in enumerate(events,1):
        row={'schemaVersion':1,'seq':i,'previousSha256':previous,'event':event};previous=sha(r.canonical(row));rows.append(r.canonical({**row,'sha256':previous})+b'\n')
    files={'result.json':raw,'comparison.html':b'<p>synthetic</p>','receipt.jsonl':b''.join(rows)}
    for name,data in files.items():(path/name).write_bytes(data)
    marker={'schemaVersion':1,'exportStatus':'complete','runId':result['runId'],'runStatus':result['status'],'resultSha256':sha(raw),'htmlSha256':sha(files['comparison.html']),'receiptSha256':sha(files['receipt.jsonl'])}
    (path/'completion.json').write_bytes(r.canonical(marker))

def rehash(path,name,key):
    p=path/'completion.json';m=json.loads(p.read_bytes());m[key]=sha((path/name).read_bytes());p.write_bytes(r.canonical(m))

@pytest.mark.parametrize('change',['newline','truncated','seq','previous','event_tamper','empty'])
def test_chain_invalid_even_after_outer_hash_rebound(tmp_path,change):
    make(tmp_path);p=tmp_path/'receipt.jsonl';rows=[json.loads(x) for x in p.read_bytes().splitlines()]
    if change=='newline':raw=p.read_bytes()[:-1]
    elif change=='truncated':raw=p.read_bytes()[:-8]
    elif change=='empty':raw=b''
    else:
        if change=='seq':rows[-1]['seq']=3
        elif change=='previous':rows[-1]['previousSha256']='f'*64
        else:rows[-1]['event']['phase']='spoofed'
        raw=b''.join(r.canonical(x)+b'\n' for x in rows)
    p.write_bytes(raw);rehash(tmp_path,'receipt.jsonl','receiptSha256')
    with pytest.raises(ValueError):r.verify_export(tmp_path)

@pytest.mark.parametrize('target,key',[('result.json','resultSha256'),('receipt.jsonl','receiptSha256')])
def test_duplicate_json_keys_rejected_beyond_manifest(tmp_path,target,key):
    make(tmp_path);p=tmp_path/target;raw=p.read_bytes()
    if target=='result.json':raw=raw[:-1]+b',"runId":"independent"}'
    else:raw=raw.replace(b'"seq":1',b'"seq":1,"seq":1')
    p.write_bytes(raw);rehash(tmp_path,target,key)
    with pytest.raises(ValueError,match='duplicate'):r.verify_export(tmp_path)

@pytest.mark.parametrize('event',[{'phase':'created'}, {'phase':'artifacts_written','groupRunId':'other','status':'unknown','outputDigest':'a'*64}])
def test_self_consistent_chain_wrong_terminal_rejected(tmp_path,event):
    make(tmp_path,events=[event])
    with pytest.raises(ValueError,match='receipt terminal'):r.verify_export(tmp_path)

def test_author_claim_does_not_authenticate_and_unknown_not_promoted(tmp_path):
    make(tmp_path,result_changes={'authenticityVerified':True,'author':'SYNTHETIC'})
    result=r.verify_export(tmp_path)
    assert result['authenticityVerified'] is False and result['runStatus']=='unknown'
    assert result['exportStatus']=='verified_local_consistency' and result['factActivated'] is False

@pytest.mark.parametrize('field',['factActivated','consensusComputed'])
def test_fact_and_consensus_claim_rejected(tmp_path,field):
    make(tmp_path,result_changes={field:True})
    with pytest.raises(ValueError,match='result mismatch'):r.verify_export(tmp_path)

def test_partial_write_error_does_not_advance_writer(tmp_path,monkeypatch):
    writer=r.Receipt(tmp_path/'partial');original=os.write;calls=[]
    def fail(fd,data):
        calls.append(1)
        if len(calls)>1:raise OSError('synthetic')
        return original(fd,data[:5])
    monkeypatch.setattr(r.os,'write',fail)
    try:
        with pytest.raises(OSError):writer.append({'phase':'created'})
        assert writer.sequence==0 and writer.previous=='0'*64 and writer.file_hash.hexdigest()==sha(b'')
        assert (tmp_path/'partial').stat().st_size==5
    finally:writer.close()

def test_zero_write_fails_without_loop(tmp_path,monkeypatch):
    writer=r.Receipt(tmp_path/'zero');monkeypatch.setattr(r.os,'write',lambda *a:0)
    try:
        with pytest.raises(OSError):writer.append({'phase':'created'})
        assert writer.sequence==0
    finally:writer.close()

def test_exact_published_source_and_stdlib_only():
    import ast
    path='research/expert_group/receipt.py';raw=Path(path).read_bytes()
    # Pinned during byte-for-byte extraction from source commit
    # 1d5262c9f8a491fd7b1d8037c4dff8988865770c (not a main ancestor).
    # Do not fetch unrelated history or derive the expected digest from this file.
    assert sha(raw)=='90bec2c56a046cd536b9afb167c6ca9181f0a340ec51365bdad9785c1123eeb5'
    tree=ast.parse(raw);names={n.name for node in ast.walk(tree) if isinstance(node,ast.Import) for n in node.names}
    assert names=={'hashlib','json','os','re','stat'}
