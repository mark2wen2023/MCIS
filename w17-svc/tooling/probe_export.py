from tests.conftest import C,H
import tempfile;from pathlib import Path
from fastapi.testclient import TestClient
from mcis_service.main import create_app
from mcis_service.config import Settings
with tempfile.TemporaryDirectory() as t:
  app=create_app(Settings(data_dir=Path(t),seed_demo=True))
  with TestClient(app) as c:
    r=c.get(C+'/export',headers=H('LeadInvestigator'));print('export',r.status_code,r.headers.get('content-type'),r.text[:300])
