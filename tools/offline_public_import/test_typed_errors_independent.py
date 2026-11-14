import pytest
import assemble as a
import adapter
from test_typed_errors import artifact

@pytest.mark.parametrize('error',[adapter.Rejected('/private/secret\nSTACK'),adapter.Rejected(['secret']),RuntimeError('secret full diagnostic'),adapter.Rejected('PAGE_SHA')])
def test_adapter_errors_whitelisted(error,artifact,tmp_path,monkeypatch,capsys):
 def bad(*args,**kwargs):raise error
 monkeypatch.setattr(adapter,'consume',bad)
 # main invokes the supplied-artifact path, whose exceptions must be contained.
 import json
 src=tmp_path/'secret-artifact.json';src.write_text(json.dumps(artifact));out=tmp_path/'secret-output.json'
 assert a.main(['--material-id',a.MATERIAL,'--bundle','--derivative',str(src),'--output',str(out)])==2
 captured=capsys.readouterr();assert 'secret' not in captured.err+captured.out and str(tmp_path) not in captured.err
 assert ('PAGE_BINDING_MISMATCH' if error.args==('PAGE_SHA',) else 'W4_LINK_REJECTED') in captured.err
 assert not out.exists()

@pytest.mark.parametrize('args',[['--material-id'],['--output'],['--material-id','secret','--output','secret','--derivative','secret']])
def test_parser_error_arguments_hidden(args,capsys):
 with pytest.raises(SystemExit) as e:a.main(args)
 assert e.value.code==2
 c=capsys.readouterr();assert 'secret' not in c.err+c.out and 'CLI_ARGUMENT_INVALID' in c.err

def test_legacy_success_reports_unknown(tmp_path,capsys):
 out=tmp_path/'ok.json'
 assert a.main(['--material-id',a.MATERIAL,'--output',str(out)])==0
 c=capsys.readouterr();assert not c.err and 'W4 linkage UNKNOWN' in c.out
 assert 'byte consistency only' not in c.out

def test_filename_in_oserror_hidden(monkeypatch,tmp_path,capsys):
 def failed(*args,**kwargs):raise PermissionError(13,'secret reason','/private/secret')
 monkeypatch.setattr(a,'write_new',failed)
 assert a.main(['--material-id',a.MATERIAL,'--output',str(tmp_path/'out')])==2
 err=capsys.readouterr().err
 assert 'IO_FAILED' in err and 'secret' not in err and '/private' not in err
