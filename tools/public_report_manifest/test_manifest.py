"""Synthetic protocol fixtures only; no PDF semantic or model evaluation."""
import copy,json,os,stat
import pytest
from manifest import preview,sha,PROFILE,Invalid,main
RAW=b'%PDF-synthetic marker only; deliberately not valid PDF'
def manifest():
 return dict(profile=PROFILE,title='明确合成测试',publisher='测试者',sourceUrl='https://example.com/fixture.pdf',publicationDate=None,fileSha256=sha(RAW),locators=[dict(pdfPage=1,printedPage='i',label='合成定位')])
def run(m=None,raw=RAW):return preview(json.dumps(m or manifest(),ensure_ascii=False).encode(),raw)
def test_valid_unverified():
 d=run();assert d['manifest']==manifest();assert not d['caseWritten'] and not d['modelUsed'] and not d['networkUsed']
 assert not d['pageLocatorsVerified'] and not d['pdfStructureValidated'] and d['sourceAuthenticity']=='not_verified'
@pytest.mark.parametrize('url',['http://example.com/a','https://user:pass@example.com/a','https://example.com/a?key=secret','https://example.com/a?','https://example.com/#','https://localhost./a','https://127.0.0.1/a','https://127.1/a','https://example.local/a'])
def test_bad_urls(url):
 m=manifest();m['sourceUrl']=url
 with pytest.raises(Invalid):run(m)
@pytest.mark.parametrize('page',[0,-1,10001,True,1.0,'1'])
def test_bad_pages(page):
 m=manifest();m['locators'][0]['pdfPage']=page
 with pytest.raises(Invalid):run(m)
@pytest.mark.parametrize('date',['2026-02-30','20261114','2026-1-1',True])
def test_bad_date(date):
 m=manifest();m['publicationDate']=date
 with pytest.raises(Invalid):run(m)
def test_digest_mismatch():
 with pytest.raises(Invalid):run(raw=RAW+b'changed')
def test_no_pdf_validation_claim():
 assert run()['byteLength']==len(RAW)
def test_duplicate_json():
 raw=json.dumps(manifest()).replace('"profile":','"title":"other","profile":').encode()
 with pytest.raises(Invalid):preview(raw,RAW)
def test_unknown_field_rejected():
 m=manifest();m['approved']=True
 with pytest.raises(Invalid):run(m)
def test_duplicate_locator_rejected():
 m=manifest();m['locators']*=2
 with pytest.raises(Invalid):run(m)
def test_page_does_not_infer_printed_page():
 m=manifest();m['locators'][0]['printedPage']=None
 assert run(m)['manifest']['locators'][0]['printedPage'] is None

def inputs(tmp_path):
 p=tmp_path/'f.pdf';p.write_bytes(RAW);m=tmp_path/'m.json';m.write_text(json.dumps(manifest()));o=tmp_path/'out.json';return m,p,o

def cli(m,p,o):return main(['--manifest',str(m),'--pdf',str(p),'--output',str(o)])
def test_cli_new_output(tmp_path):
 m,p,o=inputs(tmp_path);assert cli(m,p,o)==0
 assert json.loads(o.read_bytes())['manifest']==manifest();assert stat.S_IMODE(o.stat().st_mode)==0o600
 before=o.read_bytes();assert cli(m,p,o)==3 and o.read_bytes()==before

def test_validation_before_write(tmp_path):
 m,p,o=inputs(tmp_path);p.write_bytes(RAW+b'changed');assert cli(m,p,o)==4 and not o.exists()
@pytest.mark.parametrize('target',['manifest','pdf','output','parent'])
def test_symlinks_rejected(tmp_path,target):
 m,p,o=inputs(tmp_path);link=tmp_path/'link'
 if target=='manifest':link.symlink_to(m);m=link
 elif target=='pdf':link.symlink_to(p);p=link
 elif target=='output':link.symlink_to(o);o=link
 else:link.symlink_to(tmp_path,target_is_directory=True);o=link/'out.json'
 assert cli(m,p,o)==3
 assert not (tmp_path/'out.json').exists()

def test_fifo_does_not_wait(tmp_path):
 m,p,o=inputs(tmp_path);p.unlink();os.mkfifo(p);assert cli(m,p,o)==4 and not o.exists()

def test_no_network(tmp_path,monkeypatch):
 import socket
 monkeypatch.setattr(socket,'socket',lambda *a,**kw:pytest.fail('network forbidden'))
 m,p,o=inputs(tmp_path);assert cli(m,p,o)==0
