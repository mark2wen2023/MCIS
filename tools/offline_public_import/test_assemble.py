import copy,json,os
from pathlib import Path
import pytest
import assemble as a
@pytest.fixture(scope='module')
def packet():return a.assemble(a.MATERIAL)
def test_real_report_all_pending(packet):
 p=packet;assert p['candidate']['status']=='Candidate'
 c=p['candidate']['content'];assert c['body']==c['summary']==c['source']['excerpt']==p['locator']['exactExcerpt']
 assert p['locator']['pdfPage']==24 and p['locator']['printedPage']==22
 assert all(x['status']=='pending' for x in p['worksheet']['checks']+p['worksheet']['requiredReleaseApprovals'])
 assert p['reviewRecords']==[] and not p['approvalGranted'] and not p['authorizationVerified']
 assert p['sourceAuthenticity']=='not_verified' and not p['freshness']['sourceCurrentnessVerified']
 assert not any(p[k] for k in ('modelUsed','ocrUsed','networkUsed','formalDatabaseUsed'))
def test_original_unchanged(packet):assert a.sha(a.PDF.read_bytes())==a.SHA==packet['bindings']['sourceFileSha256']
def test_unknown_material():
 with pytest.raises(a.Rejected):a.assemble('private-case')
def test_changed_pdf_rejected(tmp_path,monkeypatch):
 p=tmp_path/'x.pdf';p.write_bytes(b'changed');monkeypatch.setattr(a,'PDF',p)
 with pytest.raises(a.Rejected,match='SOURCE_BYTES'):a.assemble(a.MATERIAL)
def test_symlink_refused(tmp_path,monkeypatch):
 p=tmp_path/'x.pdf';p.symlink_to(a.PDF);monkeypatch.setattr(a,'PDF',p)
 with pytest.raises(OSError):a.assemble(a.MATERIAL)
def test_atomic_write_and_no_overwrite(packet,tmp_path):
 p=tmp_path/'packet.json';a.write_new(p,packet);raw=p.read_bytes();assert json.loads(raw)==packet
 assert p.stat().st_mode & 0o777==0o600
 with pytest.raises(FileExistsError):a.write_new(p,packet)
 assert p.read_bytes()==raw and not list(tmp_path.glob('.pending-*'))
def test_final_link_failure_no_partial(packet,tmp_path,monkeypatch):
 def fail(*args,**kwargs):raise OSError('simulated link failure')
 monkeypatch.setattr(a.os,'link',fail)
 with pytest.raises(OSError):a.write_new(tmp_path/'packet.json',packet)
 assert list(tmp_path.iterdir())==[]
def test_symlink_output_parent(packet,tmp_path):
 real=tmp_path/'real';real.mkdir();link=tmp_path/'link';link.symlink_to(real)
 with pytest.raises(OSError):a.write_new(link/'packet.json',packet)
 assert not list(real.iterdir())
def test_cli_unknown_does_not_write(tmp_path):
 p=tmp_path/'packet.json';assert a.main(['--material-id','unknown','--output',str(p)])==2;assert not p.exists()
def test_html_serialization_inert(packet,tmp_path):
 p=copy.deepcopy(packet);p['note']='<script>fetch("https://bad")</script>';out=tmp_path/'x.json';a.write_new(out,p)
 assert b'<script>' not in out.read_bytes();assert json.loads(out.read_bytes())['note']==p['note']
