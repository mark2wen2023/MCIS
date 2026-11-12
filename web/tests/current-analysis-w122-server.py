import os
from pathlib import Path
from datetime import datetime,timedelta,timezone
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow,VesselRow,TrackPointRow
s=Settings();s.seed_demo=False;s.data_dir=Path(os.environ['MCIS_DATA_DIR']);s.db_url='sqlite:///'+str(s.data_dir/'browser.db')
app=create_app(s)
with app.state.db.session() as session:
 for cid in ['SYNTHETIC-W122','EMPTY-W122']:
  put_doc(session,CaseRow,cid,cid,dict(caseId=cid,title='Synthetic browser only',isFictionalDemo=True,caseEpochUtc='2026-01-01T00:00:00Z',incidentLocation={'latDeg':0,'lonDeg':0}))
  for v in ['A','B']:put_doc(session,VesselRow,cid,v,dict(caseId=cid,vesselId=v,name='Synthetic '+v))
 for v in ['A','B']:
  for t in range(205):
   p=dict(vesselId=v,timeSec=t,utc=(datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(seconds=t)).isoformat().replace('+00:00','Z'),latDeg=0,lonDeg=0 if v=='A' else .01,sogKn=10 if v=='A' else 0,cogDeg=90,provenance='Measured' if v=='A' else 'Interpolated',source='<img src=x onerror=window.pwned=1> declared only')
   session.add(TrackPointRow(case_id='SYNTHETIC-W122',vessel_id=v,time_sec=t,doc=p))
import uvicorn
uvicorn.run(app,host='127.0.0.1',port=15861)
