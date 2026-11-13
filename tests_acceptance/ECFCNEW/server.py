"""Owned synthetic-only loopback service for independent browser acceptance."""
import os
from pathlib import Path
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.evidence.models import EvidenceRow
root=Path(os.environ['ECFC_ACCEPTANCE_DATA'])
app=create_app(Settings(data_dir=root,db_url=f"sqlite:///{root / 'mcis.db'}",seed_demo=False))
with app.state.db.session() as s:
 for cid in ('INDEPENDENT-BROWSER-A','INDEPENDENT-BROWSER-B'):
  put_doc(s,CaseRow,cid,cid,{'caseId':cid,'title':'Independent synthetic ECFC browser','schemaVersion':'1.0.0','accidentType':'Collision','isFictionalDemo':True,'caseEpochUtc':'2026-01-01T00:00:00Z','incidentTimeUtc':'2026-01-01T00:00:00Z','incidentLocation':{'lonDeg':121,'latDeg':31},'displayTimeZoneOffsetMinutes':0})
  put_doc(s,EvidenceRow,cid,'EV-901',{'caseId':cid,'evidenceId':'EV-901','title':'Independent synthetic source','sha256':'b'*64,'confidentiality':'Restricted'})
if __name__=='__main__':
 import uvicorn
 uvicorn.run(app,fd=int(os.environ['ECFC_ACCEPTANCE_FD']),log_level='error')
