"""Independent parser-boundary tests, local synthetic processes and fixtures."""
from pathlib import Path
import hashlib
import os
import signal
import sys
import time
from dataclasses import replace
import pytest
from derive import derive, Limits, DerivationError, run_bounded

@pytest.mark.parametrize('value',[True, float('nan'),float('inf'),0,-1,301])
def test_invalid_time_limits(value):
    with pytest.raises(DerivationError,match='invalid_limits'):
        derive(b'%PDF-1.7',Limits(seconds=value))

@pytest.mark.parametrize('value',[bytearray(b'%PDF-1.7'),memoryview(b'%PDF-1.7')])
def test_input_must_be_immutable_bytes(value):
    with pytest.raises(DerivationError,match='immutable_bytes_required'):derive(value)


def test_combined_output_exact_budget_and_excess():
    args=[sys.executable,'-c',"import os;os.write(1,b'123');os.write(2,b'45')"]
    assert run_bounded(args,deadline=time.monotonic()+2,limit=5)==(b'123',b'45')
    with pytest.raises(DerivationError,match='output_budget'):
        run_bounded(args,deadline=time.monotonic()+2,limit=4)


def test_nonzero_parser_is_failure_even_with_output():
    with pytest.raises(DerivationError,match='parser_failed'):
        run_bounded([sys.executable,'-c',"print('partial');raise SystemExit(7)"],deadline=time.monotonic()+2,limit=100)


def test_inherited_pipe_descendant_terminated_after_timeout(tmp_path):
    pidfile=tmp_path/'pid'
    code="import subprocess,sys; p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(20)']);open(sys.argv[1],'w').write(str(p.pid))"
    child=None
    try:
        with pytest.raises(DerivationError,match='time_budget'):
            run_bounded([sys.executable,'-c',code,str(pidfile)],deadline=time.monotonic()+.5,limit=100)
        child=int(pidfile.read_text())
        # A zombie is dead and awaiting init reaping; do not mistake it for a live child.
        stat=Path(f'/proc/{child}/stat')
        def alive():
            try:return stat.read_text().split()[2]!='Z'
            except (FileNotFoundError,ProcessLookupError):return False
        until=time.monotonic()+.3
        while alive() and time.monotonic()<until:
            time.sleep(.01)
        assert not alive(), 'descendant still running after deadline'

    finally:
        if child is None and pidfile.exists():child=int(pidfile.read_text())
        if child:
            try:os.kill(child,signal.SIGKILL)
            except ProcessLookupError:pass

@pytest.mark.parametrize('page_output,error',[(b'\xff','invalid_text_encoding'),(b'ok','parser_warning')])
def test_page_parser_corruption_not_success(monkeypatch,page_output,error):
    import importlib
    module=importlib.import_module('derive')
    responses=iter([(b'',b'fake-tool-version\n'),(b'Pages: 1\nEncrypted: no\n',b''),(page_output,b'warning' if error=='parser_warning' else b'')])
    monkeypatch.setattr(module,'run_bounded',lambda *a,**k:next(responses))
    with pytest.raises(DerivationError,match=error):derive(b'%PDF-1.7 fake')


def test_second_page_failure_never_returns_partial_artifact(monkeypatch):
    import importlib
    module=importlib.import_module('derive')
    responses=iter([(b'',b'fake-tool-version\n'),(b'Pages: 2\nEncrypted: no\n',b''),(b'first page',b''),(b'partial second',b'warning')])
    monkeypatch.setattr(module,'run_bounded',lambda *a,**k:next(responses))
    result=None
    with pytest.raises(DerivationError,match='parser_warning'):result=derive(b'%PDF-1.7 fake')
    assert result is None
