"""Existing read-only API contract, synthetic Lily/Mary only; no model execution."""
import pytest
from fastapi.testclient import TestClient
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.seed.lily_mary import seed,CASE_ID
from mcis_service.audit import service as audit
from mcis_service.agents import model_client
B=f'/api/v1/cases/{CASE_ID}'
@pytest.fixture
def c(tmp_path,monkeypatch):
 monkeypatch.delenv('MCIS_AGENT_BASE_URL',raising=False);monkeypatch.delenv('MCIS_AGENT_MODEL',raising=False)
 def forbidden(*a,**kw):raise AssertionError('overview must not call model')
 monkeypatch.setattr(model_client,'complete',forbidden)
 app=create_app(Settings(data_dir=tmp_path,seed_demo=False))
 with app.state.db.session() as s:seed(s,tmp_path/'blobs')
 with TestClient(app) as client:yield client

def test_existing_registry_and_queue_no_writes(c):
 h={'X-MCIS-Role':'LeadInvestigator'}
 with c.app.state.db.session() as s:before=audit.count(s,CASE_ID)
 a=c.get('/api/v1/agents',headers=h).json();assert len(a)==6 and all(x['status']=='not_connected' for x in a)
 r=c.get(B+'/agents/drafts',headers=h);assert r.status_code==200
 assert len(r.json())==2 and all(d['caseId']==CASE_ID and d['status']=='PendingReview' for d in r.json())
 assert 'no-store' in r.headers['cache-control']
 with c.app.state.db.session() as s:assert audit.count(s,CASE_ID)==before

@pytest.mark.parametrize('role',['Public','ExternalExpert','InterestedState','Investigator','AgentService'])
def test_actual_default_policy_denials(c,role):
 assert c.get(B+'/agents/drafts',headers={'X-MCIS-Role':role}).status_code==403

def test_configured_does_not_probe_model(c,monkeypatch):
 monkeypatch.setenv('MCIS_AGENT_BASE_URL','http://127.0.0.1:19999/v1');monkeypatch.setenv('MCIS_AGENT_MODEL','synthetic-not-a-real-model')
 rows=c.get('/api/v1/agents').json();assert sum(r['status']=='configured' for r in rows)==1
 assert next(r for r in rows if r['agent']=='people_ops')['status']=='configured'
 monkeypatch.setenv('MCIS_AGENT_BASE_URL','https://example.com/v1')
 assert next(r for r in c.get('/api/v1/agents').json() if r['agent']=='people_ops')['status']=='invalid_configuration'
