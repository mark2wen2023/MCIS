"""Isolated server. Only synthetic fixtures, never default/demo runtime storage."""
import os
from pathlib import Path
import uvicorn
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
root=Path(os.environ['MCIS_DATA_DIR'])
app=create_app(Settings(data_dir=root,db_url=f'sqlite:///{root}/network.db',seed_demo=False))
@app.middleware('http')
async def independent_delay(request,call_next):
    if request.headers.get('X-W42-Delay')=='yes':
        import asyncio
        await asyncio.sleep(1)
    return await call_next(request)
with app.state.db.session() as s:
    for cid in ['W42-NETWORK','W42-UI-A','W42-UI-B']:
        doc={'caseId':cid,'schemaVersion':'1.0.0','title':'Independent synthetic '+cid,'accidentType':'Collision','incidentTimeUtc':'2020-01-01T00:00:00Z','caseEpochUtc':'2020-01-01T00:00:00Z','displayTimeZoneOffsetMinutes':0,'incidentLocation':{'latDeg':0,'lonDeg':0},'isFictionalDemo':True}
        put_doc(s,CaseRow,cid,cid,doc)
uvicorn.run(app,host='127.0.0.1',port=int(os.environ['MCIS_PORT']),log_level='warning')
