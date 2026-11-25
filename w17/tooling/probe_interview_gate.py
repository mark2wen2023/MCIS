from tests.conftest import C,H
import tempfile;from pathlib import Path
from fastapi.testclient import TestClient
from mcis_service.main import create_app
from mcis_service.config import Settings
with tempfile.TemporaryDirectory() as t:
  app=create_app(Settings(data_dir=Path(t),seed_demo=True))
  with TestClient(app) as c:
    for p in ['/interviews','/interviews/IR-03','/interviews/IR-03/crosscheck']:
      r=c.get(C+p,headers=H());print(p,r.status_code,r.text[:220])
