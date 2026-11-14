"""Offline exporter tests: no Pi processes, provider calls or network."""
import hashlib
import os
from pathlib import Path
from copy import deepcopy
import pytest
from research.expert_workbench import export as ex
from research.expert_meeting.machine import Meeting,canonical
from research.expert_bridge.protocol import Bridge
from research.expert_executor.executor import Executor

@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    import socket
    def deny(*a,**kw):raise AssertionError('network forbidden')
    monkeypatch.setattr(socket.socket,'connect',deny)


def empty_receipt(start=False):
    m=Meeting(provider_mode='remote');b=Bridge(m);e=Executor(b,provider_mode='remote_mock')
    if start:m.act({'type':'start_round'})
    return e.receipt()


def test_valid_empty_receipt_projection():
    raw=canonical(empty_receipt());p=ex.projection(raw)
    assert p['schema']=='mcis.expert-meeting-display.v1'
    assert p['receiptSha256']==hashlib.sha256(raw).hexdigest()
    assert p['rounds']==[] and p['transportMode']=='remote_mock' and p['hold']
    assert not p['realDeepSeekExecuted'] and not p['authenticityVerified']
    assert 'runId' not in p and 'manifestDigest' not in p


def test_open_round_has_fixed_two_not_started_roles():
    p=ex.projection(canonical(empty_receipt(True)))
    assert [r['roleId'] for r in p['rounds'][0]['roles']]==list(ex.ROLES)
    assert all(r['status']=='not_started' and r['ticketId'] is None and r['reviews']==[] for r in p['rounds'][0]['roles'])


def test_invalid_receipt_not_rendered(monkeypatch,tmp_path):
    source=tmp_path/'receipt';source.write_bytes(b'{}')
    def forbidden(*a):raise AssertionError('must validate before build')
    monkeypatch.setattr(ex,'render',forbidden)
    with pytest.raises(ValueError):ex.export(source,tmp_path/'out.html')
    assert not (tmp_path/'out.html').exists()


@pytest.mark.parametrize('kind',['symlink','directory','fifo','large','parent_symlink'])
def test_unsafe_receipt_rejected_without_fd_leak(tmp_path,kind):
    target=tmp_path/'target';target.write_bytes(b'{}');path=tmp_path/'input'
    if kind=='symlink':path.symlink_to(target)
    if kind=='directory':path.mkdir()
    if kind=='fifo':os.mkfifo(path)
    if kind=='large':
        with path.open('wb') as f:f.truncate(ex.MAX_RECEIPT+1)
    if kind=='parent_symlink':
        real=tmp_path/'real';real.mkdir();(real/'file').write_bytes(b'{}');path.symlink_to(real,target_is_directory=True);path=path/'file'
    before=len(os.listdir('/proc/self/fd'))
    for _ in range(3):
        with pytest.raises(ex.ExportError):ex.read_receipt(path)
    assert len(os.listdir('/proc/self/fd'))==before


def test_regular_input_bytes_preserved(tmp_path):
    path=tmp_path/'r';path.write_bytes(b'raw\nbytes');assert ex.read_receipt(path)==b'raw\nbytes'

@pytest.mark.parametrize('kind',['file','symlink','directory'])
def test_existing_output_never_overwritten(tmp_path,kind):
    target=tmp_path/'target';target.write_bytes(b'original');out=tmp_path/'out'
    if kind=='file':out.write_bytes(b'original')
    if kind=='symlink':out.symlink_to(target)
    if kind=='directory':out.mkdir()
    with pytest.raises(ex.ExportError):ex.write_exclusive(out,b'new')
    assert target.read_bytes()==b'original'
    if kind=='file':assert out.read_bytes()==b'original'
    assert not list(tmp_path.glob('.mcis-view-*'))


def test_output_permissions_repeat_and_short_writes(tmp_path,monkeypatch):
    original=ex.os.write
    monkeypatch.setattr(ex.os,'write',lambda fd,data:original(fd,data[:2]))
    out=tmp_path/'out';ex.write_exclusive(out,b'complete bytes')
    assert out.read_bytes()==b'complete bytes' and out.stat().st_mode & 0o777==0o600
    with pytest.raises(ex.ExportError):ex.write_exclusive(out,b'overwrite')
    assert out.read_bytes()==b'complete bytes'

