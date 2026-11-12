"""Synthetic loopback fixture; no public reports or production database."""
import json,os,socket,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'service'))
from fastapi.testclient import TestClient
from mcis_service.config import Settings
from mcis_service.main import create_app
from mcis_service.cases.models import CaseRow
from mcis_service.db import put_doc
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
import uvicorn
run=Path(os.environ['MCIS_W84_RUN_DIR'])
app=create_app(Settings(data_dir=run/'data',seed_demo=False))
with TestClient(app) as c:
 for name in ['A','B','REDACTED']:
  cid='CASE-W84-'+name
  doc={'caseId':cid,'schemaVersion':'1.0.0','title':'虚构档案 '+name,'accidentType':'Collision',
       'incidentTimeUtc':'2024-01-01T00:00:00Z','caseEpochUtc':'2024-01-01T00:00:00Z',
       'displayTimeZoneOffsetMinutes':0,'incidentLocation':{'lonDeg':0,'latDeg':0},'isFictionalDemo':True,
       'placeName':'虚构地点 '+name,'summaryNotes':'合成说明'}
  result=c.post('/api/v1/cases',json=doc);assert result.status_code==201,result.text
 legacy=dict(doc,caseId='CASE-W84-LEGACY-EMPTY',title='')
 with app.state.db.session() as s:put_doc(s,CaseRow,legacy['caseId'],legacy['caseId'],legacy)
 policy=default_policy();policy['matrix']['Investigator']['ais_sim']='Redacted'
 with app.state.db.session() as s:put_doc(s,AccessPolicyRow,'CASE-W84-REDACTED','policy',policy)
sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
(run/'session.json').write_text(json.dumps({'api':f'http://127.0.0.1:{port}'}))
uvicorn.run(app,host='127.0.0.1',port=port,log_level='warning')
