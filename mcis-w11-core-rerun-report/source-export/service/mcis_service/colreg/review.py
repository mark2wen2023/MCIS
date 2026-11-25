"""核查项人工复核（W6.1 裁定 2/3/4/5/7）。

请求体按 openapi：{action: confirm|dismiss|modify, verdict?, reason?, evidenceIds?}，只接受这四个字段。
W6 旧字段名 reviewStatus/note 已于 W6.2 删除（21:34/21:43 裁定）：传了返回 422 VALIDATION_ERROR，提示改用 action/reason；
其他未在合同里的字段同样 422（extra=forbid）。

- confirm/dismiss 带 verdict → 422 colreg_review_verdict_not_allowed（不静默忽略）
- dismiss/modify 理由必填（空白、全角空格都算空）→ 422 colreg_review_reason_required
- modify 缺 verdict → 422 colreg_review_verdict_required；与当前判定相同 → 422 colreg_review_no_change
- modify 可改成 Undetermined（须填理由）
- confirm：source 不变，只记 reviewStatus=Confirmed、reviewedBy、reviewedAt
- modify：source=Investigator，注解里保留 engineVerdict（第一次修改前的原判定）
- 理由全文保存在版本注解与审计行的 reason 扩展键里，不截断；审计 after 只是显示用摘要
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

from ..common.context import problem

Verdict = Literal["Complies", "Partial", "NotComplied", "NotApplicable", "NeedsReview", "NotAssessable", "Undetermined"]
ACTION_STATUS = {"confirm": "Confirmed", "dismiss": "Rejected", "modify": "Modified"}
ACTION_LABEL = {"confirm": "确认", "dismiss": "驳回", "modify": "修改"}
LEGACY_FIELDS = ("reviewStatus", "note")


class CheckReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["confirm", "dismiss", "modify"]
    verdict: Verdict | None = None
    reason: str | None = None
    evidenceIds: list[str] | None = None

    @model_validator(mode="before")
    @classmethod
    def _reject_legacy(cls, data: Any) -> Any:
        if isinstance(data, dict):
            legacy = [k for k in LEGACY_FIELDS if k in data]
            if legacy:
                raise ValueError(f"旧字段名 {'/'.join(legacy)} 已删除（W6.2），请改用 action（confirm/dismiss/modify）与 reason")
        return data

    @property
    def status(self) -> str:
        return ACTION_STATUS[self.action]  # type: ignore[index]

    @property
    def clean_reason(self) -> str:
        # str.strip() 已涵盖 \t \n 与全角空格 \u3000
        return (self.reason or "").strip()


def validate(body: CheckReview, chk: dict[str, Any]) -> None:
    """只做与数据相关的校验；不改任何东西。证据登记由调用方用 evidence_refs 校验。"""
    act = body.action
    if act in ("confirm", "dismiss") and body.verdict is not None:
        raise problem(422, "colreg_review_verdict_not_allowed", f"{ACTION_LABEL[act]}时不能传 verdict；要改判定请用 modify")
    if act in ("dismiss", "modify") and not body.clean_reason:
        raise problem(422, "colreg_review_reason_required", "驳回或修改须填写理由")
    if act == "modify":
        if body.verdict is None:
            raise problem(422, "colreg_review_verdict_required", "修改须给出新的判定")
        if body.verdict == chk.get("verdict"):
            raise problem(422, "colreg_review_no_change", f"新判定与当前判定相同（{body.verdict}），不构成修改")


def snapshot(chk: dict[str, Any]) -> str:
    return f"verdict={chk.get('verdict')}; reviewStatus={chk.get('reviewStatus') or 'Draft'}; source={chk.get('source') or ''}"


def after_summary(chk: dict[str, Any], reason: str) -> str:
    """显示用摘要（审计层可能截断到 400 字）；理由全文另存 reason 扩展键。"""
    base = snapshot(chk)
    return f"{base}; reason={reason}" if reason else base


def apply(chk: dict[str, Any], ann: dict[str, Any], body: CheckReview, *, operator: str, utc: str,
          evidence_ids: list[str]) -> dict[str, Any]:
    """改核查项（colreg.schema 内字段）与版本注解（schema 外字段）。返回本次历史记录。"""
    before_verdict = chk.get("verdict")
    before_source = chk.get("source")
    act = body.action
    chk["reviewStatus"] = body.status
    if act == "modify":
        ann.setdefault("engineVerdict", before_verdict)
        ann.setdefault("engineSource", before_source)
        chk["verdict"] = body.verdict
        chk["source"] = "Investigator"
        if body.evidenceIds is not None:
            chk["evidenceIds"] = list(evidence_ids)
    ann["reviewedBy"] = operator
    ann["reviewedAt"] = utc
    ann["lastAction"] = act
    ann["reason"] = body.clean_reason
    if act != "modify" and evidence_ids:
        ann["reviewEvidenceIds"] = list(evidence_ids)
    entry = {"action": act, "reviewStatus": body.status, "verdictBefore": before_verdict, "verdictAfter": chk.get("verdict"),
             "sourceBefore": before_source, "sourceAfter": chk.get("source"), "reason": body.clean_reason,
             "evidenceIds": list(evidence_ids), "operator": operator, "utc": utc}
    ann.setdefault("history", []).append(entry)
    return entry
