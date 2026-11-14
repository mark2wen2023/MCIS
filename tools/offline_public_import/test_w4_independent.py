import json,copy
import pytest
import assemble as a
from test_w4 import derivative

@pytest.mark.parametrize('raw',[b'null',b'[]',b'{}',b'{"x":1,"x":2}',b'{bad',b'NaN'])
def test_explicit_invalid_derivative_never_fallback(tmp_path,monkeypatch,raw):
 source=tmp_path/'d.json';source.write_bytes(raw);out=tmp_path/'new.json';calls=[]
 def forbidden(*args,**kwargs):calls.append(args);raise AssertionError('legacy parser forbidden')
 monkeypatch.setattr(a.subprocess,'run',forbidden)
 assert a.main(['--material-id',a.MATERIAL,'--output',str(out),'--bundle','--derivative',str(source)])==2
 assert calls==[] and not out.exists()

def test_bundle_no_overwrite(derivative,tmp_path):
 source=tmp_path/'d.json';source.write_text(json.dumps(derivative));out=tmp_path/'existing.json';out.write_bytes(b'KEEP')
 assert a.main(['--material-id',a.MATERIAL,'--output',str(out),'--bundle','--derivative',str(source)])==2
 assert out.read_bytes()==b'KEEP'

def test_supplied_artifact_alias_is_currently_input(derivative):
 before=copy.deepcopy(derivative);b=a.assemble_bundle(a.MATERIAL,derivative)
 assert derivative==before
 assert b['packet']['locator']['exactExcerpt']==b['packet']['candidate']['content']['source']['excerpt']
 assert b['linkage']['parserExecutionVerified'] is False and b['admissionAllowed'] is False
