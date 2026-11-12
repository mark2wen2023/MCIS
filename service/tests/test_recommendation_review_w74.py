"""Read endpoints only; synthetic Lily/Mary fixture; no real report or outbound calls."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.seed.lily_mary import seed,CASE_ID
from mcis_service.audit import service as audit
from mcis_service.recommendations.models import RecommendationRow
B=f'/api/v1/cases/{CASE_ID}'
@pytest.fixture
def c(tmp_path):
 app=create_app(Settings(data_dir=tmp_path,seed_demo=False))
 with app.state.db.session() as s:seed(s,app.state.settings.blob_dir)
 with TestClient(app) as client:yield client

def test_read_preserves_documents_and_audit(c):
 h={'X-MCIS-Role':'LeadInvestigator'}
 def snapshot():
  with c.app.state.db.session() as s:
   return [x.doc for x in s.scalars(select(RecommendationRow))],audit.all_lines(s,CASE_ID)
 before=snapshot()
 for _ in range(2):
  r=c.get(B+'/recommendations/SR-2026-03',headers=h);assert r.status_code==200
  assert r.json()['caseId']==CASE_ID and 'body' in r.json() and 'responses' in r.json()
  assert 'no-store' in r.headers['cache-control']
  a=c.get(B+'/recommendations/SR-2026-03/history',headers=h);assert a.status_code==200
  assert all(e['caseId']==CASE_ID and e['entityId']=='SR-2026-03' for e in a.json())
  assert 'no-store' in a.headers['cache-control']
 assert snapshot()==before

@pytest.mark.parametrize('role',['Public','ExternalExpert','InterestedState'])
def test_actual_default_policy(c,role):
 h={'X-MCIS-Role':role}
 r=c.get(B+'/recommendations/SR-2026-03',headers=h)
 # W7ACCESS is the real server boundary, not the UI's role condition.
 assert r.status_code==403
 assert c.get(B+'/recommendations/SR-2026-03/history',headers=h).status_code==403

def test_missing_recommendation_does_not_fallback(c):
 h={'X-MCIS-Role':'LeadInvestigator'}
 assert c.get(B+'/recommendations/SR-2026-99',headers=h).status_code==404
 assert c.get('/api/v1/cases/OTHER/recommendations/SR-2026-03',headers=h).status_code==404


def test_server_denial_overrides_internal_ui_role(c):
 from mcis_service.redaction.models import AccessPolicyRow
 from mcis_service.redaction.policy import default_policy
 from mcis_service.db import put_doc
 policy=default_policy();policy['matrix']['Investigator']['recommendations']='Deny'
 with c.app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE_ID,'policy',policy)
 r=c.get(B+'/recommendations/SR-2026-03',headers={'X-MCIS-Role':'Investigator'})
 assert r.status_code==403 and 'body' not in r.json()
