"""Run unchanged workbench assertions with synthetic-only app, excluding real report seeds."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'service'))
from tests.test_access_workbench import *
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.seed.lily_mary import seed
import pytest
@pytest.fixture
def app(tmp_path):
 app=create_app(Settings(data_dir=tmp_path,seed_demo=False))
 with app.state.db.session() as s:seed(s,app.state.settings.blob_dir)
 return app
