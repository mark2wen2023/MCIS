import copy,json
from pathlib import Path
import pytest
import assemble as a

def test_no_subprocess_run_fallback(monkeypatch):
 def fail(*args,**kwargs):raise AssertionError('legacy subprocess.run forbidden')
 monkeypatch.setattr(a.subprocess,'run',fail)
 bundle=a.assemble_bundle(a.MATERIAL)
 assert bundle['linkage']['linkStatus']=='unknown_no_derivative'
 assert bundle['packet']['locator']['pdfPage']==24 and bundle['packet']['locator']['printedPage']==22
 assert bundle['admissionAllowed'] is False

@pytest.mark.parametrize('mode',['bad_utf8','snapshot_changed','no_tool'])
def test_failure_stays_unwritten(tmp_path,monkeypatch,mode):
 original=a.run_bounded
 def controlled(argv,**kwargs):
  if mode=='bad_utf8':return b'\xff',b''
  result=original(argv,**kwargs)
  if mode=='snapshot_changed' and argv[-1]!='-v':
   p=Path(argv[-2]);p.chmod(0o600);p.write_bytes(b'changed snapshot')
  return result
 monkeypatch.setattr(a,'run_bounded',controlled)
 if mode=='no_tool':monkeypatch.setattr(a.shutil,'which',lambda _:None)
 out=tmp_path/'out.json'
 assert a.main(['--material-id',a.MATERIAL,'--output',str(out)])==2
 assert not out.exists()

def test_real_legacy_extracted_content_matches_fixed_packet():
 packet=a.assemble(a.MATERIAL)
 reference=json.loads((a.ROOT/'service/tests/fixtures/pending_packet/yangze22-pending.json').read_bytes())
 for key in ['exactExcerpt','pageExtractedText','pageTextSha256','pdfPage','printedPage','excerptSha256']:
  assert packet['locator'][key]==reference['locator'][key]
 assert packet['candidate']['content']==reference['candidate']['content']
 assert packet['approvalGranted'] is False and packet['authorizationVerified'] is False
