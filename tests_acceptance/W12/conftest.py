"""W12 验收夹具：独立临时数据目录，自动播种虚构 Lily/Mary 与海力5；不碰 service/data 与 8765。
mcis-core 通过本目录 mcis-core-norebuild.sh 直接运行已构建 dll，不触发重编。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "service"))

os.environ["MCIS_CORE"] = str(Path(__file__).resolve().parent / "mcis-core-norebuild.sh")

from fastapi.testclient import TestClient  # noqa: E402

from mcis_service.config import Settings  # noqa: E402
from mcis_service.main import create_app  # noqa: E402

LILY = "CASE-2026-DEMO-LILY-MARY"
HAILI = "CASE-2025-HAILI5-WANA17"
YANGZE = "CJK-2024-1230-YangZe22-VegaDream"
CASE_IDS = [LILY, HAILI, YANGZE]
# EvidenceItem.CaseIdPattern（unity Domain）：至少 3 位，字母数字与 . _ -
CASE_ID_RE = r"\A[A-Za-z0-9._-]{3,}\Z"  # Python \Z 等价于 C# EvidenceItem.CaseIdPattern 的 \z
HAS_CORE = (Path.home() / ".dotnet" / "dotnet").exists() and (ROOT / "tools/mcis-core/out/mcis-core.dll").exists()
CORE_CMD = os.environ["MCIS_CORE"]
NM = 1852.0


def H(role: str = "Investigator") -> dict[str, str]:
    return {"X-MCIS-Role": role}


@pytest.fixture()
def client(tmp_path):
    st = Settings()
    st.data_dir = tmp_path
    st.db_url = f"sqlite:///{tmp_path / 'w12.db'}"
    st.seed_demo = True
    st.core_cmd = CORE_CMD
    with TestClient(create_app(st)) as c:
        yield c


def get_analysis(client, cid: str) -> dict:
    r = client.get(f"/api/v1/cases/{cid}/analysis", headers=H())
    assert r.status_code == 200, r.text
    return r.json()
