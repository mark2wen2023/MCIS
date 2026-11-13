"""Independent isolated terminal demo checks; real W2 opt-in, no product edits."""
import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import pytest
from mcis_service.identity import demo

CORE=os.getenv('MCIS_PREFLIGHT_REAL_CORE')

def execute(*args,stdin=None,env=None):
    return subprocess.run([sys.executable,'-m','mcis_service.identity.demo',*args],input=stdin,
        text=True,capture_output=True,timeout=30,env=env)

@pytest.mark.skipif(not CORE,reason='actual W2 required')
def test_real_subprocess_second_source():
    r=execute('--core-command',CORE,'--choice','2','--json')
    assert r.returncode==0,r.stdout+r.stderr
    value=json.loads(r.stdout)
    assert value['sourcesImported']==1 and value['selectedSourceIds']==['EV-002']
    assert value['conflicts']==[] and value['status']=='unreviewed'
    assert value['temporaryDataCleaned'] and value['productionLogin'] is False


def test_quit_does_not_execute_missing_core():
    r=execute('--core-command','/private/nonexistent-demo-core','--choice','q','--json')
    assert r.returncode==0,r.stdout+r.stderr
    assert json.loads(r.stdout)=={'fixture':'fictional','cancelled':True,'saved':False,
        'temporaryDataCleaned':True,'productionLogin':False,'networkListener':False}


def test_interactive_quit():
    r=execute('--core-command','/private/nonexistent-demo-core',stdin='q\n')
    assert r.returncode==0 and '未计算' in r.stdout
    assert '已计算、保存' not in r.stdout


@pytest.mark.parametrize('stdin',['wrong\n',''])
def test_interactive_invalid_or_eof_has_no_success(stdin):
    r=execute('--core-command','/private/nonexistent-demo-core',stdin=stdin)
    assert r.returncode==2
    assert '演示未完成' in r.stdout and '已清理' not in r.stdout and 'Traceback' not in r.stderr
    assert 'nonexistent-demo-core' not in r.stdout+r.stderr


def test_json_requires_explicit_choice():
    r=execute('--core-command','/private/nonexistent-demo-core','--json')
    assert r.returncode==2 and not r.stdout
    assert '--json requires --choice' in r.stderr


@pytest.mark.skipif(not CORE,reason='actual W2 required')
def test_transport_has_no_python_network_or_legacy_app(monkeypatch):
    from mcis_service import main
    def forbidden(*_args,**_kw):raise AssertionError('network/legacy forbidden')
    monkeypatch.setattr(socket.socket,'bind',forbidden)
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    monkeypatch.setattr(main,'create_app',forbidden)
    result=asyncio.run(demo.run_demo(CORE,'both'))
    assert result['sourcesImported']==2 and result['conflicts'][0]['delta']==5


def test_credentials_never_appear_in_summary(monkeypatch):
    tokens=[];issue=demo.local.issue_session
    def record(*args,**kwargs):
        token=issue(*args,**kwargs);tokens.append(token);return token
    monkeypatch.setattr(demo.local,'issue_session',record)
    value=asyncio.run(demo.run_demo('/not/a/core','q'))
    assert len(tokens)==1 and tokens[0] not in json.dumps(value)
    assert set(value)=={'fixture','cancelled','saved','temporaryDataCleaned','productionLogin','networkListener'}


def watch_dirs(monkeypatch,tmp_path):
    original=tempfile.TemporaryDirectory;paths=[]
    def make(**kwargs):
        directory=original(dir=tmp_path,**kwargs);paths.append(Path(directory.name));return directory
    monkeypatch.setattr(demo.tempfile,'TemporaryDirectory',make)
    return paths


def test_fixture_prepare_failure_disposes_and_cleans(monkeypatch,tmp_path,capsys):
    paths=watch_dirs(monkeypatch,tmp_path)
    async def fail(*_):raise RuntimeError('PRIVATE-PATH-TOKEN')
    monkeypatch.setattr(demo,'prepare',fail)
    assert demo.main(['--core-command','/unused','--choice','q'])==2
    assert all(not path.exists() for path in paths)
    out=capsys.readouterr();assert 'PRIVATE-PATH-TOKEN' not in out.out+out.err
    assert '已清理' not in out.out


def test_cleanup_failure_not_claimed_success(monkeypatch,capsys):
    original=tempfile.TemporaryDirectory
    class FailedCleanup:
        def __init__(self,**kwargs):self.inner=original(**kwargs)
        def __enter__(self):return self.inner.__enter__()
        def __exit__(self,*args):
            self.inner.__exit__(*args)
            raise OSError('PRIVATE-CLEANUP-DETAIL')
    monkeypatch.setattr(demo.tempfile,'TemporaryDirectory',FailedCleanup)
    assert demo.main(['--core-command','/unused','--choice','q','--json'])==2
    out=capsys.readouterr().out
    assert 'temporaryDataCleaned' not in out and 'PRIVATE-CLEANUP-DETAIL' not in out and '已清理' not in out


def test_keyboard_interrupt_input_cleans(monkeypatch,tmp_path):
    paths=watch_dirs(monkeypatch,tmp_path)
    def stop(_):raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):asyncio.run(demo.run_demo('/unused',interactive_input=stop))
    assert paths and all(not p.exists() for p in paths)


def test_existing_environment_data_untouched(monkeypatch,tmp_path):
    db=tmp_path/'user.db';db.write_text('original-db')
    data=tmp_path/'userdata';data.mkdir();marker=data/'keep';marker.write_text('original-data')
    monkeypatch.setenv('MCIS_DB_URL',f'sqlite:///{db}')
    monkeypatch.setenv('MCIS_DATA_DIR',str(data))
    monkeypatch.setenv('MCIS_SEED_DEMO','1')
    monkeypatch.setenv('MCIS_CORE','/untrusted-env-command')
    monkeypatch.setenv('MCIS_PORT','9999')
    value=asyncio.run(demo.run_demo('/unused','q'))
    assert value['cancelled']
    assert db.read_text()=='original-db' and marker.read_text()=='original-data'
    assert sorted(p.name for p in data.iterdir())==['keep']
