import pytest
from .test_knowledge_w19 import c,H,B,content
from .test_knowledge_archive import counts
@pytest.mark.parametrize('host',['exa%mple.com','.example.com','example..com','-example.com','example-.com'])
def test_invalid_source_hostname_rejected_without_writes(c,host):
 data=content();data['source']['type']='Public';data['source']['url']='https://'+host+'/report.pdf'
 before=counts(c);r=c.post(B+'/cards',headers=H('Investigator'),json=data)
 assert r.status_code==422,r.text
 assert counts(c)==before

@pytest.mark.parametrize('url',['https://example.com/report.pdf','https://example.com./report.pdf','https://例子.中国/report.pdf','https://8.8.8.8/report.pdf'])
def test_valid_syntax_not_authenticity(c,url):
 data=content();data['source']['type']='Public';data['source']['url']=url
 r=c.post(B+'/cards',headers=H('Investigator'),json=data)
 assert r.status_code==201,r.text
 assert r.json()['status']=='Candidate' and r.json()['content']['source']['url']==url

def test_legacy_validation_not_rewritten():
 from mcis_service.knowledge.router import validate_content
 data=content();data['source']['type']='Public';data['source']['url']='https://exa%mple.com/report.pdf'
 validate_content(data) # Compatibility only; new create now separately rejects.

@pytest.mark.parametrize('url',['https://[2606:4700:4700::1111]/report.pdf','https://127.0.0.1/report.pdf','https://localhost/report.pdf'])
def test_existing_address_policy_unchanged(c,url):
 data=content();data['source']['type']='Public';data['source']['url']=url
 before=counts(c);r=c.post(B+'/cards',headers=H('Investigator'),json=data)
 assert r.status_code==422 and counts(c)==before

def test_legacy_bad_host_archive_stays_readable(c,monkeypatch):
 from mcis_service.knowledge import router
 from .test_knowledge_archive import export,save
 import json
 data=content();data['source']['type']='Public';data['source']['url']='https://exa%mple.com/report.pdf'
 # Simulate a pre-fix row using the unchanged writer, in temporary test DB only.
 with monkeypatch.context() as patch:
  patch.setattr(router,'validate_new_source_host',lambda source:None)
  assert c.post(B+'/cards',headers=H('Investigator'),json=data).status_code==201
 raw=export(c)
 assert json.loads(raw)['cards'][0]['doc']['content']['source']['url']==data['source']['url']
 assert save(c,raw).status_code==201
 assert c.post(B+'/cards',headers=H('Investigator'),json=data).status_code==422

@pytest.mark.parametrize('terminal_dot',[False,True])
def test_dns_max_length(c,terminal_dot):
 suffix='.' if terminal_dot else ''
 for last,status in [(61,201),(62,422)]:
  host='.'.join(['a'*63]*3+['b'*last])+suffix
  data=content();data['source']['type']='Public';data['source']['url']='https://'+host+'/report.pdf'
  assert c.post(B+'/cards',headers=H('Investigator'),json=data).status_code==status
