import copy
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest
sys.path.insert(0, str(Path(__file__).parent))
from receipt import Receipt, canonical, write_new
from render import render
import cli


def inputs():
    packet = json.loads(Path(__file__).with_name('public-packet.json').read_text())
    roles = []
    for role, label in [('source_attribution', 'supported'), ('uncertainty_boundary', 'insufficient')]:
        roles.append({'roleId': role, 'runId': 'child', 'status': 'completed_unverified', 'reviews': [
            {'itemId': i['itemId'], 'label': label, 'quote': i['citation']['quote'],
             'rationale': '<script>untrusted</script>', 'uncertainty': '未认证来源'} for i in packet['items']]})
    result = {'status': 'completed_unverified', 'runId': 'group', 'packetSha256': hashlib.sha256(canonical(packet)).hexdigest(),
              'transportMocked': True, 'factActivated': False, 'consensusComputed': False, 'roles': roles}
    return packet, result


def test_inert_html_disagreement_and_incomplete():
    packet, result = inputs()
    text = render(packet, result).decode()
    assert '<script>' not in text and '&lt;script&gt;' in text
    assert '<a ' not in text and "connect-src 'none'" in text
    assert '建议标签不同' in text and '脚本模拟提供方' in text
    assert '不是真人专家' in text and '未认证来源' in text
    assert '171.053' in text and 'pdfSha256' in text
    result['roles'][1]['status'] = 'not_started'
    text = render(packet, result).decode()
    assert '意见不完整' in text and '建议标签不同' not in text


def test_equal_labels_never_consensus():
    packet, result = inputs()
    result['roles'][1]['reviews'] = copy.deepcopy(result['roles'][0]['reviews'])
    assert '标签相同；不是共识或事实确认' in render(packet, result).decode()
    result['factActivated'] = True
    with pytest.raises(ValueError): render(packet, result)


def test_receipt_chain_permissions_and_no_overwrite(tmp_path):
    path = tmp_path/'receipt.jsonl'
    receipt = Receipt(path)
    receipt.append({'phase': 'created', 'transportMocked': True})
    receipt.append({'phase': 'model_attempt', 'modelCalls': 1})
    with pytest.raises(ValueError): receipt.append({'phase': 'x', 'apiKey': 'must-not-log'})
    receipt.close()
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    previous = '0'*64
    for seq, row in enumerate(rows, 1):
        digest = row.pop('sha256')
        assert row['seq'] == seq and row['previousSha256'] == previous
        assert hashlib.sha256(canonical(row)).hexdigest() == digest
        previous = digest
    assert path.stat().st_mode & 0o777 == 0o600
    before = path.read_bytes()
    with pytest.raises(FileExistsError): Receipt(path)
    assert path.read_bytes() == before
    link = tmp_path/'link'; link.symlink_to(path)
    with pytest.raises(FileExistsError): write_new(link, b'bad')
    assert path.read_bytes() == before


def test_cli_fixture_never_reads_key_and_duplicate_refuses(tmp_path, monkeypatch, capsys):
    packet, result = inputs()
    calls = []
    def run(raw, **kw):
        assert kw['fixture'] is True and kw['key'] is None
        calls.append(True); kw['emit']({'phase': 'completed_unverified'})
        return result
    monkeypatch.setitem(sys.modules, 'engine', SimpleNamespace(disclosure=lambda: {'scope': 'fixed'}, run_group=run))
    monkeypatch.setattr(cli, 'read_secret', lambda: (_ for _ in ()).throw(AssertionError('secret touched')))
    directory = tmp_path/'new'
    assert cli.main(['--fixture', '--output-dir', str(directory)]) == 0
    assert directory.stat().st_mode & 0o777 == 0o700
    before = (directory/'result.json').read_bytes()
    assert cli.main(['--fixture', '--output-dir', str(directory)]) == 2
    assert calls == [True] and (directory/'result.json').read_bytes() == before


