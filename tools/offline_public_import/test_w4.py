import copy,json,sys,importlib.util
from pathlib import Path
import pytest
import assemble as a
@pytest.fixture(scope='module')
def derivative():
 p=a.ROOT/'tools/pdf_text_layer/derive.py'
 assert a.sha(p.read_bytes())=='39d57ffd056cd98d50d5743ec4ee809a05f1994f82b356c50befa8e15e381508'
 spec=importlib.util.spec_from_file_location('cli_w4_checked',p);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
 return m.derive(a.PDF.read_bytes())
def test_real_bundle_without_legacy_parser(derivative,monkeypatch):
 def forbidden(*args,**kwargs):raise AssertionError('must consume supplied artifact')
 monkeypatch.setattr(a.subprocess,'run',forbidden)
 b=a.assemble_bundle(a.MATERIAL,derivative)
 assert b['packet']['candidate']['status']=='Candidate' and not b['admissionAllowed']
 assert b['linkage']['linkStatus']=='supplied_bytes_aligned_not_authenticated'
 assert b['packet']['locator']['pageTextSha256']==derivative['pages'][23]['textSha256']
 assert b['derivativeArtifact']==derivative
@pytest.mark.parametrize('kind',['pdf','page','hash','tool','parameters','version'])
def test_invalid_artifact_no_fallback(derivative,kind,monkeypatch):
 d=copy.deepcopy(derivative)
 if kind=='pdf':d['sourcePdfSha256']='0'*64
 elif kind=='page':d['pages'][23]['physicalPage']=22
 elif kind=='hash':d['pages'][23]['textSha256']='0'*64
 elif kind=='tool':d['tool']='unapproved'
 elif kind=='parameters':d['parameters']=[]
 elif kind=='version':d['version']=2
 with pytest.raises(a.Rejected):a.assemble_bundle(a.MATERIAL,d)
def test_missing_artifact_unknown():
 b=a.assemble_bundle(a.MATERIAL)
 assert b['linkage']['linkStatus']=='unknown_no_derivative' and not b['admissionAllowed']
def test_bundle_cli(derivative,tmp_path):
 source=tmp_path/'derivative.json';source.write_text(json.dumps(derivative));output=tmp_path/'bundle.json'
 assert a.main(['--material-id',a.MATERIAL,'--output',str(output),'--bundle','--derivative',str(source)])==0
 b=json.loads(output.read_bytes());assert not b['admissionAllowed'] and b['derivativeArtifact']==derivative
def test_bad_json_no_output(tmp_path):
 p=tmp_path/'bad.json';p.write_text('{"version":1,"version":2}');out=tmp_path/'out.json'
 assert a.main(['--material-id',a.MATERIAL,'--output',str(out),'--bundle','--derivative',str(p)])==2
 assert not out.exists()
def test_explicit_bundle_required(tmp_path):
 with pytest.raises(SystemExit):a.main(['--material-id',a.MATERIAL,'--output',str(tmp_path/'out'),'--derivative','x'])
 assert not (tmp_path/'out').exists()
def test_existing_destination_unchanged(derivative,tmp_path):
 src=tmp_path/'d.json';src.write_text(json.dumps(derivative));out=tmp_path/'out';out.write_text('keep')
 assert a.main(['--material-id',a.MATERIAL,'--output',str(out),'--bundle','--derivative',str(src)])==2
 assert out.read_text()=='keep'
