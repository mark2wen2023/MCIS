"""mcis-core align 已接入后的服务层测试：/api/v1/core/align 不再返回 501。"""
from __future__ import annotations

import pytest

from .conftest import H, HAS_DOTNET

CSV_A = """# 合成
time_utc,cog_deg
2026-05-18T06:20:00Z,45.0
2026-05-18T06:21:00Z,45.0
"""

CSV_B = """# 合成
time_utc,cog_deg
2026-05-18T06:20:00Z,50.0
2026-05-18T06:21:00Z,50.0
"""


@pytest.mark.skipif(not HAS_DOTNET, reason="需要 ~/.dotnet")
def test_core_align_detects_course_conflict(client):
    """最小合成输入：两源航向差超过默认 2° 阈值，应返回 200 且冲突通过合同校验。"""
    mapping = {"timeColumn": "time_utc", "columns": [{"column": "cog_deg", "kind": "CourseOverGround"}]}
    payload = {
        "caseId": "CASE-2026-DEMO-LILY-MARY",
        "caseEpochUtc": "2026-05-18T06:00:00Z",
        "sources": [
            {"sourceId": "SRC-A", "format": "csv", "text": CSV_A, "csvMapping": mapping},
            {"sourceId": "SRC-B", "format": "csv", "text": CSV_B, "csvMapping": mapping},
        ],
    }
    r = client.post("/api/v1/core/align", json=payload, headers=H())
    assert r.status_code != 501, r.text
    assert r.status_code == 200, r.text
    env = r.json()
    assert env["ok"] is True and env["command"] == "align"
    conflicts = env["result"]["conflicts"]
    assert conflicts, env
    c = conflicts[0]
    assert c["caseId"] == "CASE-2026-DEMO-LILY-MARY"
    assert c["trackKind"] == "CourseOverGround"
    assert c["delta"] == pytest.approx(5.0)
    assert c["deltaUnit"] == "deg"
    assert c["status"] == "Open"
    ver = client.get("/api/v1/core/version", headers=H()).json()
    assert "align" in ver["result"]["commands"]


@pytest.mark.skipif(not HAS_DOTNET, reason="需要 ~/.dotnet")
def test_core_align_bad_request(client):
    r = client.post("/api/v1/core/align", json={"sources": []}, headers=H())
    assert r.status_code == 422
    body = r.json()
    assert body.get("code") == "BAD_REQUEST"
