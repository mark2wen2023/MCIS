import copy
import pytest
from .conftest import C, H, HAS_DOTNET
from mcis_service.timeline import align_preview as preview
from mcis_service.colreg.core_client import CoreError

URL=f'{C}/timeline/align-preview'
SOURCE={'sourceId':'A','text':'time,cog\n2026-05-18T06:20:00Z,45\n2026-05-18T06:21:00Z,45',
        'csvMapping':{'timeColumn':'time','columns':[{'column':'cog','kind':'CourseOverGround'}]}}
BODY={'sources':[SOURCE]}

def result(payload):
    return {'ok':True,'command':'align','result':{'caseId':payload['caseId'],
        'conflicts':[],'clockOffsets':[],'calibration':{'allCalibrated':False,'uncalibratedSources':['A'],'sources':[],'error':'no anchors'},
        'importDiagnostics':[],'conflictDiagnostics':[],'stats':{k:0 for k in ['sourcesImported','tracks','linesRead','sentencesUsed','anchorCount','manualAnchorCount']}}}

@pytest.mark.parametrize('where,key', [('root','path'),('root','caseId'),('root','caseEpochUtc'),('root','command'),('root','manualAnchors'),('source','path'),('source','format'),('mapping','path'),('column','path')])
def test_unknown_rejected_before_core(client,monkeypatch,where,key):
    body=copy.deepcopy(BODY)
    node={'root':body,'source':body['sources'][0],'mapping':body['sources'][0]['csvMapping'],'column':body['sources'][0]['csvMapping']['columns'][0]}[where]
    node[key]=None
    monkeypatch.setattr(preview,'core_run',lambda *a:pytest.fail('must not invoke core'))
    assert client.post(URL,json=body,headers=H()).status_code==422

@pytest.mark.parametrize('role', ['Investigator','LeadInvestigator','ExternalExpert','InterestedState','AgentService','Public'])
def test_role_payload_and_no_persistence(client,monkeypatch,role):
    seen=[]
    def run(cmd,command,payload,timeout):
        seen.append(payload)
        assert command=='align' and payload['caseId']==C.split('/')[-1]
        assert payload['sources'][0]['format']=='csv'
        assert payload['sources'][0]['csvMapping']['timeZoneOffsetHours']==0
        return result(payload)
    monkeypatch.setattr(preview,'core_run',run)
    before=[client.get(C+x,headers=H()).json() for x in ['/audit','/conflicts','/timeline']]
    r=client.post(URL,json=BODY,headers=H(role))
    assert r.status_code==(403 if role=='Public' else 200),r.text
    assert bool(seen)==(role!='Public')
    assert [client.get(C+x,headers=H()).json() for x in ['/audit','/conflicts','/timeline']]==before

@pytest.mark.parametrize('code,status', [('CORE_NO_OUTPUT',502),('CORE_TIMEOUT',504),('CORE_UNAVAILABLE',503),('BAD_REQUEST',422),('unknown/private',502)])
def test_error_redaction(client,monkeypatch,code,status):
    def fail(*a):raise CoreError(code,'secret /home/private/password')
    monkeypatch.setattr(preview,'core_run',fail)
    r=client.post(URL,json=BODY,headers=H())
    assert r.status_code==status and 'private' not in r.text and 'password' not in r.text

@pytest.mark.parametrize('change', ['case','epoch','nan','missing'])
def test_output_validation(client,monkeypatch,change):
    def bad(*args):
        env=result(args[2]);r=env['result']
        if change=='case':r['caseId']='other'
        if change=='epoch':r['caseEpochUtc']='2020-01-01T00:00:00Z'
        if change=='nan':r['stats']['tracks']=float('nan')
        if change=='missing':del r['calibration']
        return env
    monkeypatch.setattr(preview,'core_run',bad)
    r=client.post(URL,json=BODY,headers=H())
    assert r.status_code==502 and r.json()['code']=='ALIGN_PREVIEW_BAD_OUTPUT'

@pytest.mark.parametrize('body', [ {'sources':[SOURCE]*5}, {'sources':[SOURCE,SOURCE]}, {'sources':[{**SOURCE,'text':'中'*87382}]}, {'sources':[{**SOURCE,'sourceId':123}]}, {'sources':[{**SOURCE,'csvMapping':{'timeColumn':'time','columns':[{'column':'cog','kind':'Position'}]}}]} ])
def test_limits_types(client,monkeypatch,body):
    monkeypatch.setattr(preview,'core_run',lambda *a:pytest.fail('no core'))
    assert client.post(URL,json=body,headers=H()).status_code==422

@pytest.mark.skipif(not HAS_DOTNET,reason='real CLI SDK required')
def test_real_cli_csv_preview(client):
    b=copy.deepcopy(BODY);b['sources'].append({**SOURCE,'sourceId':'B','text':SOURCE['text'].replace(',45',',50')})
    r=client.post(URL,json=b,headers=H())
    assert r.status_code==200,r.text
    data=r.json();assert data['previewOnly'] and not data['persisted']
    assert data['result']['conflicts'][0]['delta']==5
    assert data['result']['calibration']['allCalibrated'] is False
