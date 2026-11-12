"""Partial source statements, deliberately NOT EnvironmentState simulation inputs."""
import math
import re
from datetime import datetime
from typing import Any

from ..common import contracts
from ..common.context import problem

NUMERIC_FIELDS = ("windSpeedMps", "windFromDirDeg", "currentSpeedKn", "currentToDirDeg", "visibilityNm")


def validate_observation(body: Any, case_id: str) -> None:
    contracts.validate("environment-observation", body)
    if body["caseId"] != case_id:
        raise problem(422, "CASE_MISMATCH", "环境记录所属案件与请求不一致")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", body["observationId"]):
        raise problem(422, "CONTRACT_VIOLATION", "观测编号格式无效")
    for key in ("caseId", "description", "sourceLabel", "locationDescription"):
        if body.get(key) is not None and not body[key].strip():
            raise problem(422, "CONTRACT_VIOLATION", f"{key} 不可只有空白；未知地点请使用 null")
    stamp = body["observedAtUtc"]
    if stamp is not None:
        try:
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", stamp):
                raise ValueError()
            datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            raise problem(422, "CONTRACT_VIOLATION", "观测时刻须为真实 UTC 日期时间（秒精度，Z 结尾）")
    for key in NUMERIC_FIELDS:
        value = body.get(key)
        if value is None:
            continue
        try:
            valid = math.isfinite(value) and value >= 0
        except (TypeError, OverflowError):
            valid = False
        if not valid:
            raise problem(422, "CONTRACT_VIOLATION", f"{key} 必须是有限非负数，未知请留空")


def validate_observations(items: Any, case_id: str) -> None:
    if not isinstance(items, list):
        raise problem(422, "BAD_PACKAGE", "环境记录必须是数组")
    seen = set()
    for item in items:
        validate_observation(item, case_id)
        if item["observationId"] in seen:
            raise problem(422, "BAD_PACKAGE", "环境记录编号重复，不允许覆盖")
        seen.add(item["observationId"])
