"""W12 分析页接口（只读种子 data/w12-analysis-seed.json，由 build_seed.py 离线生成）。

运行时不调用 mcis-core、不重算 W14：演示求稳，数字与 W14.2 导出逐字一致。
种子文件在每次读取时按旁注 .sha256 自检，不一致返回 500 analysis_seed_tampered。
"""
from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from ..common.context import problem

DATA = Path(__file__).resolve().parent / "data"
SEED = DATA / "w12-analysis-seed.json"
SIDECAR = SEED.with_suffix(".sha256")

router = APIRouter(prefix="/api/v1", tags=["analysis"])

# 合同（openapi）尚未声明这两条路由，已追加到 REQUESTS.md；在架构师补齐前不进自动生成的 schema。
PENDING_CONTRACT = True
EXT = {"include_in_schema": not PENDING_CONTRACT}
EXTENSION_ROUTES = [
    ("GET", "/api/v1/analysis/cases"),
    ("GET", "/api/v1/cases/{case_id}/analysis"),
]

_lock = threading.Lock()
_cache: dict[str, Any] = {}


def load_seed(path: Path = SEED, sidecar: Path = SIDECAR) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    expected = sidecar.read_text(encoding="utf-8").split()[0] if sidecar.exists() else None
    if expected != digest:
        raise problem(500, "analysis_seed_tampered", "分析页种子与哈希旁注不一致，请重新运行 build_seed",
                      {"expected": expected, "actual": digest, "path": path.name})
    with _lock:
        if _cache.get("sha") != digest:
            _cache.update(sha=digest, doc=json.loads(raw.decode("utf-8")))
        return _cache["doc"], digest


def _meta(doc: dict[str, Any], sha: str) -> dict[str, Any]:
    return {"seedSha256": sha, "seedVerified": True, "generatedAt": doc["generatedAt"], "generator": doc["generator"],
            "coreVersion": doc["coreVersion"], "coreDll": doc["coreDll"], "w14Export": doc["w14Export"],
            "w14Frozen": doc["w14Frozen"], "crossCheck": doc["crossCheck"], "disclaimer": doc["disclaimer"]}


@router.get("/analysis/cases", **EXT)
def list_analysis_cases() -> dict[str, Any]:
    doc, sha = load_seed()
    return {"cases": [{"caseId": c["caseId"], "key": c["key"], "title": c["title"], "isFictionalDemo": c["isFictionalDemo"],
                       "sourceLabel": c["sourceLabel"], "hasWhatIf": c["whatif"] is not None} for c in doc["cases"]],
            **_meta(doc, sha)}


@router.get("/cases/{case_id}/analysis", **EXT)
def get_analysis(case_id: str) -> dict[str, Any]:
    doc, sha = load_seed()
    for c in doc["cases"]:
        if c["caseId"] == case_id or c["key"] == case_id:
            return {**c, "meta": _meta(doc, sha)}
    raise problem(404, "analysis_case_not_found", f"分析页没有该案例：{case_id}",
                  {"available": [c["caseId"] for c in doc["cases"]]})
