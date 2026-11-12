"""FastAPI 应用入口。运行：.venv/bin/python -m mcis_service（只监听 127.0.0.1）。"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .knowledge.router import router as knowledge_router
from .agents.router import router as agents_router
from .audit.router import router as audit_router
from .case_metadata.router import router as case_metadata_router
from .cases.router import router as cases_router
from .colreg.router import router as colreg_router
from .config import Settings
from .db import Database
from .environment.router import router as environment_router
from .evidence.router import router as evidence_router
from .interviews.router import router as interviews_router
from .package.router import router as package_router
from .recommendations.router import router as recommendations_router
from .reports.router import router as reports_router
from .redaction.router import router as redaction_router
from .colreg.haili5_seed import seed as seed_haili5
from .seed.lily_mary import seed
from .seed.yangze22 import seed as seed_yangze22
from .sim.router import router as sim_router
from .timeline.router import router as timeline_router
from .analysis.router import router as analysis_router  # W12 分析页（只读种子）
from .interview_compare.router import router as interview_compare_router  # W5 询问笔录比对页


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.blob_dir.mkdir(parents=True, exist_ok=True)
    db = Database(settings.resolved_db_url)
    db.create_all()
    if settings.seed_demo:
        with db.session() as s:
            seed(s, settings.blob_dir)
            seed_haili5(s, settings.blob_dir)
            seed_yangze22(s, settings.blob_dir)

    app = FastAPI(title="MCIS 调查业务服务", version=__version__,
                  description="海事事故调查仿真系统 · 模块③（契约见 contracts/openapi.yaml）。仅监听 127.0.0.1。")
    app.state.settings = settings
    app.state.db = db
    app.state.sim_states = {}
    app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5173", "http://localhost:5173",
                                                      "http://127.0.0.1:4173", "http://localhost:4173"],
                       allow_methods=["*"], allow_headers=["*"], expose_headers=["Content-Disposition", "X-Sha256", "X-MCIS-Redaction"])

    @app.exception_handler(HTTPException)
    async def http_exc(_req: Request, exc: HTTPException):
        body = exc.detail if isinstance(exc.detail, dict) else {"code": f"HTTP_{exc.status_code}", "message": str(exc.detail)}
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def val_exc(_req: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"code": "VALIDATION_ERROR", "message": "请求参数不合法",
                                                      "detail": [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]})

    @app.get("/api/v1/health", tags=["meta"])
    def health():
        return {"status": "ok", "service": "mcis-service", "version": __version__}

    for r in (cases_router, evidence_router, timeline_router, interviews_router, recommendations_router, colreg_router,
              audit_router, redaction_router, agents_router, sim_router, package_router, reports_router):
        app.include_router(r)
    app.include_router(case_metadata_router)  # W8.4 text metadata only
    app.include_router(environment_router)  # W9.2 partial observations only
    app.include_router(knowledge_router)
    app.include_router(analysis_router)  # W12
    app.include_router(interview_compare_router)  # W5
    return app
