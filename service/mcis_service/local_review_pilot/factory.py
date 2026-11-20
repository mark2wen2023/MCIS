"""Explicit synthetic-only case workbench factory. Never used by default startup.

Optional image imports use registered receipts only; task sources are refused.
The caller must provision a NEW exclusively owned temporary SQLite Database,
trusted ephemeral sessions and HTTPS loopback transport before calling this.
No login/token issuance, seed, business records or server startup is provided.
"""
from pathlib import Path
from urllib.parse import urlsplit
from types import SimpleNamespace

ROUTES = frozenset({('GET', '/pilot'), ('GET', '/api/v1/pilot/cases'),
                    ('GET', '/api/v1/cases/{case_id}')})

IMAGE_ROUTES = frozenset({
    ('GET', '/pilot/image-review'),
    ('GET', '/image-review-lab/preview.js'),
    ('GET', '/api/v1/cases/{case_id}/evidence-intakes/{digest}'),
    ('POST', '/api/v1/cases/{case_id}/image-reviews'),
    ('GET', '/api/v1/cases/{case_id}/image-reviews'),
    ('GET', '/api/v1/cases/{case_id}/image-reviews/{run_id}'),
    ('POST', '/api/v1/cases/{case_id}/image-reviews/{run_id}/reviews'),
})

REGISTRATION_ROUTES = frozenset({
    ('POST', '/api/v1/cases/{case_id}/evidence-intakes:preview'),
    ('POST', '/api/v1/cases/{case_id}/evidence-intakes:commit'),
})


def create_local_review_pilot(*, enabled=False, db=None, sessions=None, origin=None,
                              image_imports=False, image_blob_dir=None, evidence_registration=False):
    if enabled is not True:
        raise ValueError('synthetic pilot is disabled')
    from ..common.local_review_pilot import PilotSessions, _cookie_reader, _install_local_review_pilot
    if type(sessions) is not PilotSessions or db is None or not isinstance(origin, str):
        raise ValueError('explicit pilot storage, sessions and origin required')
    _cookie_reader(origin)  # Validate exact transport configuration before DDL.
    if urlsplit(origin).hostname != '127.0.0.1':
        raise ValueError('pilot requires HTTPS on 127.0.0.1')

    if type(image_imports) is not bool:
        raise ValueError('explicit image capability required')
    if type(evidence_registration) is not bool or (evidence_registration and not image_imports):
        raise ValueError('registration requires explicit image pilot capability')
    if image_imports and (not isinstance(image_blob_dir, Path) or not image_blob_dir.is_absolute()):
        raise ValueError('explicit absolute synthetic blob root required')

    from fastapi import FastAPI, Depends, Response, APIRouter
    from fastapi.responses import HTMLResponse
    from ..common.context import Ctx, problem
    from ..common.pilot_case_discovery import _register_pilot_case_discovery
    from ..common.pilot_core_storage import _initialize_pilot_core_storage
    from .pages import workbench_page, _mount_pilot_image_pages

    # Public static shell carries no identity or case data. All data requests
    # below independently verify the server session; no legacy header fallback.
    html = Path(__file__).with_name('workbench.html').read_text(encoding='utf-8')
    html = workbench_page(html, images=image_imports)
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

    if image_imports:
        from ..image_review.app import _mount_image_imports_only, _initialize_image_review_storage
        from ..evidence_intake.router import receipt_input
        from ..reports.access import NoStoreRoute
        # Only the existing receipt reader, not the intake router or download.
        app.state.settings = SimpleNamespace(blob_dir=image_blob_dir)
        receipt_router = APIRouter(route_class=NoStoreRoute)
        receipt_router.add_api_route('/api/v1/cases/{case_id}/evidence-intakes/{digest}',
                                     receipt_input, methods=['GET'])
        if evidence_registration:
            from ..evidence_intake.router import preview_input, commit_input
            # Preserve original bounded body, identity-bound digest, history,
            # exclusive file write, custody/audit and cleanup behavior in full.
            receipt_router.add_api_route('/api/v1/cases/{case_id}/evidence-intakes:preview',
                                         preview_input, methods=['POST'])
            receipt_router.add_api_route('/api/v1/cases/{case_id}/evidence-intakes:commit',
                                         commit_input, methods=['POST'])
        app.include_router(receipt_router)
        _mount_image_imports_only(app)
        _mount_pilot_image_pages(app)

    expected = ROUTES | IMAGE_ROUTES if image_imports else ROUTES
    if evidence_registration:
        expected = expected | REGISTRATION_ROUTES
    actual = [(method, route.path) for route in app.routes for method in route.methods]
    if len(actual) != len(expected) or frozenset(actual) != expected:
        raise RuntimeError('pilot route surface changed; initialization refused')
    _initialize_pilot_core_storage(db)
    if image_imports:
        _initialize_image_review_storage(app, imported_only=True)
    return app
