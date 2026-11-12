"""Owned loopback test service, synthetic HTTP fixture only."""
import os,json
from pathlib import Path
from fastapi.testclient import TestClient
from mcis_service.main import create_app
from mcis_service.config import Settings
from test_bundle import CASE,HEADERS,BASE
root=Path(os.environ['OUTPUT_ACCEPTANCE_DATA'])
app=create_app(Settings(data_dir=root,seed_demo=False))
with TestClient(app) as c:
    r=c.post('/api/v1/cases',headers=HEADERS,json={'caseId':CASE,'schemaVersion':'1.0.0','title':'虚构浏览器下载验收','accidentType':'Collision','isFictionalDemo':True,'caseEpochUtc':'2026-01-01T00:00:00Z','incidentTimeUtc':'2026-01-01T00:00:00Z','incidentLocation':{'lonDeg':121,'latDeg':31},'displayTimeZoneOffsetMinutes':0})
    assert r.status_code==201,r.text
    r=c.post(BASE+'/reports',headers=HEADERS,json={'templateId':'imo-cic','lang':'bilingual'})
    assert r.status_code==201,r.text
    (root/'synthetic-report.json').write_text(json.dumps(r.json()))
if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,fd=int(os.environ['OUTPUT_ACCEPTANCE_FD']),log_level='error')
