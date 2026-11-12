"""Workspace metadata only; preserve immutable accident/coordinate/fiction flags."""
import hashlib
import json
import re
from copy import deepcopy

from sqlalchemy import select

from ..audit.models import AuditEventRow
from ..cases.service import load_case
from ..common import contracts
from ..common.context import problem

ACTION = "case.metadata.update"
FIELDS = ("title", "placeName", "leadInvestigator", "agencyName", "summaryNotes")
SCHEMA = "w84-case-metadata/v1"


def rows(s, case_id):
    return s.scalars(select(AuditEventRow).where(AuditEventRow.case_id == case_id,
                     AuditEventRow.action == ACTION).order_by(AuditEventRow.seq.desc()))


def details(row):
    try:
        data = json.loads(json.loads(row.line).get("reason", "null"))
        if not isinstance(data, dict) or data.get("schema") != SCHEMA:
            return None
        if not all(isinstance(data.get(k), str) and data[k].strip() for k in ("operationId", "sourceLabel", "changeReason")):
            return None
        if not isinstance(data.get("after"), dict) or not data["after"] or set(data["after"]) - set(FIELDS):
            return None
        return data
    except (ValueError, TypeError, AttributeError):
        return None


def snapshot(s, case_id):
    case = load_case(s, case_id)
    last = rows(s, case_id).first()
    # Audit identity in the token detects A -> B -> A, unlike content-only hashes.
    serial = json.dumps([case, last.line if last else None], sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    revision = hashlib.sha256(serial.encode()).hexdigest()
    data = details(last) if last else None
    change = None if data is None else {"operationId": data["operationId"], "utc": last.utc,
             "operator": last.operator, "sourceLabel": data["sourceLabel"],
             "changeReason": data["changeReason"], "fields": list(data["after"])}
    return {"case": case, "revision": revision, "lastChange": change}


def validate_update(body):
    contracts.validate("case-metadata#/$defs/update", body)
    if not re.fullmatch(r"[0-9a-f]{64}", body["expectedRevision"]):
        raise problem(422, "CONTRACT_VIOLATION", "版本格式无效")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", body["operationId"]):
        raise problem(422, "CONTRACT_VIOLATION", "修改请求编号无效")
    for key in ("sourceLabel", "changeReason"):
        if not body[key].strip():
            raise problem(422, "CONTRACT_VIOLATION", "来源和变更理由不可只有空白")
    for key, value in body["changes"].items():
        if value is not None and not value.strip():
            raise problem(422, "CONTRACT_VIOLATION", f"{key} 不可只有空白；清除可选字段请使用 null")


def apply_changes(case, changes):
    updated = deepcopy(case)
    before, after = {}, {}
    for key, value in changes.items():
        if value is None:
            if key not in case:
                continue
            updated.pop(key)
        else:
            if key in case and value == case[key]:
                continue
            updated[key] = value
        before[key] = {"present": key in case, "value": case.get(key)}
        after[key] = {"present": key in updated, "value": updated.get(key)}
    if not after:
        raise problem(422, "NO_METADATA_CHANGE", "没有实际变更，不重复写入")
    contracts.validate("case", updated)
    return updated, before, after
