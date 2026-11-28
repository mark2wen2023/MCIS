"""Owned synthetic-only loopback service for the W11 real save/reopen acceptance.
Seeds the fictional case only when the temporary SQLite has none, so a restart reuses the same database untouched."""
import os
from pathlib import Path
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import get_doc, put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.evidence.models import EvidenceRow
CID='W11-REAL-SAVE-FICTIONAL'
root=Path(os.environ['W11_SAVE_DATA'])
app=create_app(Settings(data_dir=root,db_url=f"sqlite:///{root / 'mcis.db'}",seed_demo=False))
with app.state.db.session() as s:
 if get_doc(s,CaseRow,CID,CID) is None:
  put_doc(s,CaseRow,CID,CID,{'caseId':CID,'title':'W11 fictional ECFC save/reopen','schemaVersion':'1.0.0','accidentType':'Collision','isFictionalDemo':True,'caseEpochUtc':'2026-01-01T00:00:00Z','incidentTimeUtc':'2026-01-01T00:00:00Z','incidentLocation':{'lonDeg':121,'latDeg':31},'displayTimeZoneOffsetMinutes':0})
  put_doc(s,EvidenceRow,CID,'EV-901',{'caseId':CID,'evidenceId':'EV-901','title':'Fictional synthetic source (not a real case file)','sha256':'b'*64,'confidentiality':'Restricted'})
if __name__=='__main__':
 import uvicorn
 uvicorn.run(app,fd=int(os.environ['W11_SAVE_FD']),log_level='warning')
