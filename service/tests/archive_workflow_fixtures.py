"""Construct a new metadata/vessel-only case, never clear an existing case.
Explicit legacy fields preserve revision semantics across archive normalization.
"""
import pytest
from fastapi.testclient import TestClient
from mcis_service.main import create_app
from .conftest import CASE,H,make_settings

@pytest.fixture()
def supported_archive_client(tmp_path):
    app=create_app(make_settings(tmp_path,seed=False))
    with TestClient(app) as client:
        case={'schemaVersion':'1.0.0','caseId':CASE,
              'title':'Synthetic supported archive workflow','accidentType':'Collision',
              'caseEpochUtc':'2026-01-01T00:00:00Z','incidentTimeUtc':'2026-01-01T00:00:00Z',
              'incidentLocation':{'lonDeg':0.0,'latDeg':0.0,'heightM':0.0},
              'accidentCode':'','accidentGrade':'','seaLevelOffsetM':0.0,
              'leadInvestigator':'','agencyName':'','summaryNotes':'',
              'displayTimeZoneOffsetMinutes':0,'isFictionalDemo':True}
        response=client.post('/api/v1/cases',json=case,headers=H())
        assert response.status_code==201,response.text
        yield client
