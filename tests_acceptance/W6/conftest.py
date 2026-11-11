"""W6 验收夹具：每个用例独立临时数据目录（自动播种虚构 Lily/Mary 与海力5），不碰 service/data 与 8765。"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import quote

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "service"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
# 直接运行已构建的 mcis-core.dll，不触发重编
os.environ["MCIS_CORE"] = str(Path(__file__).resolve().parent / "mcis-core-norebuild.sh")

from fastapi.testclient import TestClient  # noqa: E402

from mcis_service.config import Settings  # noqa: E402
from mcis_service.main import create_app  # noqa: E402

LILY = "CASE-2026-DEMO-LILY-MARY"
HAILI = "CASE-2025-HAILI5-WANA17"
HAS_CORE = (Path.home() / ".dotnet" / "dotnet").exists() and (ROOT / "tools/mcis-core/out/mcis-core.dll").exists()


def H(role: str = "Investigator", operator: str | None = None) -> dict[str, str]:
    h = {"X-MCIS-Role": role}
    if operator:
        h["X-MCIS-Operator"] = quote(operator)
    return h


@pytest.fixture()
def client(tmp_path):
    st = Settings()
    st.data_dir = tmp_path
    st.db_url = f"sqlite:///{tmp_path / 'w6.db'}"
    st.seed_demo = True
    st.core_cmd = os.environ["MCIS_CORE"]
    with TestClient(create_app(st)) as c:
        yield c
