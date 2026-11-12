"""Loopback-only synthetic application fixture with isolated SQLite database."""
import json
import os
import socket
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'service'))
from fastapi.testclient import TestClient
from mcis_service.config import Settings
from mcis_service.main import create_app
from mcis_service.db import put_doc
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
import uvicorn
run=Path(os.environ['MCIS_W92_RUN_DIR'])
app=create_app(Settings(data_dir=run/'data',seed_demo=False))
with TestClient(app) as client:
    for name in ['A','B','REDACTED']:
        cid='CASE-W92-'+name
        doc={'caseId':cid,'schemaVersion':'1.0.0','title':'虚构环境验收 '+name,'accidentType':'Collision',
             'incidentTimeUtc':'2024-01-01T00:00:00Z','caseEpochUtc':'2024-01-01T00:00:00Z',
             'displayTimeZoneOffsetMinutes':0,'incidentLocation':{'lonDeg':0,'latDeg':0},'isFictionalDemo':True}
        response=client.post('/api/v1/cases',json=doc);assert response.status_code==201,response.text
    policy=default_policy();policy['matrix']['Investigator']['ais_sim']='Redacted'
    with app.state.db.session() as s:put_doc(s,AccessPolicyRow,'CASE-W92-REDACTED','policy',policy)
sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
(run/'session.json').write_text(json.dumps({'api':f'http://127.0.0.1:{port}'}))
uvicorn.run(app,host='127.0.0.1',port=port,log_level='warning')
