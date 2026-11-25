"""W9.1 create validation; does not tighten legacy reads/imports."""
import math
import re
from typing import Any

from ..common import contracts
from ..common.context import problem

NUMBERS = {"loaM": False, "beamM": False, "draftForeM": True,
           "draftAftM": True, "displacementTons": False}


def validate_create(body: dict[str, Any], case: dict[str, Any]) -> None:
    contracts.validate("vessel", body)
    if body["caseId"] != case["caseId"]:
        raise problem(422, "CASE_MISMATCH", "船舶所属案件与请求不一致")
    for key in ("vesselId", "name"):
        if not body[key].strip() or body[key] != body[key].strip():
            raise problem(422, "CONTRACT_VIOLATION", f"{key} 不可为空或包含首尾空白")
    for key, pattern in (("mmsi", r"[0-9]{9}"), ("colorHex", r"#[0-9a-fA-F]{6}")):
        if key in body and not re.fullmatch(pattern, body[key]):
            raise problem(422, "CONTRACT_VIOLATION", f"{key} 格式无效")
    for key, zero_allowed in NUMBERS.items():
        if key in body:
            value = body[key]
            try:
                valid = math.isfinite(value) and (value >= 0 if zero_allowed else value > 0)
            except (OverflowError, TypeError):
                valid = False
            if not valid:
                raise problem(422, "CONTRACT_VIOLATION", f"{key} 必须是有效的有限{'非负' if zero_allowed else '正'}数")
    sources = body.get("parameterSources", {})
    for key, source in sources.items():
        if key not in body or not source["sourceLabel"].strip():
            raise problem(422, "CONTRACT_VIOLATION", "来源必须对应已填写参数且不可为空")
    if not case.get("isFictionalDemo", False):
        missing = set(body) - {"vesselId", "caseId", "colorHex", "parameterSources"} - sources.keys()
        if missing:
            raise problem(422, "CONTRACT_VIOLATION", "非虚构案件的每项参数必须填写来源与口径", sorted(missing))
