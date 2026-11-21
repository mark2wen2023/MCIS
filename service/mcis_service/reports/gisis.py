"""GISIS 本地准备字段：显式来源、缺值、临时校验和可追溯导出，不写案件。"""
from __future__ import annotations

import copy
import csv
import io
import json
import math
import re
from datetime import datetime

from .templates import DISCLAIMER_EN, DISCLAIMER_ZH, GISIS_FIELDS

_SEVERITY = {"VerySerious": "Very serious marine casualty", "Very serious": "Very serious marine casualty",
             "MarineIncident": "Marine incident", "Marine incident": "Marine incident"}
_MISSING = "缺数据 / Missing data"


def _get_path(data, path):
    value = data
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _materialize(definition, value, *, vessel_id=None):
    field = {k: copy.deepcopy(v) for k, v in definition.items() if k != "scope"}
    if vessel_id is not None:
        field["id"] = f"vessels.{vessel_id}.{field['id']}"
        field["sourceRefs"] = [ref.replace("vessels[]", f"vessels.{vessel_id}") for ref in field["sourceRefs"]]
    # 空白不代表已有数据；数字0与布尔false都必须保留。
    missing = value is None or (isinstance(value, str) and not value.strip())
    field.update(value=None if missing else value, missing=missing, missingLabel=_MISSING if missing else None, vesselId=vessel_id)
    return field


def build_gisis(case: dict, vessels: list) -> dict:
    fields = []
    for definition in GISIS_FIELDS:
        if definition["scope"] == "vessel":
            # 没有船舶资料也给出缺项，避免看起来已经满足必填校验。
            for vessel in vessels or [{"vesselId": "missing-vessel"}]:
                key = definition["id"]
                source_key = "vesselTypeCode" if key == "vesselType" else key
                value = vessel.get(source_key)
                if key == "imoNumber" and isinstance(value, str):
                    value = re.sub(r"^IMO\s*", "", value.strip(), flags=re.I)
                fields.append(_materialize(definition, value, vessel_id=vessel.get("vesselId") or "missing-vessel"))
            continue
        source = definition["sourceRefs"][0].removeprefix("case.")
        if definition["id"] == "numberOfShips":
            value = len(vessels) if vessels else None
        else:
            value = _get_path(case, source)
        if definition["id"] == "severity":
            value = _SEVERITY.get(value) if isinstance(value, str) else None
        fields.append(_materialize(definition, value))
    from .service import data_status, is_fictional
    fictional = is_fictional(case)
    return {"caseId": case["caseId"], "isFictionalDemo": fictional,
            "realDataStatus": data_status(case), "fields": fields,
            "notice": f"GISIS 本地准备字段，未向 IMO 提交；{'虚构示例 / Fictional；' if fictional else ''}{DISCLAIMER_ZH} / {DISCLAIMER_EN}"}


def _valid_type(value, expected):
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        # Integers are finite without a lossy/overflowing float conversion.
        return (isinstance(value, int) and not isinstance(value, bool)) or (isinstance(value, float) and math.isfinite(value))
    if expected == "string":
        return isinstance(value, str)
    return True


def _invalid(value, rules):
    if not _valid_type(value, rules.get("type")):
        return "field_type", "字段类型不符 / Invalid field type"
    if "enum" in rules and value not in rules["enum"]:
        return "field_enum", "不在允许值中 / Value is not in the allowed list"
    if "minimum" in rules and value < rules["minimum"]:
        return "field_range", "低于最小值 / Value below minimum"
    if "maximum" in rules and value > rules["maximum"]:
        return "field_range", "超过最大值 / Value above maximum"
    if "minLength" in rules and len(value.strip()) < rules["minLength"]:
        return "field_length", "文本不能为空 / Text is required"
    if "pattern" in rules and re.fullmatch(rules["pattern"], value) is None:
        return "field_pattern", "格式不符 / Invalid format"
    if rules.get("checksum") == "imo":
        if len(value) != 7 or not value.isascii() or not value.isdigit() or sum(int(d) * (7 - i) for i, d in enumerate(value[:6])) % 10 != int(value[-1]):
            return "field_checksum", "IMO 号校验位不符（虚构号码也会校验） / Invalid IMO check digit"
    if rules.get("format") == "utc":
        try:
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z", value):
                raise ValueError("UTC 后缀必须为 Z")
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return "field_utc", "必须为有效 UTC ISO 时间（Z） / Valid UTC timestamp ending in Z required"
    return None


def validate_gisis(doc: dict, values: dict | None = None) -> dict:
    fields = copy.deepcopy(doc["fields"])
    by_id = {field["id"]: field for field in fields}
    errors = []
    for key, value in (values or {}).items():
        if key not in by_id:
            errors.append({"fieldId": key, "code": "field_unknown", "message": "未知字段 / Unknown field"})
            continue
        field = by_id[key]
        missing = value is None or (isinstance(value, str) and not value.strip())
        field.update(value=None if missing else value, missing=missing, missingLabel=_MISSING if missing else None)
        # 覆盖值只是本次人工输入，不能继续声称来自原案件字段；保留原路径供核查。
        original_sources = "; ".join(field["sourceRefs"])
        field["sourceRefs"] = [f"request.values.{key} (Investigator temporary input; original sources: {original_sources})"]
    for field in fields:
        if field["missing"]:
            if field["required"]:
                errors.append({"fieldId": field["id"], "code": "field_required", "message": _MISSING})
            continue
        issue = _invalid(field["value"], field["rules"])
        if issue:
            errors.append({"fieldId": field["id"], "code": issue[0], "message": issue[1]})
    return {"valid": not errors, "errors": errors, "fields": fields}


def serialize_gisis(doc: dict, format: str) -> bytes:
    if format == "json":
        return json.dumps(doc, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
    if format != "csv":
        raise ValueError("GISIS format must be json or csv")
    output = io.StringIO(newline="")
    keys = ["caseId", "isFictionalDemo", "notice", "id", "labelZh", "labelEn", "vesselId", "required", "value", "missing", "missingLabel", "sourceRefs", "gisisRef", "mappingStatus", "mappingNote", "rules"]
    writer = csv.DictWriter(output, fieldnames=keys)
    writer.writeheader()
    for field in doc["fields"]:
        row = {**field, "caseId": doc["caseId"], "isFictionalDemo": json.dumps(doc["isFictionalDemo"]), "notice": doc["notice"]}
        # 显式字符串 null 保留“未知”含义，不能让空格、0或false冒充缺值。
        for key in ("value", "missing", "required", "sourceRefs", "rules"):
            row[key] = json.dumps(row[key], ensure_ascii=False, allow_nan=False)
        writer.writerow(row)
    return output.getvalue().encode("utf-8-sig")
