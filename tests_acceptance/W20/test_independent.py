"""Independent W20 acceptance. All inference is fake; no real model evaluated."""
import copy
import json
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'service'))
from fastapi.testclient import TestClient
from mcis_service.config import Settings
from mcis_service.main import create_app
from mcis_service.agents import model_client, extraction
from mcis_service.redaction.policy import default_policy

C='/api/v1/cases/CASE-2026-DEMO-LILY-MARY'
H={'X-MCIS-Role':'Investigator'}
PATH=C+'/agents/people_ops/interviews/IR-91:extract'
ITEM={'kind':'Operation','subject':'vessel.operation','summary':'虚构测试陈述','claim':{'valueType':'Occurrence','occurred':True},'round':1,'field':'Answer','quote':'右满舵'}

def record(answer='😀右满舵，保持瞭望。', fragments=None):
    return {'recordId':'IR-91','interviewee':{'intervieweeId':'P91','name':'测试甲','role':'船员','affiliation':'虚构'},'startUtc':'2026-11-12T00:00:00Z','turns':[{'round':1,'question':'采取何操作？','answer':answer,'sensitiveFragments':fragments or []}],'statements':[]}

@pytest.fixture
def client(tmp_path,monkeypatch):
    st=Settings();st.data_dir=tmp_path;st.db_url=f'sqlite:///{tmp_path}/test.db';st.seed_demo=True
    monkeypatch.setenv('MCIS_AGENT_BASE_URL','http://127.0.0.1:12345/v1');monkeypatch.setenv('MCIS_AGENT_MODEL','independent-fake-not-real-inference')
    monkeypatch.setattr(model_client,'complete',lambda *_:json.dumps({'statements':[ITEM]}))
    with TestClient(create_app(st),raise_server_exceptions=False) as c:
        assert c.post(C+'/interviews',headers=H,json=record()).status_code==201
        yield c

def draft(c):
    r=c.post(PATH,headers=H);assert r.status_code==201,r.text;return r.json()

def review(c,d,decision='Confirmed',payload=None):
    body={'decision':decision}
    if payload is not None:body['payload']=payload
    return c.post(C+'/agents/drafts/'+d['draftId']+'/review',headers=H,json=body)

def current(c):return c.get(C+'/interviews/IR-91',headers=H).json()


def test_concurrent_review_exactly_once(client):
    d=draft(client)
    assert current(client)['statements']==[]
    with ThreadPoolExecutor(2) as pool:statuses=list(pool.map(lambda _: review(client,d).status_code,range(2)))
    assert sorted(statuses)==[200,409]
    sts=current(client)['statements'];assert len(sts)==1
    assert sts[0]['span']=={'round':1,'field':'Answer','start':2,'length':3}
    assert sts[0]['revision']==1 and sts[0]['extractedBy']=='Agent'


def test_source_changes_during_inference(client,monkeypatch):
    def complete(*_):
        assert client.post(C+'/interviews/IR-91/turns',headers=H,json={'question':'补充','answer':'虚构'}).status_code==201
        return json.dumps({'statements':[ITEM]})
    monkeypatch.setattr(model_client,'complete',complete)
    r=client.post(PATH,headers=H)
    assert r.status_code==409 and r.json()['code']=='SOURCE_CHANGED'
    assert current(client)['statements']==[]
    assert not any(d.get('targetEntityId')=='IR-91' for d in client.get(C+'/agents/drafts',headers=H).json())

@pytest.mark.parametrize('change',[{'field':'Question'},{'round':2},{'quote':'右满舵不存在'},{'quote':'[已遮盖]'}])
def test_citation_atomic_rejection(client,monkeypatch,change):
    monkeypatch.setattr(model_client,'complete',lambda *_:json.dumps({'statements':[ITEM,{**ITEM,**change}]}))
    r=client.post(PATH,headers=H);assert r.status_code in (422,502)
    assert current(client)['statements']==[]


def test_access_revoked_before_confirmation(client):
    d=draft(client);p=default_policy();p['matrix']['AgentService']['testimony']='Deny'
    assert client.put(C+'/access-policy',headers={'X-MCIS-Role':'LeadInvestigator'},json=p).status_code==200
    assert review(client,d).status_code==403
    assert current(client)['statements']==[]


