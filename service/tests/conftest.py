import os
import shutil
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from mcis_service.config import PROJECT_ROOT, Settings
from mcis_service.main import create_app

CASE = "CASE-2026-DEMO-LILY-MARY"
C = f"/api/v1/cases/{CASE}"
CORE = PROJECT_ROOT / "tools" / "mcis-core" / "mcis-core.sh"
HAS_DOTNET = Path(os.environ.get("MCIS_DOTNET", str(Path.home() / ".dotnet" / "dotnet"))).is_file() and CORE.exists()


def make_settings(tmp: Path, seed: bool = True) -> Settings:
    st = Settings()
    st.data_dir = tmp
    st.db_url = f"sqlite:///{tmp / 'test.db'}"
    st.seed_demo = seed
    return st


@pytest.fixture()
def app(tmp_path):
    return create_app(make_settings(tmp_path))


@pytest.fixture()
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def empty_client(tmp_path_factory):
    d = tmp_path_factory.mktemp("empty")
    with TestClient(create_app(make_settings(d, seed=False))) as c:
        yield c


def H(role="Investigator", operator=None):
    h = {"X-MCIS-Role": role}
    if operator:
        h["X-MCIS-Operator"] = quote(operator)
    return h
