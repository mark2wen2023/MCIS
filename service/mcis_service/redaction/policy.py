"""默认权限矩阵与字段级脱敏规则（与原型 s15_17「权限与脱敏设置」页一致）。"""
from __future__ import annotations

import copy

CATEGORIES = ["ais_sim", "vdr_audio", "testimony", "personal", "medical", "report_draft",
              "evidence_meta", "timeline", "colreg", "recommendations", "audit", "agent_drafts"]

RW, RO, RD, DENY = "ReadWrite", "ReadOnly", "Redacted", "Deny"

_MATRIX = {
    #                  ais  vdr   test  pers  med   report evid  tl   colreg recs audit agent
    "LeadInvestigator": [RW, RW, RW, RW, RO, RW, RW, RW, RW, RW, RO, RW],
    "Investigator":     [RW, RO, RW, RO, DENY, RW, RW, RW, RW, RW, RO, RW],
    "ExternalExpert":   [RO, RD, RD, DENY, DENY, DENY, RO, RO, RO, RO, DENY, DENY],
    "InterestedState":  [RO, DENY, RD, DENY, DENY, RO, RO, RO, RO, RO, DENY, DENY],
    "AgentService":     [RO, RD, RD, DENY, DENY, RO, RO, RO, RO, RO, DENY, RW],
    "Public":           [RO, DENY, DENY, DENY, DENY, DENY, DENY, DENY, DENY, RO, DENY, DENY],
}

FIELD_RULES = [
    {"ruleId": "FR-01", "field": "interviewee.name", "method": "RoleCode", "appliesTo": ["ExternalExpert", "InterestedState", "Public"],
     "description": "人员姓名替换为角色代号（张某 → 二副(OOW)）"},
    {"ruleId": "FR-02", "field": "pii.idNumber+phone", "method": "Mask", "appliesTo": ["Investigator", "ExternalExpert", "InterestedState", "AgentService", "Public"],
     "description": "证件号 / 电话全部遮盖（除首席外）"},
    {"ruleId": "FR-03", "field": "turns.sensitiveFragments", "method": "Mask", "appliesTo": ["ExternalExpert", "InterestedState", "AgentService", "Public"],
     "description": "与调查无关的个人隐私片段遮盖为 [已遮盖]"},
    {"ruleId": "FR-04", "field": "interviewee.name", "method": "Token", "appliesTo": ["AgentService"],
     "description": "发给 LLM 的文本：姓名先替换为 <ROLE_xx> 再发送"},
    {"ruleId": "FR-05", "field": "evidence.restricted", "method": "Remove",
     "appliesTo": ["ExternalExpert", "InterestedState", "AgentService", "Public"],
     "description": "Restricted 证据（MSC.255(84) 第 23 章保密资料）仅调查组可见，不对外部角色列出"},
]

DEFAULT_POLICY = {
    "version": "1.0.0",
    "categories": CATEGORIES,
    "matrix": {role: dict(zip(CATEGORIES, levels)) for role, levels in _MATRIX.items()},
    "fieldRules": FIELD_RULES,
}


def default_policy() -> dict:
    return copy.deepcopy(DEFAULT_POLICY)