def test_known_defect_overlapping_quote_must_be_rejected():
    rec=record('aaaa');item={**ITEM,'quote':'aaa'}
    p=extraction.parse_output(json.dumps({'statements':[item]}),rec)
    with pytest.raises(Exception):extraction.checked_statements(p,rec,default_policy())


def test_known_defect_sensitive_fragment_overlapping_name_must_not_leave_private_text():
    rec=record('测试甲患有虚构病症。随后右满舵。',['测试甲患有虚构病症'])
    assert '虚构病症' not in json.dumps(extraction.redacted_input(rec,default_policy()),ensure_ascii=False)

@pytest.mark.parametrize('invalid',['Infinity','"\\ud800"'])
def test_known_defect_modified_invalid_json_rejected_atomically(client,invalid):
    d=draft(client);p=copy.deepcopy(d['payload'])
    if invalid=='Infinity':p['statements'][0]['claim']={'valueType':'Scalar','scalar':float('inf')}
    else:p['statements'][0]['summary']='\ud800'
    r=client.post(C+'/agents/drafts/'+d['draftId']+'/review',headers={**H,'Content-Type':'application/json'},content=json.dumps({'decision':'Modified','payload':p}))
    assert r.status_code==422,r.text
    assert current(client)['statements']==[]
    assert next(x for x in client.get(C+'/agents/drafts',headers=H).json() if x['draftId']==d['draftId'])['status']=='PendingReview'

@pytest.mark.parametrize('fragments',[['甲乙','乙丙'],['乙丙','甲乙']])
def test_sensitive_fragment_union_of_overlapping_ranges(fragments):
    rec=record('甲乙丙随后右满舵。',fragments)
    sent=json.dumps(extraction.redacted_input(rec,default_policy()),ensure_ascii=False)
    for private in '甲乙丙':assert private not in sent

@pytest.mark.parametrize('url',['http://localhost:99/v1','http://127.0.0.1.example:99/v1','http://0.0.0.0:99/v1','https://127.0.0.1:99/v1','http://[::ffff:127.0.0.1]:99/v1','http://x:y@127.0.0.1:99/v1','http://127.0.0.1:99/v1?key=secret'])
def test_nonliteral_or_unsafe_configuration_never_enabled(monkeypatch,url):
    monkeypatch.setenv('MCIS_AGENT_BASE_URL',url);monkeypatch.setenv('MCIS_AGENT_MODEL','fake')
    with pytest.raises(Exception):model_client.config()


def test_preserve_existing_statements_on_append(client):
    old=client.post(C+'/interviews/IR-91/statements',headers=H,json={'kind':'Operation','subject':'vessel.operation','summary':'既有虚构陈述','claim':{'valueType':'Occurrence','occurred':True},'span':{'round':1,'field':'Answer','start':2,'length':3}})
    assert old.status_code==201
    before=current(client)
    d=draft(client);assert review(client,d).status_code==200
    after=current(client)
    assert after['statements'][0]==before['statements'][0]
    assert after['crossChecks']==before['crossChecks']
    assert after['statements'][1]['statementId']!=before['statements'][0]['statementId']


def test_bad_second_item_never_persists_first(client,monkeypatch):
    monkeypatch.setattr(model_client,'complete',lambda *_:json.dumps({'statements':[ITEM,{**ITEM,'summary':'bad','extra':'unallowed'}]}))
    r=client.post(PATH,headers=H);assert r.status_code==502
    assert not any(d.get('targetEntityId')=='IR-91' for d in client.get(C+'/agents/drafts',headers=H).json())


def test_audit_records_success_failure_without_raw_payload(client,monkeypatch):
    d=draft(client)
    assert review(client,d).status_code==200
    monkeypatch.setattr(model_client,'complete',lambda *_:'private-raw-response-not-json')
    assert client.post(PATH,headers=H).status_code==502
    events=client.get(C+'/audit',headers=H,params={'category':'Agent'}).json()
    if isinstance(events,dict):events=events.get('items',events.get('events',[]))
    actions=[e['action'] for e in events]
    for name in ['agent.run.started','agent.draft','agent.run.failed','agent.review']:assert name in actions
    raw=json.dumps(events,ensure_ascii=False)
    assert 'private-raw-response-not-json' not in raw
    assert '😀右满舵，保持瞭望。' not in raw
    assert client.get(C+'/audit:verify',headers=H).json()['valid'] is True
