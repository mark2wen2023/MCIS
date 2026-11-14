"""Independent tests using synthetic marker bytes, not PDF/model evaluation."""
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
import pytest
import manifest as impl
from test_manifest import RAW, manifest, inputs, cli

def test_declared_fields_never_read_as_paths(tmp_path):
 m,p,o=inputs(tmp_path);doc=manifest();doc['path']=str(tmp_path/'secret')
 m.write_text(json.dumps(doc));assert cli(m,p,o)==4 and not o.exists()

@pytest.mark.parametrize('change',[
 lambda m:m.update(title='\ud800'),lambda m:m.update(publisher='x\u0001y'),
 lambda m:m['locators'][0].update(label='\n'),lambda m:m['locators'][0].update(pdfPage=1.0),
 lambda m:m.update(publicationDate=[]),lambda m:m.update(fileSha256=impl.sha(RAW).upper()),
])
def test_bad_structures_rejected(change):
 m=manifest();change(m)
 with pytest.raises(impl.Invalid):impl.preview(json.dumps(m).encode(),RAW)

def test_nonfinite_deep_duplicate_reject():
 raw=json.dumps(manifest()).replace('"pdfPage": 1','"pdfPage": 1, "pdfPage": 2').encode()
 with pytest.raises(impl.Invalid):impl.preview(raw,RAW)
 with pytest.raises(impl.Invalid):impl.preview(b'{"x":NaN}',RAW)

def test_file_and_manifest_budgets():
 with pytest.raises(impl.Invalid):impl.preview(b' '*65537,RAW)
 with pytest.raises(impl.Invalid):impl.preview(json.dumps(manifest()).encode(),b'%PDF-'+b'x'*(impl.MAX_FILE-4))

def test_directory_input_and_parent_traversal(tmp_path):
 m,p,o=inputs(tmp_path);p.unlink();p.mkdir()
 assert cli(m,p,o)==3 and not o.exists()  # fdopen rejects directory as I/O failure
 assert impl.main(['--manifest',str(tmp_path/'..'/tmp_path.name/'m.json'),'--pdf',str(p),'--output',str(o)])==4

def test_input_parent_symlink_rejected(tmp_path):
 real=tmp_path/'actual';real.mkdir();m,p,o=inputs(real)
 link=tmp_path/'linked';link.symlink_to(real,target_is_directory=True)
 assert cli(link/'m.json',p,tmp_path/'out.json')==3 and not (tmp_path/'out.json').exists()

def test_output_cannot_overwrite_input(tmp_path):
 m,p,o=inputs(tmp_path);old=p.read_bytes()
 assert cli(m,p,p)==3 and p.read_bytes()==old

def test_fsync_failure_not_success(tmp_path,monkeypatch,capsys):
 m,p,o=inputs(tmp_path)
 def fail(*a):raise OSError('sensitive-path-do-not-print')
 monkeypatch.setattr(impl.os,'fsync',fail)
 assert cli(m,p,o)==3
 assert 'sensitive-path' not in capsys.readouterr().err
 assert o.exists() and stat.S_IMODE(o.stat().st_mode)==0o600

def test_no_safe_flags_no_fallback(tmp_path,monkeypatch):
 m,p,o=inputs(tmp_path);monkeypatch.delattr(impl.os,'O_NOFOLLOW')
 assert cli(m,p,o)==4 and not o.exists()

def test_validation_error_no_content_or_path_echo(tmp_path,capsys):
 m,p,o=inputs(tmp_path);doc=manifest();doc['fileSha256']='secret-invalid-value';m.write_text(json.dumps(doc))
 assert cli(m,p,o)==4
 err=capsys.readouterr().err
 assert 'secret-invalid-value' not in err and str(tmp_path) not in err

def test_fifo_cli_finishes(tmp_path):
 m,p,o=inputs(tmp_path);p.unlink();os.mkfifo(p)
 run=subprocess.run([sys.executable,str(Path(impl.__file__)), '--manifest',str(m),'--pdf',str(p),'--output',str(o)],capture_output=True,timeout=3)
 assert run.returncode==4 and not o.exists()

def test_not_page_count_or_authenticity(tmp_path):
 m,p,o=inputs(tmp_path);doc=manifest();doc['locators'][0]['pdfPage']=10000;m.write_text(json.dumps(doc))
 assert cli(m,p,o)==0
 d=json.loads(o.read_bytes());assert d['manifest']['locators'][0]['pdfPage']==10000
 assert d['pageLocatorsVerified'] is False and d['sourceAuthenticity']=='not_verified' and d['caseWritten'] is False
