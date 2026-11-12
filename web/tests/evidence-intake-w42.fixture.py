"""Only synthetic isolated cases, used by the W4.2 implementation browser check."""
from copy import deepcopy
import asyncio
from mcis_service.config import Settings
from mcis_service.main import create_app
from mcis_service.seed.lily_mary import seed
from mcis_service.cases.service import load_case
from mcis_service.cases.models import CaseRow
from mcis_service.db import put_doc
settings=Settings();settings.seed_demo=False
app=create_app(settings)
with app.state.db.session() as s:
    seed(s,settings.blob_dir)
    c=load_case(s,'CASE-2026-DEMO-LILY-MARY')
    for cid in ['QA-W42-A','QA-W42-B','QA-W42-C']:
        case=deepcopy(c);case.update(caseId=cid,title='W4.2 合成文件登记验收 '+cid,isFictionalDemo=True,caseEpochUtc='2026-01-01T00:00:00Z');put_doc(s,CaseRow,cid,cid,case)

@app.middleware("http")
async def delayed_commit_body(request, call_next):
    # Synthetic D01 regression: wait before reading the request body.
    if request.url.path == '/api/v1/cases/QA-W42-C/evidence-intakes:commit':
        await asyncio.sleep(1)
    return await call_next(request)
