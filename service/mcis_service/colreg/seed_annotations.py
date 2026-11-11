"""种子版本的时间带证据链接（W6.1 裁定 6）。

colreg.schema.json 的 band 不允许 evidenceIds（additionalProperties=false，合同变更已写 REQUESTS.md），
因此时间带证据放在版本注解（runs.annotations.bands）里，不进 GET /colreg 的主文档。
"""
from __future__ import annotations

from .haili5_seed import BAND_EVIDENCE as HAILI5_BAND_EVIDENCE, CASE_ID as HAILI5_CASE

LILY_MARY_CASE = "CASE-2026-DEMO-LILY-MARY"

# 虚构 Lily/Mary：EV-001 Mary VDR、EV-002 Lily S-VDR、EV-003 VTS AIS、EV-005 车钟/舵角记录
LILY_MARY_BAND_EVIDENCE: dict[str, list[str]] = {
    "B1": ["EV-003", "EV-001"],
    "B2": ["EV-003", "EV-001"],
    "B3": ["EV-001", "EV-002"],
    "B4": ["EV-001", "EV-002", "EV-005"],
    "B5": ["EV-001", "EV-002", "EV-003"],
}

BAND_EVIDENCE: dict[str, dict[str, list[str]]] = {
    LILY_MARY_CASE: LILY_MARY_BAND_EVIDENCE,
    HAILI5_CASE: HAILI5_BAND_EVIDENCE,
}


def seed_band_evidence(case_id: str) -> dict[str, list[str]]:
    return {k: list(v) for k, v in BAND_EVIDENCE.get(case_id, {}).items()}