@pytest.mark.parametrize('stage',['write','file_fsync','link','directory_fsync'])
def test_output_faults_never_report_success(tmp_path,monkeypatch,stage):
    def fail(*a,**kw):raise OSError('synthetic failure')
    if stage=='write':monkeypatch.setattr(ex.os,'write',fail)
    if stage=='link':monkeypatch.setattr(ex.os,'link',fail)
    if stage in ('file_fsync','directory_fsync'):
        original=ex.os.fsync;calls=[0]
        def sync(fd):
            calls[0]+=1
            if calls[0]==(1 if stage=='file_fsync' else 2):fail()
            return original(fd)
        monkeypatch.setattr(ex.os,'fsync',sync)
    with pytest.raises(ex.ExportError):ex.write_exclusive(tmp_path/'out',b'whole output')
    if (tmp_path/'out').exists():assert (tmp_path/'out').read_bytes()==b'whole output'
    assert not list(tmp_path.glob('.mcis-view-*'))


def test_build_failure_does_not_create_output(tmp_path,monkeypatch):
    source=tmp_path/'r';source.write_bytes(canonical(empty_receipt()))
    def fail(*a,**kw):raise ex.subprocess.CalledProcessError(1,'node')
    monkeypatch.setattr(ex.subprocess,'run',fail)
    assert ex.main(['--receipt',str(source),'--output',str(tmp_path/'out')])==2
    assert not (tmp_path/'out').exists()


def test_full_export_with_stub_build_and_readonly_source(tmp_path,monkeypatch):
    raw=canonical(empty_receipt(True));source=tmp_path/'r';source.write_bytes(raw)
    monkeypatch.setattr(ex,'render',lambda view:b'<!doctype html><title>synthetic test</title>')
    sha=ex.export(source,tmp_path/'view.html')
    assert sha==hashlib.sha256(raw).hexdigest() and source.read_bytes()==raw
    assert ex.main(['--receipt',str(source),'--output',str(tmp_path/'view.html')])==2

@pytest.fixture(scope='module')
def mock_completed_receipt():
    """Actual Pi plus explicitly mocked HTTP; not real model capability evidence."""
    m=Meeting(provider_mode='remote');b=Bridge(m);e=Executor(b,provider_mode='remote_mock')
    for _ in range(2):
        m.act({'type':'start_round'})
        for role in ex.ROLES:e.run_turn(role)
    return canonical(e.receipt())


def test_completed_projection_keeps_two_round_reviews(mock_completed_receipt):
    p=ex.projection(mock_completed_receipt)
    assert len(p['rounds'])==2 and p['meetingPhase']=='completed_unverified'
    assert p['budget']=={'totalModels':12,'totalTools':8,'received':12,'unknown':0,'notDispatched':0,'limits':{'models':16,'tools':32}}
    assert all(r['status']=='completed_unverified' and len(r['reviews'])==3 for rd in p['rounds'] for r in rd['roles'])
    assert p['hold'] and p['transportMode']=='remote_mock' and not p['realDeepSeekExecuted']


def test_actual_html_build_exclusive_output(tmp_path,mock_completed_receipt):
    source=tmp_path/'receipt.json';source.write_bytes(mock_completed_receipt)
    out=tmp_path/'view.html';ex.export(source,out)
    html=out.read_text()
    assert html.startswith('<!doctype html>') and 'Content-Security-Policy' in html
    assert 'connect-src' in html and 'remote_mock' in html
    assert source.read_bytes()==mock_completed_receipt
    with pytest.raises(ex.ExportError):ex.export(source,out)


def test_partial_unknown_projection_no_invented_review(monkeypatch):
    from research.expert_remote import isolated,transport
    async def fail(*a,**kw):raise transport.TransportError('mock_unknown',True)
    monkeypatch.setattr(isolated,'request',fail)
    m=Meeting(provider_mode='remote');b=Bridge(m);e=Executor(b,provider_mode='remote_mock');m.act({'type':'start_round'})
    with pytest.raises(Exception):e.run_turn(ex.ROLES[0])
    p=ex.projection(canonical(e.receipt()))
    assert p['rounds'][0]['roles'][0]['status']=='unknown'
    assert p['rounds'][0]['roles'][1]['status']=='not_started'
    assert all(r['reviews']==[] for r in p['rounds'][0]['roles'])
    assert p['budget']['unknown']==1 and p['budget']['received']==0
