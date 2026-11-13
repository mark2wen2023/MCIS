import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
from mcis_service.identity import demo

CORE=os.getenv('MCIS_PREFLIGHT_REAL_CORE')
pytestmark=pytest.mark.skipif(not CORE,reason='explicit actual W2 required')


def test_subprocess_both_real_core():
    r=subprocess.run([sys.executable,'-m','mcis_service.identity.demo','--core-command',CORE,'--choice','both','--json'],capture_output=True,text=True,timeout=30)
    assert r.returncode==0,r.stdout+r.stderr
    result=json.loads(r.stdout)
    assert result['saved'] and result['read'] and result['status']=='unreviewed'
    assert result['sourcesImported']==2 and result['conflicts'][0]['delta']==5
    assert result['temporaryDataCleaned'] and not result['networkListener']
    assert 'Bearer' not in r.stdout and 'token' not in r.stdout.lower()


def test_interactive_single_real_core():
    r=subprocess.run([sys.executable,'-m','mcis_service.identity.demo','--core-command',CORE],input='1\n',capture_output=True,text=True,timeout=30)
    assert r.returncode==0,r.stdout+r.stderr
    assert '来源数：1' in r.stdout and '未审核' in r.stdout and '临时演示数据已清理' in r.stdout


def test_no_listener_or_old_app_and_env_db_ignored(monkeypatch,tmp_path):
    import socket
    from mcis_service import main
    monkeypatch.setattr(socket.socket,'bind',lambda *_:pytest.fail('must not bind sockets'))
    monkeypatch.setattr(main,'create_app',lambda *_:pytest.fail('must not instantiate legacy app'))
    marker=tmp_path/'existing.db';marker.write_text('keep')
    monkeypatch.setenv('MCIS_DB_URL','sqlite:///'+str(marker))
    result=asyncio.run(demo.run_demo(CORE,'both'))
    assert result['sourcesImported']==2 and marker.read_text()=='keep'


def test_failure_and_cancel_clean_temp(monkeypatch,tmp_path):
    from tempfile import TemporaryDirectory
    created=[]
    def folder(**kwargs):
        value=TemporaryDirectory(dir=tmp_path,**kwargs);created.append(Path(value.name));return value
    monkeypatch.setattr(demo.tempfile,'TemporaryDirectory',folder)
    result=asyncio.run(demo.run_demo('/not/a/core','q'))
    assert result['cancelled'] and not result['saved']
    with pytest.raises(Exception):asyncio.run(demo.run_demo('/not/a/core','both'))
    assert all(not path.exists() for path in created)


def test_cli_failure_sanitized(capsys):
    assert demo.main(['--core-command','/private/secret-not-a-core','--choice','both'])==2
    out=capsys.readouterr().out
    assert 'secret-not-a-core' not in out and '凭据' in out and '已计算' not in out
