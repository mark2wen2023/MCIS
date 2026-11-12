"""Implementation smoke fixture: isolated synthetic cases, never user data."""
from copy import deepcopy
from mcis_service.config import Settings
from mcis_service.main import create_app
from mcis_service.seed.lily_mary import seed
from mcis_service.cases.service import load_case,vessels
from mcis_service.cases.models import CaseRow,VesselRow
from mcis_service.db import put_doc
settings=Settings();settings.seed_demo=False
app=create_app(settings)
with app.state.db.session() as s:
 seed(s,settings.blob_dir)
 c=load_case(s,'CASE-2026-DEMO-LILY-MARY');v=vessels(s,c['caseId'])[0]
 for cid in ['QA-W102-A','QA-W102-B']:
  case=deepcopy(c);case.update(caseId=cid,title='W10.2 合成输入验收',isFictionalDemo=True,caseEpochUtc='2026-01-01T00:00:00Z');put_doc(s,CaseRow,cid,cid,case)
  for vid in ['V1','V2']:
   ship=deepcopy(v);ship.update(caseId=cid,vesselId=vid,name='测试船'+vid);put_doc(s,VesselRow,cid,vid,ship)
