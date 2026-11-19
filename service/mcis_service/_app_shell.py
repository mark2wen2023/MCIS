"""Private application shell; no business imports or initialization."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__


def _create_app_shell(settings, db) -> FastAPI:
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

    return app
