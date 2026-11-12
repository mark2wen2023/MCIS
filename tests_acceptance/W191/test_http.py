"""Independent real TCP/HTTP W19.1 acceptance; only synthetic fixtures, temporary SQLite."""
import copy, hashlib, json, socket, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import httpx
import pytest
import uvicorn
from sqlalchemy import text
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'service'))
from mcis_service.main import create_app
from mcis_service.config import Settings
B='/api/v1/knowledge'
ROLES=['LeadInvestigator','Investigator','ExternalExpert','InterestedState','AgentService','Public']
PRIVATE={'createdBy','reviewedBy','reviewNote','approvals'}

def sample(kind='Case'):
 return dict(kind=kind,title='合成 <b>航行</b> 50%_\\ STRASSE',summary='not an accident report',body='literal needle 🌊 合成正文',tags=['Straße','AIS'],applicability='合成，不用于责任认定',source=dict(type='Synthetic',title='Synthetic author',locator='paragraph 1',excerpt='synthetic excerpt',rightsNote='test author permits synthetic example'))

@pytest.fixture
def api(tmp_path):
 app=create_app(Settings(data_dir=tmp_path,seed_demo=False))
 sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen(128)
 server=uvicorn.Server(uvicorn.Config(app,log_level='critical'))
 t=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);t.start()
 for _ in range(200):
  if server.started:break
  time.sleep(.01)
 assert server.started
 try:
  with httpx.Client(base_url=f'http://127.0.0.1:{sock.getsockname()[1]}',timeout=15,trust_env=False) as client:
   yield client,app
 finally:
  server.should_exit=True;t.join(10);sock.close();assert not t.is_alive()

def req(api,method,path,role='LeadInvestigator',**kw):
 return api[0].request(method,B+path,headers={'X-MCIS-Role':role,'X-MCIS-Operator':'private-operator'},**kw)
def make(api,kind='Case'):
 r=req(api,'POST','/cards',json=sample(kind));assert r.status_code==201,r.text;return r.json()
def decision(card,state='Published',**kw):
 return dict(decision=state,expectedDigest=card['contentDigest'],note='private reason',sourceVerified=True,rightsVerified=True,releaseApproved=True,**kw)
def review(api,card,state='Published',**kw):
 body=decision(card,state);body.update(kw)
 return req(api,'POST',f"/cards/{card['cardId']}/review",json=body)

@pytest.mark.parametrize('role',ROLES)
def test_role_matrix(api,role):
 card=make(api);internal=role in ROLES[:2]
 for state in ['Candidate','Rejected','Withdrawn']:
  assert req(api,'GET','/cards',role,params={'status':state}).status_code==(200 if internal else 403)
 for path in ['/audit','/audit:verify']:
  assert req(api,'GET',path,role).status_code==(200 if internal else 403)
 assert req(api,'GET','/cards/'+card['cardId'],role).status_code==(200 if internal else 404)
 assert req(api,'POST','/cards',role,json=sample()).status_code==(201 if internal else 403)
 assert req(api,'POST','/cards/'+card['cardId']+'/review',role,json=decision(card)).status_code==(200 if role==ROLES[0] else 403)
 if role!=ROLES[0]:assert review(api,card).status_code==200
 for path in ['/cards/'+card['cardId'],'/cards']:
  r=req(api,'GET',path,role);assert r.status_code==200
  result=r.json() if '/cards/' in path else r.json()['items'][0]
  assert bool(PRIVATE.intersection(result))==internal
 assert review(api,card,'Withdrawn').status_code==200
 assert req(api,'GET','/cards',role).json()['total']==0
 assert req(api,'GET','/cards/'+card['cardId'],role).status_code==(200 if internal else 404)

@pytest.mark.parametrize('kind',['Case','Challenge','Method'])
def test_search_detail_paging(api,kind):
 cards=[make(api,kind) for _ in range(3)]
 for c in cards:assert review(api,c).status_code==200
 for q in ['50%_\\','strasse','🌊','<b>','needle']:
  assert req(api,'GET','/cards','Public',params={'q':q,'kind':kind,'tag':'STRASSE'}).json()['total']==3
 for q in ['50xx','Synthetic author','paragraph 1',"' OR 1=1 --"]:
  assert req(api,'GET','/cards','Public',params={'q':q}).json()['total']==0
 for i in range(3):
  page=req(api,'GET','/cards','Public',params={'offset':i,'limit':1,'case':'unrelated'}).json()
  assert page['total']==3 and page['items'][0]['cardId']==cards[2-i]['cardId']
  assert page['items'][0]['content']==sample(kind)
 assert req(api,'GET','/cards','Public',params={'offset':3}).json()['items']==[]
 for p in [{'limit':0},{'limit':51},{'offset':-1},{'offset':10001},{'kind':'Other'},{'status':'all'},{'q':'x'*161},{'tag':'a|b'}]:
  assert req(api,'GET','/cards',params=p).status_code==422

