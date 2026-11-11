"""字段级脱敏网关：服务出口按角色应用。路由只调用 require() + redact_*()。"""
from __future__ import annotations

import copy
import re
from typing import Any

from sqlalchemy.orm import Session

from ..common.context import Ctx, problem
from ..db import get_doc
from .models import AccessPolicyRow
from .policy import DENY, RD, RW, default_policy

MASK = "██████"
FRAGMENT_MASK = "[已遮盖]"
PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d[ -]?\d{4}[ -]?\d{4}(?!\d)")
IDNO_RE = re.compile(r"(?<!\d)\d{15}(?:\d{2}[\dXx])?(?!\d)")


def get_policy(s: Session, case_id: str) -> dict:
    return get_doc(s, AccessPolicyRow, case_id, "policy") or default_policy()


def level_of(policy: dict, role: str, category: str) -> str:
    return policy.get("matrix", {}).get(role, {}).get(category, DENY)


def require(ctx: Ctx, s: Session, case_id: str, category: str, write: bool = False) -> str:
    lvl = level_of(get_policy(s, case_id), ctx.role, category)
    if lvl == DENY:
        raise problem(403, "FORBIDDEN", f"角色 {ctx.role} 无权访问 {category}")
    if write and lvl != RW:
        raise problem(403, "READ_ONLY", f"角色 {ctx.role} 对 {category} 只有 {lvl} 权限")
    return lvl


def _rules_for(policy: dict, role: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for r in policy.get("fieldRules", []):
        if role in r.get("appliesTo", []):
            out[r["field"]] = r["method"]
    return out


def mask_pii(text: str) -> str:
    text = PHONE_RE.sub(MASK, text)
    return IDNO_RE.sub(MASK, text)


def redact_text(text: str, *, names: dict[str, str], fragments: list[str], mask_fragments: bool) -> str:
    for name, repl in names.items():
        if name:
            text = text.replace(name, repl)
    if mask_fragments:
        for frag in fragments:
            if frag:
                text = text.replace(frag, FRAGMENT_MASK)
    return mask_pii(text)


def redact_interview(doc: dict[str, Any], role: str, policy: dict, token_index: int = 1) -> dict[str, Any]:
    """返回脱敏后的副本。首席调查官看原文；调查员只遮盖证件/电话；外部角色按规则替换。"""
    rules = _rules_for(policy, role)
    d = copy.deepcopy(doc)
    iv = d.get("interviewee", {})
    real_name = iv.get("name", "")
    names: dict[str, str] = {}
    if rules.get("interviewee.name") == "Token":
        names[real_name] = f"<ROLE_{token_index:02d}>"
    elif rules.get("interviewee.name") == "RoleCode":
        names[real_name] = iv.get("role", "受询问人")
    if names.get(real_name):
        iv["name"] = names[real_name]
    if "pii.idNumber+phone" in rules:
        for k in ("idNumber", "phone"):
            if iv.get(k):
                iv[k] = MASK
    mask_frag = "turns.sensitiveFragments" in rules
    redacted_any = bool(names) or mask_frag or "pii.idNumber+phone" in rules
    for t in d.get("turns", []):
        frags = t.get("sensitiveFragments", [])
        t["question"] = redact_text(t.get("question", ""), names=names, fragments=frags, mask_fragments=mask_frag)
        t["answer"] = redact_text(t.get("answer", ""), names=names, fragments=frags, mask_fragments=mask_frag)
        if mask_frag:
            t["sensitiveFragments"] = []
    for st in d.get("statements", []):
        st["quote"] = redact_text(st.get("quote", ""), names=names, fragments=[], mask_fragments=False)
    if redacted_any and role != "LeadInvestigator":
        d["_redaction"] = {"role": role, "rules": sorted(rules.keys())}
    return d


def strip_meta(doc: dict[str, Any]) -> dict[str, Any]:
    d = dict(doc)
    d.pop("_redaction", None)
    return d


def filter_evidence(items: list[dict[str, Any]], role: str, policy: dict) -> list[dict[str, Any]]:
    rules = _rules_for(policy, role)
    testimony = level_of(policy, role, "testimony")
    out = []
    for it in items:
        if it.get("confidentiality") == "Restricted" and (testimony == DENY or rules.get("evidence.restricted") == "Remove"):
            continue
        out.append(it)
    return out


__all__ = ["get_policy", "level_of", "require", "redact_interview", "filter_evidence", "redact_text", "mask_pii",
           "RW", "RD", "DENY", "MASK", "FRAGMENT_MASK", "strip_meta"]
