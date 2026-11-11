"""Controlled-time TestClient checks, NOT real HTTP/browser clock validation.
Each test creates a fresh disposable DB and patches only the consultation module's
now_utc provider. No OS/production clock or stored deadline is modified.
"""
from datetime import datetime, timedelta
from importlib import import_module
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'service'))
from mcis_service.config import Settings
from mcis_service.main import create_app
router = import_module('mcis_service.recommendations.router')
C='/api/v1/cases/CASE-2026-DEMO-LILY-MARY'
H={'X-MCIS-Role':'Investigator'}

@pytest.mark.parametrize('offset_us,expected',[(-1,409),(0,200),(1,200)])
def test_exact_deadline_close_boundary(tmp_path,monkeypatch,offset_us,expected):
    settings=Settings(data_dir=tmp_path,db_url=f'sqlite:///{tmp_path}/case.db',seed_demo=True)
    with TestClient(create_app(settings)) as client:
        rounds=client.get(C+'/consultation/rounds',headers=H).json()
        rnd=next(r for r in rounds if r['roundNo']==2)
        assert not rnd['allReplied'] and not rnd['isClosed']
        deadline=datetime.fromisoformat(rnd['deadlineUtc'])
        controlled=deadline+timedelta(microseconds=offset_us)
        monkeypatch.setattr(router,'now_utc',lambda:controlled)
        before=client.get(C+'/audit?category=Consultation',headers=H).json()
        result=client.post(C+'/consultation/rounds/2:close',json={},headers=H)
        assert result.status_code==expected
        after=client.get(C+'/audit?category=Consultation',headers=H).json()
        if expected==409:
            assert result.json()['code']=='consultation_cannot_close'
            assert after==before
        else:
            assert result.json()['isClosed'] and not result.json()['allReplied']
            assert len(after)==len(before)+1 and after[-1]['action']=='consultation.close'
        persisted=next(r for r in client.get(C+'/consultation/rounds',headers=H).json() if r['roundNo']==2)
        assert persisted['isClosed']==(expected==200)
        assert client.get(C+'/audit:verify',headers=H).json()['valid']