@pytest.mark.parametrize('field',['sourceVerified','rightsVerified','releaseApproved'])
@pytest.mark.parametrize('value',[False,0,1,'true',None,[],{}])
def test_approval_strict(api,field,value):
 card=make(api);assert review(api,card,**{field:value}).status_code==422
 assert req(api,'GET','/audit:verify').json()=={'valid':True,'count':1}

@pytest.mark.parametrize('mutation',[
 {'title':'\ud800'}, {'title':'\x00'}, {'title':'   '},{'body':'x'*6001},{'tags':['Straße','STRASSE']},{'tags':['a|b']},{'kind':'Private'},{'extra':1},
 {'source':dict(type='Synthetic',title='x',locator='x',excerpt='x',rightsNote='x',url='https://example.org')},
 {'body':'🌊'*6000,'summary':'🌊'*600,'applicability':'🌊'*1000,'source':dict(type='Synthetic',title='🌊'*240,locator='🌊'*240,excerpt='🌊'*2000,rightsNote='🌊'*1000)},
])
def test_input_rejection(api,mutation):
 data=sample();data.update(mutation)
 r=req(api,'POST','/cards',content=json.dumps(data).encode())
 assert r.status_code==422,r.text
 assert req(api,'GET','/audit:verify').json()=={'valid':True,'count':0}

@pytest.mark.parametrize('url',['http://example.org','https://localhost','https://127.0.0.1','https://example.org:444/a','https://u:p@example.org','file:///tmp/x'])
def test_public_url_rejected(api,url):
 data=sample();data['source'].update(type='Public',url=url)
 assert req(api,'POST','/cards',json=data).status_code==422

def test_public_not_permission_and_rejection(api):
 data=sample();data['source'].update(type='Public',url='https://example.org/synthetic-example')
 r=req(api,'POST','/cards',json=data);assert r.status_code==201;card=r.json()
 assert req(api,'GET','/cards','Public').json()['total']==0
 body=decision(card);body.pop('releaseApproved')
 assert req(api,'POST','/cards/'+card['cardId']+'/review',json=body).status_code==422
 assert review(api,card,expectedDigest='0'*64).status_code==409
 assert review(api,card,unknown='x').status_code==422
 assert review(api,card,'Rejected').status_code==200
 assert review(api,card).status_code==409
 assert req(api,'GET','/cards/'+card['cardId'],'Public').status_code==404

def test_concurrency_audit_append_only_atomicity(api):
 card=make(api)
 with ThreadPoolExecutor(8) as pool:
  codes=list(pool.map(lambda _:review(api,card).status_code,range(8)))
 assert codes.count(200)==1 and codes.count(409)==7
 events=req(api,'GET','/audit').json();assert len(events)==2
 prev='0'*64
 for i,e in enumerate(events,1):
  assert e['seq']==i and e['prevHash']==prev
  prev=hashlib.sha256(json.dumps(e,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 assert req(api,'GET','/audit',params={'afterSeq':1,'limit':1,'order':'desc'}).json()==events[1:]
 engine=api[1].state.db.engine
 for sql in ['DELETE FROM knowledge_audit','UPDATE knowledge_audit SET line=\'{}\'']:
  with pytest.raises(Exception):
   with engine.begin() as conn:conn.execute(text(sql))
 # Force audit insertion failure at database boundary, not a mocked route.
 with engine.begin() as conn:conn.execute(text("CREATE TRIGGER reject_test_audit BEFORE INSERT ON knowledge_audit BEGIN SELECT RAISE(ABORT,'test fault'); END;"))
 assert req(api,'POST','/cards',json=sample()).status_code==500
 assert review(api,card,'Withdrawn').status_code==500
 assert req(api,'GET','/cards','Public').json()['total']==1
 assert req(api,'GET','/cards',params={'status':'Candidate'}).json()['total']==0
 assert req(api,'GET','/audit:verify').json()=={'valid':True,'count':2}
 with engine.begin() as conn:conn.execute(text('DROP TRIGGER reject_test_audit'))
 assert review(api,card,'Withdrawn').status_code==200
 assert req(api,'GET','/audit:verify').json()=={'valid':True,'count':3}

@pytest.mark.parametrize('constant',['NaN','Infinity','-Infinity'])
def test_nonfinite_json(api,constant):
 payload=json.dumps(sample())[:-1]+',"nonfinite":'+constant+'}'
 assert req(api,'POST','/cards',content=payload).status_code==422
 assert req(api,'GET','/audit:verify').json()['count']==0

def test_immutable_and_review_validation(api):
 card=make(api);path='/cards/'+card['cardId']
 for method in ['PUT','PATCH','DELETE']:
  assert req(api,method,path,json=sample()).status_code==405
 for changes in [{'note':''},{'note':'\x00'},{'note':'x'*2001},{'expectedDigest':'G'*64},{'decision':'Candidate'},{'unexpected':True}]:
  assert review(api,card,**changes).status_code==422
 assert req(api,'GET',path).json()==card
 assert req(api,'GET','/audit:verify').json()['count']==1
