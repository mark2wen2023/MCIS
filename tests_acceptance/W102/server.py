import os, contextvars
from pathlib import Path
from fastapi import Request
import uvicorn
from sqlalchemy.orm import Session
from mcis_service.main import create_app
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow,VesselRow
from mcis_service.tracks_import import router as r
app=create_app()
if os.environ.get('ACCEPT_SEED','1')=='1':
 with app.state.db.session() as s:
  for i in range(40):
   cid=f'ACCEPT-W102-{i}'
   put_doc(s,CaseRow,cid,cid,dict(caseId=cid,schemaVersion='1.0.0',title='合成验收案件 '+str(i),accidentType='Collision',incidentTimeUtc='2026-01-01T00:00:00Z',caseEpochUtc='2026-01-01T00:00:00Z',displayTimeZoneOffsetMinutes=0,incidentLocation={'latDeg':0,'lonDeg':0},isFictionalDemo=True))
   for v in ['V1','V2']: put_doc(s,VesselRow,cid,v,dict(caseId=cid,vesselId=v,name='合成船 '+v))
fault=contextvars.ContextVar('fault',default='')
@app.middleware('http')
async def inject(request:Request,call_next):
 token=fault.set(request.headers.get('X-Accept-Fault',''))
 try:return await call_next(request)
 finally:fault.reset(token)
orig_write=r.exclusive_write
orig_commit=Session.commit
orig_unlink=Path.unlink
def write(path,data,created):
 if fault.get() in ('file2','cleanup') and path.name=='report.json':raise OSError('Independent injected file 2 failure')
 return orig_write(path,data,created)
def commit(self):
 if fault.get()=='dbcommit' and list(app.state.settings.blob_dir.rglob('report.json')) and any(x.name=='report.json' for x in (app.state.settings.blob_dir/'ACCEPT-W102-7').rglob('*')):raise OSError('Independent injected DB commit failure')
 return orig_commit(self)
def unlink(self,*a,**kw):
 if fault.get()=='cleanup' and self.name=='source.csv':raise OSError('Independent injected cleanup failure')
 return orig_unlink(self,*a,**kw)
r.exclusive_write=write;Session.commit=commit;Path.unlink=unlink
uvicorn.run(app,host='127.0.0.1',port=int(os.environ['MCIS_PORT']),log_level='warning')
