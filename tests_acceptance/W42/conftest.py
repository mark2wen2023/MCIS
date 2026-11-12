"""Independent synthetic fixtures; no implementation self-test imports."""
import base64
import hashlib
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from mcis_service.config import Settings
from mcis_service.main import create_app
CASE='W42-SYNTHETIC'
C=f'/api/v1/cases/{CASE}'
H={'X-MCIS-Role':'Investigator','X-MCIS-Operator':'Independent-Operator'}
CASE_DOC={'caseId':CASE,'schemaVersion':'1.0.0','title':'W42 synthetic acceptance only','accidentType':'Collision','incidentTimeUtc':'2020-01-01T00:00:00Z','caseEpochUtc':'2020-01-01T00:00:00Z','displayTimeZoneOffsetMinutes':0,'incidentLocation':{'latDeg':0,'lonDeg':0},'isFictionalDemo':True}
def application(root):
    return create_app(Settings(data_dir=root,db_url=f'sqlite:///{root}/acceptance.db',seed_demo=False))
@pytest.fixture
def env(tmp_path):
    app=application(tmp_path)
    with TestClient(app,raise_server_exceptions=False) as client:
        r=client.post('/api/v1/cases',json=CASE_DOC,headers=H)
        assert r.status_code==201,r.text
        yield app,client,tmp_path
    app.state.db.engine.dispose()
def payload(raw=b'\x00\xff\xfe\x80\r\n<script>not executed</script>'):
    return dict(profile='mcis-evidence-intake-v1',fileName='synthetic.bin',title='  原文 <script>alert(1)</script>  ',source='原来源\n移交方式\t合成',extractedBy=' 声明提取人 ',extractedUtc='2001-02-03T04:05:06Z',category='Other',confidentiality='Restricted',note='原登记备注\n☎ 13800000000',contentBase64=base64.b64encode(raw).decode())
def snapshot(env):
    app,_,root=env
    with app.state.db.engine.connect() as conn:
        tables={name:conn.execute(text(f'SELECT * FROM {name} ORDER BY id')).fetchall() for name in ('evidence_items','custody_events','audit_events')}
    files={str(p.relative_to(root/'blobs')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'blobs').rglob('*') if p.is_file()}
    return tables,files

def preview(client,body,headers=H):
    r=client.post(C+'/evidence-intakes:preview',json=body,headers=headers)
    assert r.status_code==200,r.text
    return r.json()
def commit(client,body,headers=H):
    p=preview(client,body,headers)
    r=client.post(C+'/evidence-intakes:commit',json={**body,'requestDigest':p['requestDigest'],'confirmed':True},headers=headers)
    assert r.status_code==200,r.text
    return r.json()
