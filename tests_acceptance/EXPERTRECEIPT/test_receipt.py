"""Synthetic local files only; no model, provider or case evidence."""
import hashlib
import json
import os
import pytest
from research.expert_group import receipt as r


def bundle(path, status='failed'):
    result = dict(runId='synthetic', status=status, artifactPolicy='incomplete_without_valid_completion_manifest', factActivated=False, consensusComputed=False, transportMocked=True)
    raw = r.canonical(result)
    r.write_new(path/'result.json', raw)
    r.write_new(path/'comparison.html', b'<p>synthetic unverified</p>')
    receipt = r.Receipt(path/'receipt.jsonl')
    try:
        receipt.append(dict(phase='artifacts_written', groupRunId='synthetic', status=status, outputDigest=hashlib.sha256(raw).hexdigest()))
    finally:
        receipt.close()
    marker = dict(schemaVersion=1, exportStatus='complete', runId='synthetic', runStatus=status)
    for key, file in [('resultSha256','result.json'),('htmlSha256','comparison.html'),('receiptSha256','receipt.jsonl')]:
        marker[key] = hashlib.sha256((path/file).read_bytes()).hexdigest()
    r.write_new(path/'completion.json', r.canonical(marker))


@pytest.mark.parametrize('status', ['failed','partial','cancelled','unknown','completed_unverified'])
def test_consistency_never_promotes_status(tmp_path, status):
    bundle(tmp_path, status)
    assert r.verify_export(tmp_path) == dict(exportStatus='verified_local_consistency',runId='synthetic',runStatus=status,authenticityVerified=False,transportMocked=True,factActivated=False)


@pytest.mark.parametrize('file',['result.json','comparison.html','receipt.jsonl'])
def test_tamper(tmp_path,file):
    bundle(tmp_path)
    with (tmp_path/file).open('ab') as out: out.write(b' ')
    with pytest.raises(ValueError,match='artifact mismatch'): r.verify_export(tmp_path)


@pytest.mark.parametrize('raw',[b'{"x":1,"x":2}',b'{"x":NaN}',b'{}', b' '*4097])
def test_bad_manifest(tmp_path,raw):
    (tmp_path/'completion.json').write_bytes(raw)
    with pytest.raises(ValueError): r.verify_export(tmp_path)


@pytest.mark.parametrize('kind',['directory','symlink','fifo'])
def test_nonregular_leaf_closes_descriptors(tmp_path,kind):
    path=tmp_path/'completion.json'
    if kind=='directory': path.mkdir()
    elif kind=='symlink': path.symlink_to('missing')
    else: os.mkfifo(path)
    before=len(os.listdir('/proc/self/fd'))
    for _ in range(8):
        with pytest.raises((ValueError,OSError)): r.verify_export(tmp_path)
    assert len(os.listdir('/proc/self/fd'))==before


def test_fdopen_failure_closes_raw_fd(tmp_path,monkeypatch):
    bundle(tmp_path)
    def fail(*a,**k): raise OSError('synthetic wrapping failure')
    monkeypatch.setattr(r.os,'fdopen',fail)
    before=len(os.listdir('/proc/self/fd'))
    for i in range(4):
        with pytest.raises(OSError): r.verify_export(tmp_path)
        with pytest.raises(OSError): r.write_new(tmp_path/f'new-{i}',b'data')
    assert len(os.listdir('/proc/self/fd'))==before


def test_exclusive_write_and_receipt(tmp_path):
    path=tmp_path/'existing'
    path.write_bytes(b'original')
    with pytest.raises(FileExistsError): r.write_new(path,b'replacement')
    with pytest.raises(FileExistsError): r.Receipt(path)
    assert path.read_bytes()==b'original'


def test_short_writes(tmp_path,monkeypatch):
    original=os.write
    monkeypatch.setattr(r.os,'write',lambda fd,data: original(fd,data[:7]))
    bundle(tmp_path)
    assert r.verify_export(tmp_path)['runStatus']=='failed'


def test_fsync_failure_does_not_advance(tmp_path,monkeypatch):
    receipt=r.Receipt(tmp_path/'receipt')
    monkeypatch.setattr(r.os,'fsync',lambda fd: (_ for _ in ()).throw(OSError('synthetic sync failure')))
    try:
        with pytest.raises(OSError): receipt.append({'phase':'test'})
        assert receipt.sequence==0 and receipt.previous=='0'*64
    finally: receipt.close()