def test_scope_rejects_before_secret_or_output(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, 'engine', SimpleNamespace(disclosure=lambda: {'scope': 'fixed'}))
    monkeypatch.setattr(cli, 'read_secret', lambda: (_ for _ in ()).throw(AssertionError('secret touched')))
    path = tmp_path/'out'
    assert cli.main(['--approved-remote', '--approved-disclosure', 'wrong', '--output-dir', str(path)]) == 2
    assert not path.exists()


def test_partial_run_not_reported_complete(tmp_path, monkeypatch, capsys):
    _, result = inputs(); result['status'] = 'not_accepted'; result['roles'][1]['status'] = 'not_started'
    monkeypatch.setitem(sys.modules, 'engine', SimpleNamespace(disclosure=lambda: {}, run_group=lambda *a, **k: result))
    path = tmp_path/'partial'
    assert cli.main(['--fixture', '--output-dir', str(path)]) == 2
    assert json.loads((path/'result.json').read_text())['status'] == 'not_accepted'
    assert '意见不完整' in (path/'comparison.html').read_text()


def test_completion_marker_required_and_tampering_rejected(tmp_path, monkeypatch):
    from receipt import verify_export
    _, result = inputs()
    monkeypatch.setitem(sys.modules, 'engine', SimpleNamespace(disclosure=lambda: {}, run_group=lambda *a, **k: result))
    path = tmp_path/'checked'
    assert cli.main(['--fixture','--output-dir',str(path)]) == 0
    assert verify_export(path)['authenticityVerified'] is False
    (path/'comparison.html').write_text('changed')
    with pytest.raises(ValueError): verify_export(path)
    (path/'completion.json').unlink()
    with pytest.raises(FileNotFoundError): verify_export(path)


def test_terminal_receipt_failure_has_no_completion_marker(tmp_path, monkeypatch):
    from receipt import verify_export
    _, result = inputs()
    monkeypatch.setitem(sys.modules, 'engine', SimpleNamespace(disclosure=lambda: {}, run_group=lambda *a, **k: result))
    original = Receipt.append
    def fail(self, event):
        if event['phase'] == 'artifacts_written': raise OSError('disk error')
        return original(self, event)
    monkeypatch.setattr(Receipt, 'append', fail)
    path = tmp_path/'failed'
    assert cli.main(['--fixture','--output-dir',str(path)]) == 2
    assert json.loads((path/'result.json').read_text())['artifactPolicy'] == 'incomplete_without_valid_completion_manifest'
    assert not (path/'completion.json').exists()
    with pytest.raises(FileNotFoundError): verify_export(path)


@pytest.mark.parametrize('leaf', ['completion.json', 'result.json', 'comparison.html', 'receipt.jsonl'])
def test_directory_leaf_rejected_without_descriptor_leak(tmp_path, monkeypatch, leaf):
    from receipt import verify_export
    _, result = inputs()
    monkeypatch.setitem(sys.modules, 'engine', SimpleNamespace(disclosure=lambda: {}, run_group=lambda *a, **k: result))
    path = tmp_path/'run'
    assert cli.main(['--fixture', '--output-dir', str(path)]) == 0
    (path/leaf).unlink(); (path/leaf).mkdir()
    before = len(os.listdir('/proc/self/fd'))
    for _ in range(4):
        with pytest.raises(ValueError, match='regular file required'):
            verify_export(path)
    assert len(os.listdir('/proc/self/fd')) == before


def test_fdopen_failure_closes_untransferred_read_and_write_fds(tmp_path, monkeypatch):
    import receipt
    _, result = inputs()
    monkeypatch.setitem(sys.modules, 'engine', SimpleNamespace(disclosure=lambda: {}, run_group=lambda *a, **k: result))
    path = tmp_path/'run'
    assert cli.main(['--fixture', '--output-dir', str(path)]) == 0
    def fail(*a, **k): raise OSError('wrapper failure')
    monkeypatch.setattr(receipt.os, 'fdopen', fail)
    before = len(os.listdir('/proc/self/fd'))
    for index in range(4):
        with pytest.raises(OSError, match='wrapper failure'): receipt.verify_export(path)
        with pytest.raises(OSError, match='wrapper failure'): receipt.write_new(tmp_path/f'new-{index}', b'')
    assert len(os.listdir('/proc/self/fd')) == before
