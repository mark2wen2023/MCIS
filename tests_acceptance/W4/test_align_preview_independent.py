"""Independent W4.1 TestClient/temp SQLite; real DLL test is explicitly separate."""
import copy
from pathlib import Path
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'service'))
from mcis_service.config import Settings
from mcis_service.main import create_app
from mcis_service.timeline import align_preview as module
from mcis_service.colreg.core_client import CoreError
from mcis_service.db import put_doc
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from align_preview_negative_cases import forbidden_payloads
A='CASE-2026-DEMO-LILY-MARY';B='CASE-2025-HAILI5-WANA17'
H={'X-MCIS-Role':'Investigator'}
SOURCE={'sourceId':'A','text':'t,h\n2026-05-18T06:20:00Z,10\n2026-05-18T06:21:00Z,10', 'csvMapping':{'timeColumn':'t','columns':[{'column':'h','kind':'Heading'}]}}
BODY={'sources':[SOURCE]}
def url(case=A):return f'/api/v1/cases/{case}/timeline/align-preview'
def snap(c):
    with c.app.state.db.engine.connect() as conn:
        names=conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")).scalars()
        return {n:sorted(repr(tuple(r)) for r in conn.execute(text(f'SELECT * FROM "{n}"'))) for n in names}
@pytest.fixture()
def client(tmp_path):
    app=create_app(Settings(data_dir=tmp_path,db_url=f'sqlite:///{tmp_path}/test.db',seed_demo=True))
    with TestClient(app) as c:yield c

def envelope(p):
    return {'ok':True,'command':'align','result':{'caseId':p['caseId'],'caseEpochUtc':p['caseEpochUtc'],'conflicts':[],'clockOffsets':[], 'calibration':{'allCalibrated':False,'uncalibratedSources':['A'],'sources':[]},'importDiagnostics':[],'conflictDiagnostics':[], 'stats':{k:0 for k in ['sourcesImported','tracks','linesRead','sentencesUsed','anchorCount','manualAnchorCount']}}}
@pytest.fixture()
def spy(monkeypatch):
    calls=[]
    def run(cmd,command,p,timeout):
        calls.append(copy.deepcopy(p));assert command=='align';return envelope(p)
    monkeypatch.setattr(module,'core_run',run);return calls

def test_canary_all_nested_forbidden_fields(client,spy,tmp_path):
    canary=tmp_path/'harmless.csv';canary.write_text('not sensitive canary')
    before=snap(client)
    for name,body in forbidden_payloads(BODY,str(canary)):
        r=client.post(url(),json=body,headers=H)
        assert r.status_code==422,(name,r.text)
    assert spy==[] and snap(client)==before and canary.read_text()=='not sensitive canary'

@pytest.mark.parametrize('role',['LeadInvestigator','Investigator','ExternalExpert','InterestedState','AgentService','Public'])
def test_default_roles(client,spy,role):
    before=snap(client);r=client.post(url(),json=BODY,headers={'X-MCIS-Role':role})
    assert r.status_code==(403 if role=='Public' else 200),r.text
    assert len(spy)==(0 if role=='Public' else 1) and snap(client)==before

def test_per_case_policy_epoch_and_payload(client,spy):
    for case,level in [(A,'Deny'),(B,'ReadOnly')]:
        policy=default_policy();policy['matrix']['ExternalExpert']['timeline']=level
        with client.app.state.db.session() as s:put_doc(s,AccessPolicyRow,case,'policy',policy)
    before=snap(client);headers={'X-MCIS-Role':'ExternalExpert'}
    assert client.post(url(A),json=BODY,headers=headers).status_code==403
    r=client.post(url(B),json=BODY,headers=headers);assert r.status_code==200,r.text
    p=spy[0];stored=client.get(f'/api/v1/cases/{B}/timeline',headers=H).json()
    assert p['caseId']==B and p['caseEpochUtc']==stored['caseEpochUtc']
    assert r.json()['caseId']==B and r.json()['caseEpochUtc']==stored['caseEpochUtc']
    expected={'caseId':B,'caseEpochUtc':stored['caseEpochUtc'],'calibrate':True,'referenceSourceId':'GNSS','offsetMethod':'Median','sources':[{'sourceId':'A','text':SOURCE['text'],'format':'csv','csvMapping':{'timeColumn':'t','delimiter':',','timeZoneOffsetHours':0,'columns':[{'column':'h','kind':'Heading','scale':1,'offset':0,'markChanges':False}]}}]}
    assert p==expected and snap(client)==before

def test_unknown_case_and_role_no_core(client,spy):
    assert client.post(url('NO-SUCH-CASE'),json=BODY,headers=H).status_code==404
    assert client.post(url(),json=BODY,headers={'X-MCIS-Role':'Unknown'}).status_code==400
    assert spy==[]

