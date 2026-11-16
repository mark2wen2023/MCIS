"""W9.1 synthetic create-only slice; isolated test database."""
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from .conftest import C, H, CASE, make_settings
from .archive_workflow_fixtures import supported_archive_client
from mcis_service.main import create_app
from mcis_service.audit import service as audit
from mcis_service.db import put_doc
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy


def vessel(**extra):
    return {'caseId': CASE, 'vesselId': 'new-ship', 'name': '虚构测试船', **extra}


def test_create_reopen_export_and_audit(supported_archive_client,empty_client):
    client=supported_archive_client
    body=vessel(loaM=123.4,draftForeM=0,mmsi='001234567',parameterSources={'loaM':{'sourceLabel':'虚构资料第2页','kind':'Estimated'}})
    before=client.get(C+'/vessels').json()
    r=client.post(C+'/vessels',json=body,headers=H(operator='测试调查员'))
    assert r.status_code==201,r.text
    assert r.json()==body
    assert client.get(C+'/vessels').json()==before+[body]
    assert client.get(C+'/overview').json()['counts']['vessels']==len(before)+1
    response=client.get(C+'/audit',headers=H('LeadInvestigator'))
    assert response.status_code==200,response.text
    events=response.json();assert isinstance(events,list)
    assert audit.verify_chain([e['line'] for e in events])['valid']
    added=[e for e in events if e['action']=='vessel.create']
    assert len(added)==1 and added[0]['entityId']=='new-ship'
    assert added[0]['operator']=='测试调查员'
    from mcis_service.package.mcase import read_zip
    response=client.get(C+'/export',headers=H('LeadInvestigator'))
    assert response.status_code==200,response.text
    exported=read_zip(response.content)
    assert body in json.loads(exported['vessels.json'])
    restored=empty_client.post('/api/v1/cases:import',content=response.content,headers=H('LeadInvestigator'))
    assert restored.status_code==201,restored.text
    assert empty_client.get(C+'/vessels').json()==before+[body]
    again=empty_client.get(C+'/export',headers=H('LeadInvestigator'))
    assert again.status_code==200,again.text
    assert json.loads(read_zip(again.content)['vessels.json'])==json.loads(exported['vessels.json'])


@pytest.mark.parametrize('role',['LeadInvestigator','Investigator'])
def test_allowed_roles(client,role):
    assert client.post(C+'/vessels',json=vessel(),headers=H(role)).status_code==201


@pytest.mark.parametrize('role',['ExternalExpert','InterestedState','AgentService','Public'])
def test_read_only_roles(client,role):
    assert client.get(C+'/vessels',headers=H(role)).status_code==200
    assert client.post(C+'/vessels',json=vessel(),headers=H(role)).status_code==403
    assert not any(v['vesselId']=='new-ship' for v in client.get(C+'/vessels').json())


@pytest.mark.parametrize('level',['ReadOnly','Redacted','Deny'])
def test_custom_policy_cannot_be_bypassed(client,app,level):
    policy=default_policy();policy['matrix']['Investigator']['ais_sim']=level
    with app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',policy)
    assert client.post(C+'/vessels',json=vessel()).status_code==403


@pytest.mark.parametrize('change',[
    {'name':''},{'name':'  '},{'name':' x '},{'vesselId':' x'},{'vesselId':''},
    {'caseId':'CASE-other'},{'unknown':1},{'mmsi':'123'},{'mmsi':'123456789\n'},
    {'loaM':0},{'loaM':-1},{'beamM':0},{'displacementTons':0},{'draftForeM':-0.01},
    {'loaM':True},{'loaM':'5'},{'loaM':None},
    {'parameterSources':{'loaM':{'sourceLabel':'source','kind':'Direct'}}},
    {'parameterSources':{'name':{'sourceLabel':' ','kind':'Direct'}}},
    {'parameterSources':{'name':{'sourceLabel':'x','kind':'AI'}}},
])
def test_bad_input_no_writes(client,change):
    before=client.get(C+'/overview').json()['counts']
    assert client.post(C+'/vessels',json=vessel(**change)).status_code==422
    assert client.get(C+'/overview').json()['counts']==before


@pytest.mark.parametrize('number',['NaN','Infinity','-Infinity','1e400'])
def test_nonfinite_rejected(client,number):
    body=json.dumps(vessel())[:-1]+',"loaM":'+number+'}'
    assert client.post(C+'/vessels',content=body,headers={'Content-Type':'application/json'}).status_code==422


def test_duplicate_and_concurrent_create_no_overwrite(client):
    with ThreadPoolExecutor(2) as executor:
        codes=list(executor.map(lambda n:client.post(C+'/vessels',json=vessel(name='Ship '+str(n))).status_code,range(2)))
    assert sorted(codes)==[201,409]
    saved=client.get(C+'/vessels').json()
    assert len([v for v in saved if v['vesselId']=='new-ship'])==1
    assert client.post(C+'/vessels',json=vessel(name='Overwrite')).status_code==409
    assert client.get(C+'/vessels').json()==saved


def test_unknown_case(client):
    assert client.post('/api/v1/cases/CASE-missing/vessels',json=vessel(caseId='CASE-missing')).status_code==404


def test_failure_rolls_back_vessel_and_audit(client,monkeypatch):
    before=client.get(C+'/overview').json()['counts']
    def fail(*args,**kwargs):raise RuntimeError('synthetic audit failure')
    monkeypatch.setattr(audit,'append',fail)
    with pytest.raises(RuntimeError):client.post(C+'/vessels',json=vessel())
    assert client.get(C+'/overview').json()['counts']==before


def test_persistence_restart_case_isolation_sources(tmp_path):
    settings=make_settings(tmp_path,False)
    template={
      'schemaVersion':'1.0.0','caseId':'CASE-A','title':'Synthetic test','accidentType':'Collision','caseEpochUtc':'2026-11-12T00:00:00Z','incidentTimeUtc':'2026-11-12T00:00:00Z','incidentLocation':{'lonDeg':0,'latDeg':0},'displayTimeZoneOffsetMinutes':0,'isFictionalDemo':False}
    with TestClient(create_app(settings)) as c:
      for case in ['CASE-A','CASE-B']:
        assert c.post('/api/v1/cases',json={**template,'caseId':case}).status_code==201
      body=vessel(caseId='CASE-A',loaM=10)
      assert c.post('/api/v1/cases/CASE-A/vessels',json=body).status_code==422
      body['parameterSources']={key:{'sourceLabel':'synthetic source, not real evidence','kind':'Direct'} for key in ['name','loaM']}
      assert c.post('/api/v1/cases/CASE-A/vessels',json=body).status_code==201
      assert c.get('/api/v1/cases/CASE-B/vessels').json()==[]
      assert c.post('/api/v1/cases/CASE-B/vessels',json={**body,'caseId':'CASE-B'}).status_code==201
    with TestClient(create_app(settings)) as c:
      assert c.get('/api/v1/cases/CASE-A/vessels').json()==[body]
      assert c.get('/api/v1/cases/CASE-B/vessels').json()==[{**body,'caseId':'CASE-B'}]
