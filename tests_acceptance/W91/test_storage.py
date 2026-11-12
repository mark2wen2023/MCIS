"""Independent lifecycle/custom-policy/fault-injection acceptance."""
import sys,json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'service'))
sys.path.insert(0,str(ROOT/'tests_acceptance/W82'))
from harness import payload
from mcis_service.config import Settings
from mcis_service.main import create_app
from mcis_service.db import put_doc
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.audit import service as audit
from mcis_service.package.mcase import read_zip

@pytest.fixture()
def settings(tmp_path):
    return Settings(data_dir=tmp_path,db_url='sqlite:///'+str(tmp_path/'test.db'),seed_demo=False)

def body():return {'caseId':'W91-storage','vesselId':'one','name':'Synthetic vessel','beamM':12.5,'parameterSources':{'beamM':{'sourceLabel':'Synthetic plan page 2','kind':'Estimated'}}}

@pytest.mark.parametrize('role,level',[('Investigator','ReadOnly'),('Investigator','Redacted'),('LeadInvestigator','Deny'),('Public','ReadWrite'),('AgentService','ReadWrite')])
def test_custom_policy_and_role_both_required(settings,role,level):
    app=create_app(settings)
    with TestClient(app) as c:
        assert c.post('/api/v1/cases',json=payload('W91-storage')).status_code==201
        policy=default_policy();policy['matrix'][role]['ais_sim']=level
        with app.state.db.session() as s:put_doc(s,AccessPolicyRow,'W91-storage','policy',policy)
        headers={'X-MCIS-Role':role}
        r=c.post('/api/v1/cases/W91-storage/vessels',json=body(),headers=headers)
        assert r.status_code==403,r.text
        assert c.get('/api/v1/cases/W91-storage/overview').json()['counts']['vessels']==0
        assert not [e for e in c.get('/api/v1/cases/W91-storage/audit').json() if e['action']=='vessel.create']


def test_database_reopen_and_package_preserve_sources(settings):
    with TestClient(create_app(settings)) as c:
        assert c.post('/api/v1/cases',json=payload('W91-storage')).status_code==201
        assert c.post('/api/v1/cases/W91-storage/vessels',json=body()).status_code==201
    with TestClient(create_app(settings)) as c:
        assert c.get('/api/v1/cases/W91-storage/vessels').json()==[body()]
        archive=c.get('/api/v1/cases/W91-storage/export')
        assert archive.status_code==200
        assert json.loads(read_zip(archive.content)['vessels.json'])==[body()]
        assert c.post('/api/v1/packages:verify',content=archive.content).json()['isValid']


def test_failure_after_audit_insert_rolls_back_both(settings,monkeypatch):
    with TestClient(create_app(settings),raise_server_exceptions=False) as c:
        assert c.post('/api/v1/cases',json=payload('W91-storage')).status_code==201
        before=c.get('/api/v1/cases/W91-storage/audit').json()
        original=audit.append
        def fail(*a,**kw):
            original(*a,**kw)
            raise RuntimeError('synthetic post-insert failure')
        monkeypatch.setattr(audit,'append',fail)
        assert c.post('/api/v1/cases/W91-storage/vessels',json=body()).status_code==500
        assert c.get('/api/v1/cases/W91-storage/vessels').json()==[]
        assert c.get('/api/v1/cases/W91-storage/audit').json()==before
