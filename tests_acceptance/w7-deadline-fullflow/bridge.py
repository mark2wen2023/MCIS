"""Synthetic test bridge, actual FastAPI handlers, no external server."""
import json
import re
import socket
import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from mcis_service.main import create_app
from tests.conftest import make_settings,H

CASE='SYN-W7-TERM'
ROOT='/api/v1/cases/'+CASE
def prohibited(*args,**kwargs):
    raise AssertionError('network disabled')
settings=make_settings(Path(sys.argv[1]),seed=False)
case=dict(caseId=CASE,title='Synthetic W7 complete flow',schemaVersion='1.0.0',accidentType='Collision',
        incidentTimeUtc='2026-01-01T00:00:00Z',caseEpochUtc='2026-01-01T00:00:00Z',
        incidentLocation={'latDeg':0,'lonDeg':0},displayTimeZoneOffsetMinutes=0,isFictionalDemo=True)
with patch.object(socket.socket,'connect',prohibited),patch.object(socket.socket,'connect_ex',prohibited),patch.object(socket,'getaddrinfo',prohibited):
    app=create_app(settings)
    client=TestClient(app)
    head=H('LeadInvestigator','Synthetic local W7')
    r=client.post('/api/v1/cases',headers=head,json=case)
    assert r.status_code==201,r.text
    for line in sys.stdin:
        inp=json.loads(line);seq=inp.pop('seq')
        if inp.get('command')=='reopen':
            client.close(); app.state.db.engine.dispose();app=create_app(settings);client=TestClient(app)
            out={'seq':seq,'status':200,'body':None}
        else:
            path=inp['path']; method=inp['method']
            assert path.startswith(ROOT) and re.fullmatch(r'^(|/(audit(?::verify)?(?:\?.*)?|access-policy|recommendations[\w:/-]*|consultation/rounds[\w:/-]*))$',path[len(ROOT):]),path
            assert method in ('GET','POST','PATCH')
            r=client.request(method,path,headers=inp['headers'],**({'json':inp['body']} if 'body' in inp else {}))
            out={'seq':seq,'status':r.status_code,'body':r.json()}
        print(json.dumps(out),flush=True)
    client.close(); app.state.db.engine.dispose()
