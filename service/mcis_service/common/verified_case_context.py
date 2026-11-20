"""Opt-in dependency for a future restricted app, NEVER installed by default.

Verifier must authenticate the opaque bearer credential and authorize the exact
case/operation on every call. A matching object is not authentication by itself.
Existing handler policy, byte binding, history guards and audit still apply.
"""
from dataclasses import dataclass
import re
from fastapi import Request
from .context import Ctx, ROLES, get_ctx, problem


@dataclass(frozen=True)
class CaseGrant:
    subject: str  # Stable server-verified audit identity, not a display/header alias.
    role: str
    case_id: str
    operation: str


# Exact server route templates, not URL/query supplied capabilities.
_OPERATIONS = {
    ('GET', '/api/v1/cases/{case_id}'): 'case.read',
    ('POST', '/api/v1/cases/{case_id}/evidence-intakes:preview'): 'evidence.preview',
    ('POST', '/api/v1/cases/{case_id}/evidence-intakes:commit'): 'evidence.register',
    ('GET', '/api/v1/cases/{case_id}/evidence-intakes/{digest}'): 'evidence.receipt.read',
    ('GET', '/api/v1/cases/{case_id}/evidence/{evidence_id}/intake'): 'evidence.receipt.read',
    ('POST', '/api/v1/cases/{case_id}/evidence-intakes/{digest}:download'): 'evidence.original.access',
    ('GET', '/api/v1/cases/{case_id}/image-reviews'): 'image.list',
    ('POST', '/api/v1/cases/{case_id}/image-reviews'): 'image.import',
    ('GET', '/api/v1/cases/{case_id}/image-reviews/{run_id}'): 'image.read',
    ('POST', '/api/v1/cases/{case_id}/image-reviews/{run_id}/reviews'): 'image.revise',
    ('GET', '/api/v1/cases/{case_id}/audio-reviews'): 'audio.list',
    ('POST', '/api/v1/cases/{case_id}/audio-reviews'): 'audio.import',
    ('GET', '/api/v1/cases/{case_id}/audio-reviews/{run_id}'): 'audio.read',
    ('POST', '/api/v1/cases/{case_id}/audio-reviews/{run_id}/revisions'): 'audio.revise',
    ('GET', '/api/v1/cases/{case_id}/audio-reviews/source/{digest}'): 'audio.source.read',
}


def _make_verified_case_dependency(verifier=None, *, credential_reader=None):
    """verifier: async (credential, case_id, operation) -> CaseGrant or None.

    Configure per app at construction, never from request state or headers.
    Credential validation, expiry/revocation and actual case membership belong
    to the injected verifier. No verifier is supplied by this candidate.
    """
    async def verified_context(request: Request) -> Ctx:
        if verifier is None:
            raise problem(503, 'IDENTITY_UNCONFIGURED', '可信身份源尚未配置')
        route = request.scope.get('route')
        operation = _OPERATIONS.get((request.method, getattr(route, 'path', None)))
        case_id = request.path_params.get('case_id')
        if operation is None or not isinstance(case_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', case_id):
            raise problem(403, 'CASE_SCOPE_REQUIRED', '此入口未开放该案件操作')
        if credential_reader is None:
            values = request.headers.getlist('authorization')
            if len(values) != 1 or not values[0].startswith('Bearer '):
                raise problem(401, 'AUTHENTICATION_REQUIRED', '需要已验证身份')
            credential = values[0][7:]
        else:
            # Explicit trusted transport adapter, never selected by the request.
            credential = credential_reader(request)
        if not isinstance(credential, str) or not credential or len(credential) > 8192 or any(c.isspace() for c in credential):
            raise problem(401, 'AUTHENTICATION_REQUIRED', '需要已验证身份')
        try:
            grant = await verifier(credential, case_id, operation)
        except Exception:
            # Do not expose credentials, provider errors or case existence.
            raise problem(503, 'IDENTITY_UNAVAILABLE', '身份与案件授权核查未完成') from None
        if (type(grant) is not CaseGrant or grant.case_id != case_id or grant.operation != operation
                or grant.role not in ROLES or not isinstance(grant.subject, str)
                or not grant.subject.strip() or grant.subject != grant.subject.strip()
                or len(grant.subject) > 200 or any(ord(c) < 32 or ord(c) == 127 for c in grant.subject)):
            raise problem(403, 'CASE_OPERATION_DENIED', '未确认当前案件操作权限')
        return Ctx(role=grant.role, operator=grant.subject, request=request)
    return verified_context


def _install_verified_case_context(app, *, verifier=None, credential_reader=None):
    """Only for an explicitly constructed restricted app BEFORE it serves requests.

    This overrides existing CtxDep consumers on this app, not static HTML routes
    or handlers without CtxDep. Unknown Ctx routes fail closed. Not middleware,
    not a factory and not proof that every registered route is protected.
    """
    if get_ctx in app.dependency_overrides:
        raise ValueError('context dependency already overridden')
    dependency = _make_verified_case_dependency(verifier, credential_reader=credential_reader)
    app.dependency_overrides[get_ctx] = dependency
    return dependency
