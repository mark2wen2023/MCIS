"""Explicit synthetic-only case workbench factory. Never used by default startup.

No media routes yet: their task-binding/storage closure is not approved.
The caller must provision a NEW exclusively owned temporary SQLite Database,
trusted ephemeral sessions and HTTPS loopback transport before calling this.
No login/token issuance, seed, business records or server startup is provided.
"""
from pathlib import Path
from urllib.parse import urlsplit

ROUTES = frozenset({('GET', '/pilot'), ('GET', '/api/v1/pilot/cases'),
                    ('GET', '/api/v1/cases/{case_id}')})


def create_local_review_pilot(*, enabled=False, db=None, sessions=None, origin=None):
    if enabled is not True:
        raise ValueError('synthetic pilot is disabled')
    from ..common.local_review_pilot import PilotSessions, _cookie_reader, _install_local_review_pilot
    if type(sessions) is not PilotSessions or db is None or not isinstance(origin, str):
        raise ValueError('explicit pilot storage, sessions and origin required')
    _cookie_reader(origin)  # Validate exact transport configuration before DDL.
    if urlsplit(origin).hostname != '127.0.0.1':
        raise ValueError('pilot requires HTTPS on 127.0.0.1')

    from fastapi import FastAPI, Depends, Response
    from fastapi.responses import HTMLResponse
    from ..common.context import Ctx, problem
    from ..common.pilot_case_discovery import _register_pilot_case_discovery
    from ..common.pilot_core_storage import _initialize_pilot_core_storage

    # Public static shell carries no identity or case data. All data requests
    # below independently verify the server session; no legacy header fallback.
    html = Path(__file__).with_name('workbench.html').read_text(encoding='utf-8')
    app = FastAPI(title='MCIS synthetic case pilot', docs_url=None,
                  redoc_url=None, openapi_url=None, redirect_slashes=False)
    app.state.db = db
    verified = _install_local_review_pilot(app, enabled=True, sessions=sessions, origin=origin)
    _register_pilot_case_discovery(app, enabled=True, sessions=sessions, origin=origin)

    @app.get('/api/v1/cases/{case_id}')
    def case_detail(case_id: str, response: Response, ctx: Ctx = Depends(verified)):
        response.headers['Cache-Control'] = 'no-store'
        # Reuse the real point lookup, not the unrestricted cases list router.
        from ..cases.service import load_case
        with ctx.db.session() as session:
            with session.no_autoflush:
                doc = load_case(session, case_id)
                if not isinstance(doc, dict) or doc.get('caseId') != case_id or not isinstance(doc.get('title'), str):
                    raise problem(409, 'PILOT_CASE_UNCONFIRMED', '无法确认获授权案件详情')
                return doc

    @app.get('/pilot', response_class=HTMLResponse)
    def workbench():
        return HTMLResponse(html, headers={'Cache-Control': 'no-store',
                            'Referrer-Policy': 'no-referrer',
                            'X-Content-Type-Options': 'nosniff',
                            'X-Frame-Options': 'DENY'})

    actual = [(method, route.path) for route in app.routes for method in route.methods]
    if len(actual) != len(ROUTES) or frozenset(actual) != ROUTES:
        raise RuntimeError('pilot route surface changed; initialization refused')
    _initialize_pilot_core_storage(db)
    return app
