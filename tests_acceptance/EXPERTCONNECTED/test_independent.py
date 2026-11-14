import hashlib
import json
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess
import pytest
from research.expert_workbench import export as ex
from research.expert_meeting.machine import canonical

SOURCE=Path('/tmp/mcis-connected-mock-receipt.json')

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    import socket
    import research.expert_group.engine as engine
    def deny(*a,**k):pytest.fail('network or model forbidden')
    monkeypatch.setattr(socket.socket,'connect',deny);monkeypatch.setattr(engine,'_remote',deny);monkeypatch.setattr(engine,'run_group',deny)


def test_actual_receipt_verified_export_preserves_original_and_digest(tmp_path):
    raw=SOURCE.read_bytes();source=tmp_path/'receipt.json';source.write_bytes(raw);out=tmp_path/'view.html'
    sha=ex.export(source,out)
    assert source.read_bytes()==raw and sha==hashlib.sha256(raw).hexdigest()
    assert out.stat().st_mode&0o777==0o600
    html=out.read_text();assert html.startswith('<!doctype html>') and "connect-src 'none'" in html
    assert sha in html
    with pytest.raises(ex.ExportError):ex.export(source,out)
    assert out.read_text()==html and source.read_bytes()==raw


def test_output_same_as_input_cannot_overwrite(tmp_path):
    target=tmp_path/'input.json';raw=SOURCE.read_bytes();target.write_bytes(raw)
    with pytest.raises(ex.ExportError):ex.export(target,target)
    assert target.read_bytes()==raw


@pytest.mark.parametrize('kind',['symlink_input','symlink_parent','fifo','output_symlink'])
def test_untrusted_filesystem_endpoints_fail_closed(tmp_path,kind):
    real=tmp_path/'real';real.mkdir();source=real/'r';source.write_bytes(SOURCE.read_bytes());output=tmp_path/'out'
    if kind=='symlink_input':link=tmp_path/'link';link.symlink_to(source);source=link
    elif kind=='symlink_parent':link=tmp_path/'link';link.symlink_to(real,target_is_directory=True);source=link/'r'
    elif kind=='fifo':source=tmp_path/'fifo';os.mkfifo(source)
    else:output.symlink_to(source)
    original=(real/'r').read_bytes();before=len(os.listdir('/proc/self/fd'))
    with pytest.raises(ex.ExportError):ex.export(source,output)
    assert (real/'r').read_bytes()==original and len(os.listdir('/proc/self/fd'))==before


def test_two_publishers_cannot_replace_each_other(tmp_path):
    out=tmp_path/'out.html'
    def publish(content):
        try:ex.write_exclusive(out,content);return content
        except ex.ExportError:return None
    with ThreadPoolExecutor(max_workers=2) as pool:values=list(pool.map(publish,[b'first',b'second']))
    winners=[v for v in values if v is not None];assert len(winners)==1 and out.read_bytes()==winners[0]
    assert not list(tmp_path.glob('.mcis-view-*.tmp'))


def test_mid_write_failure_does_not_publish_or_leave_temporary(monkeypatch,tmp_path):
    original=os.write;calls=[]
    def broken(fd,data):
        calls.append(1)
        if len(calls)>1:raise OSError('SYNTHETIC')
        return original(fd,data[:3])
    monkeypatch.setattr(os,'write',broken)
    with pytest.raises(ex.ExportError):ex.write_exclusive(tmp_path/'out',b'long payload')
    assert list(tmp_path.iterdir())==[]


def test_tampered_composite_never_reaches_builder(monkeypatch,tmp_path):
    receipt=json.loads(SOURCE.read_bytes());receipt['realDeepSeekExecuted']=True
    path=tmp_path/'r';path.write_bytes(canonical(receipt))
    monkeypatch.setattr(ex,'render',lambda *a:pytest.fail('build before valid receipt'))
    with pytest.raises(ValueError):ex.export(path,tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_independent_dom_with_actual_verified_projection():
    view=ex.projection(SOURCE.read_bytes())
    assert view['hold'] and not view['realDeepSeekExecuted'] and len(view['rounds'])==2
    result=subprocess.run(['node','tests_acceptance/EXPERTCONNECTED/dom.mjs'],input=canonical(view),capture_output=True,check=True)
    assert b'8 independent DOM cases passed; network=0' in result.stdout


def test_projection_parser_rejects_inconsistent_counts_and_phases():
    view=ex.projection(SOURCE.read_bytes())
    result=subprocess.run(['node','tests_acceptance/EXPERTCONNECTED/parser-boundaries.mjs'],input=canonical(view),capture_output=True)
    assert result.returncode==0,result.stdout.decode()+result.stderr.decode()
    assert b'5/5 parser boundary cases passed' in result.stdout


def test_fixed_sources_and_model_inputs_unchanged():
    assert hashlib.sha256(Path('research/expert_workbench/model.ts').read_bytes()).hexdigest()=='8423ce5ecef3372b6d7d98d9a091513730f8a8bedc1d87d8ade5a79562944f57'
    for name in ['public-packet.json','engine.py','pi-runner.mjs']:
        path='research/expert_group/'+name
        assert Path(path).read_bytes()==subprocess.check_output(['git','show','6f8f429:'+path])
