import copy,json
import pytest
import assemble as a
from derive import derive
@pytest.fixture(scope='module')
def artifact():return derive(a.PDF.read_bytes())
@pytest.mark.parametrize('case,expected',[
 ('repeat','PAGE_ANCHORS_AMBIGUOUS'),('missing','PAGE_ANCHORS_NOT_FOUND'),
 ('version','TOOL_VERSION_MISMATCH'),('schema','DERIVATIVE_VERSION_MISMATCH'),
 ('pagehash','PAGE_BINDING_MISMATCH'),('source','SOURCE_BYTES_CHANGED'),
 ('null','W4_ARTIFACT_OBJECT_REQUIRED'),('json','W4_ARTIFACT_JSON_INVALID')])
def test_public_artifact_rejections(artifact,case,expected,tmp_path,capsys):
 d=copy.deepcopy(artifact)
 if case=='repeat':d['pages'][23]['text']+='（四）结论。'
 if case=='missing':d['pages'][23]['text']=d['pages'][23]['text'].replace('（四）结论。','')
 if case=='version':d['tool']='secret-version-do-not-echo'
 if case=='schema':d['version']=99
 if case=='pagehash':d['pages'][23]['textSha256']='0'*64
 if case=='source':d['sourcePdfSha256']='0'*64
 p=tmp_path/'private-location.json';p.write_text('null' if case=='null' else '{secret' if case=='json' else json.dumps(d));out=tmp_path/'out.json'
 original=a.PDF.read_bytes();before=p.read_bytes()
 assert a.main(['--material-id',a.MATERIAL,'--bundle','--derivative',str(p),'--output',str(out)])==2
 err=capsys.readouterr().err;assert expected in err
 assert 'secret' not in err and str(tmp_path) not in err
 assert not out.exists() and p.read_bytes()==before and a.PDF.read_bytes()==original
@pytest.mark.parametrize('error',[a.Rejected('/private/secret'),a.Rejected(['secret']),ValueError('secret'),OSError('secret')])
def test_untrusted_error_text_never_echoes(error,tmp_path,monkeypatch,capsys):
 def fail(*args,**kwargs):raise error
 monkeypatch.setattr(a,'assemble',fail)
 assert a.main(['--material-id',a.MATERIAL,'--output',str(tmp_path/'x')])==2
 assert 'secret' not in capsys.readouterr().err
 assert not (tmp_path/'x').exists()
def test_argparse_unknown_does_not_echo(capsys):
 with pytest.raises(SystemExit) as e:a.main(['--private-secret=/private/secret'])
 assert e.value.code==2
 err=capsys.readouterr().err;assert 'CLI_ARGUMENT_INVALID' in err and 'secret' not in err
