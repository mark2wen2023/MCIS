"""Diagnostic unit doubles only; these tests do not validate the C# core."""
import importlib.util
from pathlib import Path
import subprocess
from types import SimpleNamespace
import pytest

spec = importlib.util.spec_from_file_location('hfacs_environment', Path(__file__).with_name('check_environment.py'))
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    (tmp_path / 'source').write_text('synthetic')
    monkeypatch.setattr(checker, 'recipe', lambda: SimpleNamespace(ROOT=tmp_path, HERE=tmp_path, INPUTS=['source'], SDK='8.0.428'))
    monkeypatch.setenv('MCIS_DOTNET', '/synthetic/sdk')
    return tmp_path


@pytest.mark.parametrize('out,code,status', [
    (b'8.0.428\n', 0, 'PREREQUISITES_READY'),
    (b'8.0.429', 0, 'SDK_VERSION_MISMATCH'),
    (b'private output', 1, 'SDK_QUERY_FAILED'),
    (b'\xff', 0, 'SDK_VERSION_MISMATCH'),
])
def test_version(setup, monkeypatch, out, code, status):
    calls = []
    def run(args, **kw):
        calls.append((args, kw))
        return subprocess.CompletedProcess(args, code, out, b'private stderr')
    monkeypatch.setattr(checker.subprocess, 'run', run)
    result = checker.check()
    assert result['status'] == status
    assert result['coreValidated'] is False
    assert 'private' not in str(result) and '/synthetic' not in str(result)
    assert calls == [(['/synthetic/sdk', '--version'], dict(capture_output=True, timeout=5, check=False))]
    assert sorted(p.name for p in setup.iterdir()) == ['source']


@pytest.mark.parametrize('error,status', [
    (FileNotFoundError(), 'SDK_MISSING'), (PermissionError(), 'SDK_NOT_EXECUTABLE'),
    (subprocess.TimeoutExpired('private', 5), 'SDK_QUERY_TIMEOUT'),
    (OSError('private'), 'SDK_QUERY_FAILED'), (ValueError('private'), 'SDK_QUERY_FAILED'),
])
def test_errors(setup, monkeypatch, error, status):
    def run(*args, **kw):
        raise error
    monkeypatch.setattr(checker.subprocess, 'run', run)
    assert checker.check()['status'] == status


def test_missing_source_never_executes(setup, monkeypatch):
    (setup / 'source').unlink()
    monkeypatch.setattr(checker.subprocess, 'run', lambda *a, **k: pytest.fail('must not execute'))
    assert checker.check()['status'] == 'SOURCE_MISSING'


def test_default_and_presence_not_validation(setup, monkeypatch):
    monkeypatch.delenv('MCIS_DOTNET')
    monkeypatch.setattr(checker.Path, 'home', lambda: setup)
    (setup / 'out').mkdir()
    for name in ('mcis-hfacs.dll', 'build-manifest.json'):
        (setup / 'out' / name).write_text('untrusted')
    def run(args, **kw):
        assert args == [str(setup / '.dotnet/dotnet'), '--version']
        return subprocess.CompletedProcess(args, 0, b'8.0.428', b'')
    monkeypatch.setattr(checker.subprocess, 'run', run)
    result = checker.check()
    assert result['dllPresent'] and result['manifestPresent']
    assert result['coreValidated'] is False and result['selection'] == 'HOME_DEFAULT'
