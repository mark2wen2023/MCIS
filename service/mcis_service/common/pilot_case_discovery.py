"""Opt-in real case discovery endpoint; no factory, database initialization or login.

Only a dedicated, explicitly prepared synthetic app may register this endpoint.
Its existing app.state.db must already have the audited schema and protections.
"""
from fastapi import Request, Response
from .context import problem
from .local_review_pilot import PilotSessions, _cookie_reader

PATH = '/api/v1/pilot/cases'


def _register_pilot_case_discovery(app, *, enabled=False, sessions=None, origin=None):
    # No arbitrary route injection or replacement of existing case/list handlers.
    if any(getattr(route, 'path', None) == PATH for route in app.routes):
        raise ValueError('pilot case discovery already registered')
    configured = enabled is True and type(sessions) is PilotSessions and isinstance(origin, str)
    read_cookie = _cookie_reader(origin) if configured else None

    @app.get(PATH, response_model=list[dict[str, str]])
    async def authorized_cases(request: Request, response: Response):
        response.headers['Cache-Control'] = 'no-store'
        if not configured:
            raise problem(503, 'IDENTITY_UNCONFIGURED', '可信试用会话尚未配置')
        credential = read_cookie(request)
        case_ids = sessions.authorized_cases(credential)
        if case_ids is None:
            raise problem(403, 'CASE_OPERATION_DENIED', '未确认案件发现权限')
        if not case_ids:
            return []  # No import or database access for empty permission set.
        # Real existing point lookup; never cases.list_cases or list_docs.
        from ..cases.service import load_case
        result = []
        with request.app.state.db.session() as session:
            with session.no_autoflush:
                for case_id in case_ids:
                    if await sessions.verify(credential, case_id, 'case.read') is None:
                        raise problem(403, 'CASE_OPERATION_DENIED', '案件发现权限已失效')
                    doc = load_case(session, case_id)
                    if (not isinstance(doc, dict) or doc.get('caseId') != case_id
                            or not isinstance(doc.get('title'), str)):
                        raise problem(409, 'PILOT_CASE_UNCONFIRMED', '无法确认获授权案件摘要')
                    result.append({'caseId': case_id, 'title': doc['title']})
                if sessions.authorized_cases(credential) != case_ids:
                    raise problem(403, 'CASE_OPERATION_DENIED', '案件发现权限已失效')
        return result
    return authorized_cases