@pytest.mark.parametrize('mode',['bytes','ascii','id','column','columns','sources','kind','type'])
def test_limits_reject_before_core(client,spy,mode):
    b=copy.deepcopy(BODY);s=b['sources'][0]
    if mode=='bytes':s['text']='中'*87382
    if mode=='ascii':s['text']='x'*262145
    if mode=='id':s['sourceId']='a'*65
    if mode=='column':s['csvMapping']['columns'][0]['column']='a'*129
    if mode=='columns':s['csvMapping']['columns']*=17
    if mode=='sources':b['sources']=[{**s,'sourceId':str(i)} for i in range(5)]
    if mode=='kind':s['csvMapping']['columns'][0]['kind']='Position'
    if mode=='type':s['sourceId']=123
    before=snap(client);r=client.post(url(),json=b,headers=H)
    assert r.status_code==422 and spy==[] and snap(client)==before

def test_exact_limits_accept_and_utf8_bytes(client,spy):
    s=copy.deepcopy(SOURCE);s['text']='中'*87381+'x';assert len(s['text'].encode())==262144
    s['csvMapping']['timeColumn']='t'*128;s['csvMapping']['columns']=[{'column':'h'*128,'kind':'Heading'}]*16
    body={'sources':[{**s,'sourceId':str(i)+'a'*63} for i in range(4)]}
    before=snap(client);r=client.post(url(),json=body,headers=H)
    assert r.status_code==200,r.text
    assert len(spy)==1 and snap(client)==before

@pytest.mark.parametrize('mode',['case','epoch','conflictcase','missing','extra','command','nan'])
def test_corrupt_output_rejected(client,monkeypatch,mode):
    def run(*args):
        e=envelope(args[2]);r=e['result']
        if mode=='case':r['caseId']=B
        if mode=='epoch':r['caseEpochUtc']='1900-01-01T00:00:00Z'
        if mode=='conflictcase':
            c=copy.deepcopy(client.get(f'/api/v1/cases/{A}/conflicts',headers=H).json()[0]);c['caseId']=B;r['conflicts']=[c]
        if mode=='missing':del r['stats']
        if mode=='extra':r['path']='/harmless/internal'
        if mode=='command':e['command']='version'
        if mode=='nan':r['stats']['tracks']=float('nan')
        return e
    monkeypatch.setattr(module,'core_run',run);before=snap(client)
    response=client.post(url(),json=BODY,headers=H)
    assert response.status_code==502 and response.json()['code']=='ALIGN_PREVIEW_BAD_OUTPUT'
    assert snap(client)==before

@pytest.mark.parametrize('code,status',[('BAD_REQUEST',422),('CORE_TIMEOUT',504),('CORE_UNAVAILABLE',503),('untrusted/path',502)])
def test_safe_errors_no_persistence(client,monkeypatch,code,status):
    def fail(*args):raise CoreError(code,'/canary/private stderr sentinel')
    monkeypatch.setattr(module,'core_run',fail);before=snap(client)
    r=client.post(url(),json=BODY,headers=H)
    assert r.status_code==status and 'canary' not in r.text and 'stderr' not in r.text and 'untrusted' not in r.text
    assert snap(client)==before

def test_real_dll_heading_conflict_uncalibrated_and_error(client):
    before=snap(client);b=copy.deepcopy(BODY)
    b['sources'].append({**copy.deepcopy(SOURCE),'sourceId':'B','text':SOURCE['text'].replace(',10',',15')})
    r=client.post(url(),json=b,headers=H);assert r.status_code==200,r.text
    d=r.json();assert d['previewOnly'] is True and d['persisted'] is False
    assert d['result']['conflicts'][0]['delta']==5 and d['result']['conflicts'][0]['caseId']==A
    assert d['result']['calibration']['allCalibrated'] is False and d['result']['clockOffsets']==[]
    b['sources'][0]['csvMapping']['timeColumn']='absent'
    r=client.post(url(),json=b,headers=H);assert r.status_code==422,r.text
    assert snap(client)==before

def test_contract_schema_strict_nested_and_live_route(client,tmp_path):
    from mcis_service.common import contracts
    assert contracts.errors('align-preview#/$defs/request',BODY)==[]
    for name,b in forbidden_payloads(BODY,str(tmp_path/'canary.csv')):
        assert contracts.errors('align-preview#/$defs/request',b),name
    spec=client.app.openapi()
    path='/api/v1/cases/{case_id}/timeline/align-preview'
    op=spec['paths'][path]['post']
    ref=op['requestBody']['content']['application/json']['schema']['$ref'].split('/')[-1]
    schemas=spec['components']['schemas']
    assert schemas[ref]['additionalProperties'] is False
    for name in ['PreviewRequest','PreviewSource','PreviewMapping','PreviewColumn']:
        assert schemas[name]['additionalProperties'] is False
    assert schemas['PreviewRequest']['properties']['sources']['maxItems']==4
    assert schemas['PreviewMapping']['properties']['columns']['maxItems']==16
    # UTF8 budgets and unique source IDs are semantic validators, not JSON Schema built-ins.
    import json
    contract=json.loads((ROOT/'contracts/schemas/align-preview.schema.json').read_text())
    assert contract['$defs']['request']['properties']['sources']['maxItems']==4
    assert contract['$defs']['response']['properties']['result']==contract['$defs']['result']
