"""Independent offline acceptance. Real Pi fixture loops, never real provider calls."""
import asyncio
import copy
import hashlib
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import time
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT/'research/expert_group'
sys.path.insert(0, str(SRC))
import engine as e
import cli
import receipt
import render as renderer


@pytest.fixture(autouse=True)
def no_ip_network(monkeypatch):
    original = socket.socket.connect
    def blocked(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            raise AssertionError('independent acceptance prohibits IP connections')
        return original(sock, address)
    monkeypatch.setattr(socket.socket, 'connect', blocked)


@pytest.fixture(scope='module')
def exported(tmp_path_factory):
    path = tmp_path_factory.mktemp('group-root')/'new-export'
    with patch.object(e, '_remote', side_effect=AssertionError('fixture tried provider')), patch.object(cli, 'read_secret', side_effect=AssertionError('fixture tried credential')):
        assert cli.main(['--fixture', '--output-dir', str(path)]) == 0
    return path


def test_frozen_bytes_and_main_ancestry():
    import subprocess
    for line in (ROOT/'logs/expert-group-r1-impl-hashes-frozen.txt').read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest
    main='3aba2bf03e393909c611489ae573a887087637ac'
    assert subprocess.check_output(['git','merge-base',main,'HEAD'],cwd=ROOT,text=True).strip()==main
    assert subprocess.run(['git','merge-base','--is-ancestor','254167e3e957784fd9d2d136a275731f33314d9b','HEAD'],cwd=ROOT).returncode==1


def test_actual_pi_fixture_artifacts_distinguish_completion_and_no_provider(exported):
    result=json.loads((exported/'result.json').read_text())
    assert result['realPi'] is True and result['realModel'] is False
    assert result['providerRequests']==0 and result['transportMocked'] is True
    assert result['factActivated'] is False and result['consensusComputed'] is False
    assert result['status']=='completed_unverified'
    assert result['artifactPolicy']=='incomplete_without_valid_completion_manifest'
    assert [r['roleId'] for r in result['roles']]==list(e.ROLES)
    assert len({r['runId'] for r in result['roles']})==2
    assert all(r['modelCalls']==3 and r['toolCalls']==2 and len(r['reviews'])==3 for r in result['roles'])
    checked=receipt.verify_export(exported)
    assert checked['exportStatus']=='verified_local_consistency' and checked['authenticityVerified'] is False
    assert all((exported/name).stat().st_mode&0o777==0o600 for name in ['result.json','comparison.html','receipt.jsonl','completion.json'])
    assert exported.stat().st_mode&0o777==0o700
    rows=[json.loads(line)['event'] for line in (exported/'receipt.jsonl').read_text().splitlines()]
    assert len([r for r in rows if r['phase']=='model_attempt'])==6
    assert not any(r['phase']=='provider_request' for r in rows)
    assert all('apiKey' not in row and 'sourceText' not in row for row in rows)


def test_terminal_receipt_failure_downgrades_group(monkeypatch):
    def emit(event):
        if event['phase']=='group_completed': raise OSError('synthetic fsync failure')
    result=e.run_group(e.load_packet(),fixture=True,emit=emit)
    assert result['status']=='not_accepted' and result['outcome']=='failed'
    assert result['errorCode']=='receipt_write_failed'


def test_failed_pre_provider_receipt_never_attempts_provider(monkeypatch):
    calls=[]
    monkeypatch.setattr(e,'_remote',lambda *a: calls.append(True))
    def emit(event):
        if event['phase']=='provider_request':raise OSError('synthetic receipt denial')
    result=e.run_group(e.load_packet(),fixture=False,key='test-only-unused',emit=emit)
    assert calls==[] and result['providerRequests']==0
    assert result['status']=='not_accepted' and result['roles'][1]['status']=='not_started'


def test_independent_histories_and_receipt_before_mock_provider(monkeypatch,tmp_path):
    log=receipt.Receipt(tmp_path/'receipt.jsonl')
    histories=[]; steps={}
    def mocked_provider(messages,key,timeout,check):
        assert json.loads((tmp_path/'receipt.jsonl').read_text().splitlines()[-1])['event']['phase']=='provider_request'
        histories.append(copy.deepcopy(messages))
        role=messages[0]['content'];step=steps.get(role,0)+1;steps[role]=step
        candidate=json.loads(messages[-1]['content'])['candidateId'] if step==3 else None
        value=e._fixture(step,e._packet(e.load_packet()),candidate)
        if step==2:
            args=json.loads(value['tool_calls'][0]['function']['arguments'])
            for review in args['reviews']:review['rationale']='UNIQUE_FIRST_ROLE' if len(steps)==1 else 'UNIQUE_SECOND_ROLE'
            value['tool_calls'][0]['function']['arguments']=json.dumps(args,ensure_ascii=False)
        return value
    monkeypatch.setattr(e,'_remote',mocked_provider)
    try:result=e.run_group(e.load_packet(),fixture=False,key='test-only-unused',emit=log.append)
    finally:log.close()
    assert result['status']=='completed_unverified' and len(histories)==6
    assert len(histories[0])==len(histories[3])==2
    assert 'UNIQUE_FIRST_ROLE' not in json.dumps(histories[3:])
    assert 'UNIQUE_SECOND_ROLE' not in json.dumps(histories[:3])
    # Mocked transport in this test is engineering evidence, not model acceptance.


def test_cancel_during_uncertain_provider_stops_sibling(monkeypatch):
    attempts=[]
    def pending(*args):
        attempts.append(1);raise e.GroupError('cancelled')
    monkeypatch.setattr(e,'_remote',pending)
    result=e.run_group(e.load_packet(),fixture=False,key='test-only-unused')
    assert attempts==[1] and result['status']=='not_accepted' and result['outcome']=='unknown'
    assert result['roles'][1]['status']=='not_started'


def test_aggregate_budget_does_not_reset_per_role(monkeypatch):
    monkeypatch.setitem(e.LIMITS,'groupModelCalls',4)
    result=e.run_group(e.load_packet(),fixture=True)
    assert result['status']=='not_accepted' and result['errorCode']=='model_budget'
    assert [r['modelCalls'] for r in result['roles']]==[3,1]


def test_header_wait_inside_absolute_deadline(monkeypatch):
    import httpx
    cleanup=[]
    class Response:
        async def __aenter__(self):
            await asyncio.sleep(5)
            raise AssertionError('header wait exceeded deadline')
        async def __aexit__(self,*args):cleanup.append('response')
    class Client:
        def __init__(self,**kwargs):
            assert kwargs['trust_env'] is False and kwargs['follow_redirects'] is False
        async def __aenter__(self):return self
        async def __aexit__(self,*args):cleanup.append('client')
        def stream(self,method,url,**kwargs):
            assert method=='POST' and url==e.ENDPOINT
            return Response()
    monkeypatch.setattr(httpx,'AsyncClient',Client)
    started=time.monotonic()
    with pytest.raises(e.GroupError,match='provider_transport_unknown'):e._remote([], 'test-only', .05)
    assert time.monotonic()-started<.5 and 'client' in cleanup


@pytest.mark.parametrize('damage',['packet_byte','source_text','source_locator'])
def test_changed_packet_rejected_before_any_process(monkeypatch,damage):
    raw=e.load_packet()
    if damage=='packet_byte':raw+=b' '
    else:
        value=json.loads(raw)
        if damage=='source_text':value['items'][0]['sourceText']='changed'
        else:value['items'][0]['sourceLocator']['pdfPage']=1
        raw=json.dumps(value).encode()
    monkeypatch.setattr(e.subprocess,'Popen',lambda *a,**kw:pytest.fail('started process for changed packet'))
    with pytest.raises(e.GroupError,match='packet_pin_mismatch'):e.run_group(raw,fixture=True)


@pytest.mark.parametrize('name',['result.json','comparison.html','receipt.jsonl','completion.json'])
def test_changed_artifact_rejected(exported,tmp_path,name):
    path=tmp_path/'copy';shutil.copytree(exported,path)
    with (path/name).open('ab') as stream:stream.write(b'X')
    with pytest.raises((ValueError,KeyError)):receipt.verify_export(path)


def test_symlink_artifact_rejected(exported,tmp_path):
    path=tmp_path/'copy';shutil.copytree(exported,path)
    original=path/'result.json';outside=tmp_path/'outside.json';original.rename(outside);original.symlink_to(outside)
    with pytest.raises(OSError):receipt.verify_export(path)


@pytest.mark.parametrize('phase',['terminal_receipt','completion_marker'])
def test_failed_final_export_has_no_verifiable_success(exported,tmp_path,monkeypatch,phase):
    result=json.loads((exported/'result.json').read_text())
    monkeypatch.setattr(e,'run_group',lambda *a,**kw:copy.deepcopy(result))
    if phase=='terminal_receipt':
        original=receipt.Receipt.append
        def append(self,event):
            if event['phase']=='artifacts_written':raise OSError('synthetic receipt fsync failure')
            return original(self,event)
        monkeypatch.setattr(receipt.Receipt,'append',append)
    else:
        original=cli.write_new
        def write(name,*args,**kw):
            if name=='completion.json':raise OSError('synthetic marker failure')
            return original(name,*args,**kw)
        monkeypatch.setattr(cli,'write_new',write)
    path=tmp_path/'incomplete'
    assert cli.main(['--fixture','--output-dir',str(path)])==2
    assert not (path/'completion.json').exists()
    assert json.loads((path/'result.json').read_text())['artifactPolicy']=='incomplete_without_valid_completion_manifest'
    with pytest.raises((OSError,ValueError)):receipt.verify_export(path)


def test_cli_stale_disclosure_does_not_read_secret_or_write(monkeypatch,tmp_path):
    monkeypatch.setattr(cli,'read_secret',lambda:pytest.fail('stale disclosure read a key'))
    monkeypatch.setattr(e,'run_group',lambda *a,**kw:pytest.fail('stale disclosure started a run'))
    path=tmp_path/'never'
    assert cli.main(['--approved-remote','--approved-disclosure','0'*64,'--output-dir',str(path)])==2
    assert not path.exists()


def test_inert_text_and_no_factual_consensus(exported):
    packet=json.loads(e.load_packet());result=json.loads((exported/'result.json').read_text())
    result['roles'][0]['reviews'][0]['rationale']='</td><script>attack()</script><img src=https://invalid>'
    result['roles'][1]['reviews'][0]['label']='supported'
    text=renderer.render(packet,result).decode()
    class Tags(HTMLParser):
        def __init__(self):super().__init__();self.tags=[]
        def handle_starttag(self,tag,attrs):self.tags.append(tag)
    parser=Tags();parser.feed(text)
    assert not set(parser.tags)&{'script','a','img','iframe','form','link'}
    assert '&lt;script&gt;' in text and '建议标签不同' in text
    assert '标签相同；不是共识或事实确认' in text and '脚本模拟提供方' in text


def fd_count():
    # Linux execution environment; enumerate and close the proc directory iterator.
    return len(list(Path('/proc/self/fd').iterdir()))


@pytest.mark.parametrize('leaf', ['completion.json', 'result.json', 'comparison.html', 'receipt.jsonl'])
@pytest.mark.parametrize('kind', ['directory', 'fifo'])
def test_repeated_nonregular_artifact_rejection_releases_descriptors(exported,tmp_path,leaf,kind):
    path=tmp_path/'nonregular';shutil.copytree(exported,path)
    (path/leaf).unlink()
    if kind=='directory':(path/leaf).mkdir()
    else:os.mkfifo(path/leaf,0o600)
    before=fd_count()
    for _ in range(8):
        with pytest.raises(ValueError,match='regular file required'):receipt.verify_export(path)
        assert fd_count()==before


@pytest.mark.parametrize('leaf', ['completion.json', 'result.json', 'comparison.html', 'receipt.jsonl'])
def test_fdopen_failure_on_each_read_stage_closes_raw_descriptor(exported,monkeypatch,leaf):
    original=receipt.os.fdopen
    affected=[]
    def fail_target(fd,*args,**kwargs):
        if Path(os.readlink('/proc/self/fd/'+str(fd))).name==leaf:
            affected.append(fd)
            raise OSError('synthetic wrapping failure')
        return original(fd,*args,**kwargs)
    before=fd_count()
    monkeypatch.setattr(receipt.os,'fdopen',fail_target)
    for _ in range(5):
        with pytest.raises(OSError,match='synthetic wrapping failure'):receipt.verify_export(exported)
        assert fd_count()==before
    assert len(affected)==5


def test_write_fdopen_failure_closes_raw_descriptor(tmp_path,monkeypatch):
    def fail(fd,*args,**kwargs):raise OSError('synthetic write wrapping failure')
    before=fd_count()
    monkeypatch.setattr(receipt.os,'fdopen',fail)
    for number in range(8):
        target=tmp_path/f'failed-{number}.json'
        with pytest.raises(OSError,match='synthetic write wrapping failure'):receipt.write_new(target,b'synthetic')
        assert fd_count()==before
        assert target.read_bytes()==b''  # A partial artifact remains, never a complete export.


def test_fstat_failure_closes_unwrapped_read_descriptor(exported,monkeypatch):
    original=receipt.os.fstat
    def fail(fd):
        if Path(os.readlink('/proc/self/fd/'+str(fd))).name=='completion.json':
            raise OSError('synthetic stat failure')
        return original(fd)
    before=fd_count()
    monkeypatch.setattr(receipt.os,'fstat',fail)
    for _ in range(5):
        with pytest.raises(OSError,match='synthetic stat failure'):receipt.verify_export(exported)
        assert fd_count()==before


@pytest.mark.parametrize('mode',['read','write'])
def test_stream_failure_after_successful_fd_transfer_still_closes(exported,tmp_path,monkeypatch,mode):
    original=receipt.os.fdopen
    class BrokenStream:
        def __init__(self,stream):self.stream=stream
        def __enter__(self):return self
        def __exit__(self,*args):self.stream.close()
        def read(self,*args):raise OSError('synthetic stream failure')
        def write(self,*args):raise OSError('synthetic stream failure')
    def wrap(fd,*args,**kwargs):return BrokenStream(original(fd,*args,**kwargs))
    before=fd_count()
    monkeypatch.setattr(receipt.os,'fdopen',wrap)
    for number in range(5):
        with pytest.raises(OSError,match='synthetic stream failure'):
            if mode=='read':receipt.verify_export(exported)
            else:receipt.write_new(tmp_path/f'partial-{number}',b'synthetic')
        assert fd_count()==before
