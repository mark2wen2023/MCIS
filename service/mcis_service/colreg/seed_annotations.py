"""种子版本的时间带证据链接（W6.1 裁定 6）。

colreg.schema.json 的 band 不允许 evidenceIds（additionalProperties=false，合同变更已写 REQUESTS.md），
因此时间带证据放在版本注解（runs.annotations.bands）里，不进 GET /colreg 的主文档。
"""
from __future__ import annotations

from ..common.demo_case_ids import HAILI5_CASE_ID as HAILI5_CASE

LILY_MARY_CASE = "CASE-2026-DEMO-LILY-MARY"

# 虚构 Lily/Mary：EV-001 Mary VDR、EV-002 Lily S-VDR、EV-003 VTS AIS、EV-005 车钟/舵角记录
LILY_MARY_# Materialize real dicts only when the public mapping is explicitly requested.
from ..common.lazy_exports import LazyExports


def _load_haili5_mapping():
    from .haili5_seed import BAND_EVIDENCE
    return BAND_EVIDENCE


def _load_all_mappings():
    return {
        LILY_MARY_CASE: LILY_MARY_BAND_EVIDENCE,
        HAILI5_CASE: _exports.get("HAILI5_BAND_EVIDENCE"),
    }


_exports = LazyExports(globals(), {
    "HAILI5_BAND_EVIDENCE": _load_haili5_mapping,
    "BAND_EVIDENCE": _load_all_mappings,
})
__all__ = ["HAILI5_CASE", "LILY_MARY_CASE", "LILY_MARY_BAND_EVIDENCE",
           "HAILI5_BAND_EVIDENCE", "BAND_EVIDENCE", "seed_band_evidence"]


def __getattr__(name):
    return _exports.get(name)


def __dir__():
    return sorted(set(globals()) | set(__all__))


def seed_band_evidence(case_id: str) -> dict[str, list[str]]:
    source = _exports.get("BAND_EVIDENCE").get(case_id, {})
    return {k: list(v) for k, v in source.items()}
