"""Localhost-only browser fixture, uses the exact same app/adapter as the DOM test."""
import sys
from pathlib import Path

from fastapi import Depends
from fastapi.responses import FileResponse, HTMLResponse
import uvicorn
from host import CASE, Settings, create_app, ec, get_ctx, setup

store,bundle,port=sys.argv[1:]
root=Path(store)
cfg=Settings(data_dir=root,db_url=f"sqlite:///{root/'w11.sqlite'}",seed_demo=False)
app=create_app(cfg)
setup(app)

@app.get("/",include_in_schema=False)
def index():
    return HTMLResponse('<!doctype html><html lang="zh"><meta charset="utf-8"><title>W11 合成验收</title><div id="root"></div><script defer src="/app.js"></script></html>')

@app.get("/app.js",include_in_schema=False)
def script():
    return FileResponse(bundle,media_type="text/javascript",headers={"Cache-Control":"no-store"})

@app.get(f"/__local_synthetic_w11/{CASE}/draft",include_in_schema=False)
def get_bound_draft(ctx=Depends(get_ctx)):
    return ec.get_draft(CASE,ctx)

uvicorn.run(app,host="127.0.0.1",port=int(port),log_level="warning")
