"""请求上下文：角色与操作者来自 HTTP 头（本地单机服务，未做身份认证，见 CONTRACTS.md 已知限制）。"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import unquote

from fastapi import Depends, HTTPException, Request

ROLES = ("LeadInvestigator", "Investigator", "ExternalExpert", "InterestedState", "AgentService", "Public")


@dataclass
class Ctx:
    role: str
    operator: str
    request: Request
    principal: object | None = None

    @property
    def db(self):
        return self.request.app.state.db

    @property
    def settings(self):
        return self.request.app.state.settings


def get_ctx(request: Request) -> Ctx:
    if getattr(request.app.state, 'identity_mode', None) == 'authenticated':
        p = getattr(request.state, 'principal', None)
        if p is None:
            raise HTTPException(401, detail={'code':'UNAUTHENTICATED'})
        # Read-only context. Client role/operator headers are ignored.
        return Ctx(role='Public', operator=p.display_name, request=request, principal=p)
    role = request.headers.get("X-MCIS-Role", "Investigator")
    if role not in ROLES:
        raise HTTPException(400, detail={"code": "BAD_ROLE", "message": f"未知角色 {role}"})
    op = unquote(request.headers.get("X-MCIS-Operator", "")) or {"LeadInvestigator": "首席调查官", "Investigator": "调查员"}.get(role, role)
    return Ctx(role=role, operator=op, request=request)


CtxDep = Depends(get_ctx)


def problem(status: int, code: str, message: str, detail=None) -> HTTPException:
    body = {"code": code, "message": message}
    if detail is not None:
        body["detail"] = detail
    return HTTPException(status, detail=body)
