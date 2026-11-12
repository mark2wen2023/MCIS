import copy
import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.knowledge.models import KnowledgeAuditRow, KnowledgeCardRow
from sqlalchemy import select, text

B='/api/v1/knowledge'
def H(role='LeadInvestigator'):return {'X-MCIS-Role':role}
def content(kind='Case'):
 return {'kind':kind,'title':'合成测试 100%_','summary':'仅验证知识卡流程','body':'合成正文，不是真实事故。','tags':['AIS','能见度'],'applicability':'不能当真实结论','source':{'type':'Synthetic','title':'合成夹具','locator':'段落1','excerpt':'合成正文','rightsNote':'测试作者构造，不含真实资料'}}
@pytest.fixture
def c(tmp_path):
 with TestClient(create_app(Settings(data_dir=tmp_path,seed_demo=False))) as c:yield c

def create(c,data=None):
 r=c.post(B+'/cards',json=data or content(),headers=H('Investigator'));assert r.status_code==201,r.text;return r.json()
def review(c,d,decision='Published',**changes):
 return c.post(B+'/cards/'+d['cardId']+'/review',headers=H(),json={'decision':decision,'expectedDigest':d['contentDigest'],'note':'已人工核查，允许发布合成测试样本','sourceVerified':True,'rightsVerified':True,'releaseApproved':True,**changes})
@pytest.mark.parametrize('kind',['Case','Challenge','Method'])
def test_lifecycle(c,kind):
 d=create(c,content(kind));assert d['status']=='Candidate'
 assert c.get(B+'/cards',headers=H('Public')).json()['total']==0
 assert c.get(B+'/cards/'+d['cardId'],headers=H('Public')).status_code==404
 assert review(c,d).status_code==200
 out=c.get(B+'/cards',headers=H('Public')).json()['items'][0]
 assert out['content']==d['content'] and 'reviewedBy' not in out and 'reviewNote' not in out and 'createdBy' not in out
 assert c.get(B+'/cards',params={'kind':kind,'tag':'ais','q':'100%_'},headers=H('Public')).json()['total']==1
 assert c.get(B+'/cards',params={'q':'100x_'},headers=H('Public')).json()['total']==0
 assert review(c,d,'Withdrawn').status_code==200
 assert c.get(B+'/cards',headers=H('Public')).json()['total']==0
 assert c.get(B+'/cards/'+d['cardId'],headers=H('Public')).status_code==404
 assert c.get(B+'/audit:verify',headers=H()).json()=={'valid':True,'count':3}
@pytest.mark.parametrize('role',['Public','ExternalExpert','InterestedState','AgentService'])
def test_role_boundary(c,role):
 d=create(c);h=H(role)
 assert c.post(B+'/cards',headers=h,json=content()).status_code==403
 for path in ['/cards?status=Candidate','/cards?status=Rejected','/cards?status=Withdrawn','/audit','/audit:verify']:assert c.get(B+path,headers=h).status_code==403
 assert c.post(B+'/cards/'+d['cardId']+'/review',headers=h,json={}).status_code==403
 assert c.get(B+'/cards',headers=h).status_code==200

def test_investigator_not_publisher(c):
 d=create(c);assert c.post(B+'/cards/'+d['cardId']+'/review',headers=H('Investigator'),json={}).status_code==403
 assert c.get(B+'/cards?status=Candidate',headers=H('Investigator')).json()['total']==1
@pytest.mark.parametrize('field',['sourceVerified','rightsVerified','releaseApproved'])
@pytest.mark.parametrize('value',[False,None,1,'true'])
def test_explicit_approvals(c,field,value):
 d=create(c);assert review(c,d,**{field:value}).status_code==422
 assert c.get(B+'/cards').json()['total']==0
 assert len(c.get(B+'/audit',headers=H()).json())==1

def test_reject_duplicate_and_digest(c):
 d=create(c);assert review(c,d,expectedDigest='0'*64).status_code==409
 assert review(c,d,'Rejected').status_code==200
 assert review(c,d).status_code==409
 assert c.get(B+'/cards').json()['total']==0
 assert c.get(B+'/audit:verify',headers=H()).json()['count']==2

def test_concurrent_publish_once(c):
 d=create(c)
 with ThreadPoolExecutor(2) as p:statuses=list(p.map(lambda _:review(c,d).status_code,range(2)))
 assert sorted(statuses)==[200,409]
 assert len(c.get(B+'/audit',headers=H()).json())==2

@pytest.mark.parametrize('mutate',[
 lambda d:d.update(secret='x'), lambda d:d.update(title='   '),lambda d:d.update(title='bad\x00'),lambda d:d.update(body='x'*6001),
 lambda d:d.update(tags=['AIS','ais']),lambda d:d.update(tags=['a|b']),lambda d:d['source'].update(type='Private'),
 lambda d:d['source'].update(url='https://example.com'),lambda d:d['source'].update(type='Public'),
 lambda d:d['source'].update(type='Public',url='javascript:alert(1)'),lambda d:d['source'].update(type='Public',url='https://127.0.0.1/x'),
 lambda d:d.update(summary='\ud800')])
def test_invalid_atomic(c,mutate):
 d=content();mutate(d)
 r=c.post(B+'/cards',headers={**H(),'Content-Type':'application/json'},content=json.dumps(d));assert r.status_code==422,r.text
 assert c.get(B+'/cards?status=Candidate',headers=H()).json()['total']==0
 assert c.get(B+'/audit',headers=H()).json()==[]

def test_public_url_not_fetch_or_auto_publish(c):
 d=content();d['source'].update(type='Public',url='https://example.com/explicit-test-not-a-report')
 card=create(c,d);assert c.get(B+'/cards').json()['total']==0
 assert card['status']=='Candidate'

def test_audit_append_only_and_rollback(c,monkeypatch):
 from mcis_service.knowledge import router
 def fail(*a,**kw):raise RuntimeError('simulated persistence failure')
 monkeypatch.setattr(router,'audit',fail)
 with pytest.raises(RuntimeError):create(c)
 assert c.get(B+'/cards?status=Candidate',headers=H()).json()['total']==0
 monkeypatch.undo();create(c)
 with pytest.raises(Exception):
  with c.app.state.db.session() as s:s.execute(text('DELETE FROM knowledge_audit'))
 assert c.get(B+'/audit:verify',headers=H()).json()['valid']

def test_pagination_literal_tag(c):
 for _ in range(3):review(c,create(c))
 r=c.get(B+'/cards?limit=2').json();assert len(r['items'])==2 and r['total']==3
 assert c.get(B+'/cards?tag=AIS%7C能见度').status_code==422
 assert c.get(B+'/cards?tag=A').json()['total']==0
 assert c.get(B+'/cards?limit=51').status_code==422
