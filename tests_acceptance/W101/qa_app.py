"""Actual app + explicitly synthetic isolated DB fixtures; never starts a model."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
from mcis_service.config import Settings
from mcis_service.main import create_app
from mcis_service.seed.lily_mary import seed
from mcis_service.cases.models import CaseRow,VesselRow,TrackPointRow
from mcis_service.db import put_doc
from mcis_service.cases.service import load_case,vessels
st=Settings();st.seed_demo=False
app=create_app(st)
with app.state.db.session() as s:
 seed(s,st.blob_dir)
 template=load_case(s,'CASE-2026-DEMO-LILY-MARY'); vessel=vessels(s,template['caseId'])[0]
 for case_id,title,has_vessel in [('QA-EMPTY','非虚构标记测试档案（独立夹具）',False),('QA-NOPOINT','无轨迹船舶（独立虚构夹具）',True),('QA-TRACK','航迹边界测试（独立虚构夹具）',True)]:
  c=deepcopy(template);c.update(caseId=case_id,title=title,isFictionalDemo=case_id!='QA-EMPTY',caseEpochUtc='2026-01-01T00:00:00Z');put_doc(s,CaseRow,case_id,case_id,c)
  if has_vessel:
   v=deepcopy(vessel);v.update(caseId=case_id,vesselId='QA-V1',name='测试船舶 <img src=x onerror=alert(1)>');put_doc(s,VesselRow,case_id,'QA-V1',v)
 for i in range(2051):
  t=i-1;p={'vesselId':'QA-V1','timeSec':t,'utc':(datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(seconds=t)).isoformat().replace('+00:00','Z'),'latDeg':-90+180*i/2050,'lonDeg':-180+360*i/2050,'sogKn':0 if i==0 else 12.5,'cogDeg':360 if i==0 else 0,'source':'<script>alert(1)</script>' if i==0 else '独立合成测试点','hdgDeg':None}
  if i%3==0:p['provenance']='Measured'
  elif i%3==1:p['provenance']='Interpolated'
  s.add(TrackPointRow(case_id='QA-TRACK',vessel_id='QA-V1',time_sec=t,doc=p))
