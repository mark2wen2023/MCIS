"""Actual main routes, isolated SQLite and synthetic opaque bytes, not live auth."""
import base64
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.evidence.models import EvidenceRow,CustodyEventRow
from mcis_service.audit.models import AuditEventRow
from mcis_service.recommendations.models import RecommendationRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy

CASE='RECOVERY-LAB';URL=f'/api/v1/cases/{CASE}/recommendations'
@pytest.fixture
def env(tmp_path):
    st=Settings();st.data_dir=tmp_path;st.db_url=f'sqlite:///{tmp_path}/test.db';st.seed_demo=False
    app=create_app(st)
    doc={'caseId':CASE,'schemaVersion':'1.0.0','title':'synthetic','isFictionalDemo':True,'caseEpochUtc':'2026-01-01T00:00:00Z','incidentTimeUtc':'2026-01-01T00:00:00Z','incidentLocation':{'lonDeg':121,'latDeg':31},'displayTimeZoneOffsetMinutes':0}
    with app.state.db.session() as s:put_doc(s,CaseRow,CASE,CASE,doc)
    with TestClient(app,headers={'X-MCIS-Role':'LeadInvestigator'}) as c:
        yield c,app

BODY={'title':'Synthetic recommendation','addressee':'Synthetic party','causeNodeIds':['TEST'],'dueUtc':'2099-01-01T00:00:00Z'}
def test_identical_create_after_ignored_success_duplicates(env):
    c,a=env
    first=c.post(URL,json=BODY); assert first.status_code==201,first.text
    second=c.post(URL,json=BODY); assert second.status_code==201,second.text
    assert first.json()['id']!=second.json()['id']
    with a.state.db.session() as s: assert s.query(RecommendationRow).count()==2

def test_identical_response_after_ignored_success_duplicates(env):
    c,a=env
    r=c.post(URL,json=BODY); assert r.status_code==201,r.text
    u=URL+'/'+r.json()['id']
    assert c.post(u+':transition',json={'to':'Issued'}).status_code==200
    body={'party':'Synthetic party','text':'Same written reply'}
    assert c.post(u+'/responses',json=body).status_code==201
    retry=c.post(u+'/responses',json=body); assert retry.status_code==201,retry.text
    responses=retry.json()['responses']; assert len(responses)==2
    assert all(x['party']==body['party'] and x['text']==body['text'] for x in responses)

def test_transition_retry_refusal_does_not_mean_first_failed(env):
    c,a=env
    r=c.post(URL,json=BODY);u=URL+'/'+r.json()['id']
    assert c.post(u+':transition',json={'to':'Issued'}).status_code==200
    assert c.post(u+':transition',json={'to':'Issued'}).status_code==409
    assert c.get(u).json()['status']=='Issued'
