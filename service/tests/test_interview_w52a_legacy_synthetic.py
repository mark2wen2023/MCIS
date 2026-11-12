"""Reuse W5 business assertions on explicitly UNSIGNED synthetic fixture copies.
Production Lily/Mary signed seed remains untouched and read-only under W5.2a.
No global role change: only selected legacy test module helpers use qualified Lead.
"""
import pytest
from sqlalchemy import select
from mcis_service.main import create_app
from mcis_service.seed.lily_mary import seed
from mcis_service.interviews.models import InterviewRow
from .conftest import make_settings,H as original_H
from . import test_interview_compare_w5 as legacy

@pytest.fixture
def app(tmp_path):
    app=create_app(make_settings(tmp_path,seed=False))
    with app.state.db.session() as s:
        seed(s,app.state.settings.blob_dir)
        for row in s.scalars(select(InterviewRow)):
            d=dict(row.doc);d['signed']=False;row.doc=d
    return app

@pytest.fixture(autouse=True)
def qualified_helpers(monkeypatch):
    h=original_H('LeadInvestigator','调查员 A')
    monkeypatch.setattr(legacy,'INV',h)
    monkeypatch.setattr(legacy._page,'__defaults__',('IR-03',h))
    def H(role='LeadInvestigator',operator=None): return original_H(role,operator)
    monkeypatch.setattr(legacy,'H',H)

# External redacted-view tests intentionally incompatible: original access now
# denied, explicitly verified in the dedicated security suite, not silently passed.
for name in dir(legacy):
    if name.startswith('test_') and name!='test_external_roles_get_redacted_page_and_cannot_write':
        globals()[name]=getattr(legacy,name)
