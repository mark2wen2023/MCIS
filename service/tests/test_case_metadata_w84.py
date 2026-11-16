"""Synthetic case text edits; no mutation of source reports."""
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from .conftest import CASE, C, H, make_settings
from .archive_workflow_fixtures import supported_archive_client
from mcis_service.main import create_app
from mcis_service.audit import service as audit
from mcis_service.common import contracts
from mcis_service.db import put_doc
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy

URL=C+'/metadata'


def request(client,changes=None,**kw):
    return {'operationId':'op-one','expectedRevision':client.get(URL).json()['revision'],
            'changes':{'title':'虚构测试档案修订'} if changes is None else changes,
            'sourceLabel':'虚构资料 p.2','changeReason':'修正测试文字',**kw}


def test_read_update_audit_original_and_roundtrip(supported_archive_client,empty_client):
    client=supported_archive_client
    original=client.get(C).json();before=client.get(URL).json()
    assert before['case']==original and before['lastChange'] is None
    frozen={key:client.get(C+key).json() for key in ['/vessels','/tracks','/evidence','/environment-observations']}
    body=request(client,{'title':'虚构测试修订','placeName':' 某测试水域 ','leadInvestigator':'测试角色',
      'agencyName':'合成调查组','summaryNotes':'第一行\n'+'测试长文本'*1000})
    r=client.patch(URL,json=body,headers=H(operator='合成测试者'));assert r.status_code==200,r.text
    saved=r.json();contracts.validate('case-metadata#/$defs/snapshot',saved)
    assert saved['revision']!=before['revision']
    assert saved['lastChange']['operationId']=='op-one' and saved['lastChange']['sourceLabel']==body['sourceLabel']
    assert saved['lastChange']['operator']=='合成测试者'
    assert all(saved['case'][k]==v for k,v in body['changes'].items())
    assert {k:v for k,v in original.items() if k not in body['changes']}=={k:v for k,v in saved['case'].items() if k not in body['changes']}
    for key,value in frozen.items():assert client.get(C+key).json()==value
    response=client.get(C+'/audit',headers=H('LeadInvestigator'))
    assert response.status_code==200,response.text
    events=response.json();assert isinstance(events,list)
    event=next(x for x in events if x['action']=='case.metadata.update')
    reason=json.loads(json.loads(event['line'])['reason'])
    assert reason['after']['summaryNotes']['value']==body['changes']['summaryNotes']
    assert reason['before']['title']=={'present':True,'value':original['title']}
    assert audit.verify_chain([e['line'] for e in events])['valid']
    response=client.get(C+'/export',headers=H('LeadInvestigator'))
    assert response.status_code==200,response.text
    data=response.content
    r=empty_client.post('/api/v1/cases:import',content=data,headers=H('LeadInvestigator'));assert r.status_code==201,r.text
    assert empty_client.get(URL).json()==saved


@pytest.mark.parametrize('role',['LeadInvestigator','Investigator'])
def test_writers(client,role):
    assert client.patch(URL,json=request(client),headers=H(role)).status_code==200


@pytest.mark.parametrize('role',['ExternalExpert','InterestedState','AgentService','Public'])
def test_readers_not_writers(client,role):
    assert client.get(URL,headers=H(role)).status_code==200
    assert client.patch(URL,json=request(client),headers=H(role)).status_code==403


@pytest.mark.parametrize('level',['ReadOnly','Redacted','Deny'])
def test_case_policy(client,app,level):
    body=request(client);policy=default_policy();policy['matrix']['Investigator']['ais_sim']=level
    with app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',policy)
    assert client.get(URL).status_code==(200 if level=='ReadOnly' else 403)
    assert client.patch(URL,json=body).status_code==403


@pytest.mark.parametrize('field',['caseId','schemaVersion','incidentTimeUtc','caseEpochUtc','displayTimeZoneOffsetMinutes',
    'incidentLocation','seaLevelOffsetM','accidentType','accidentGrade','isFictionalDemo','durationSec','accidentCode','unknown'])
def test_immutable_fields_rejected(client,field):
    before=client.get(URL).json();r=client.patch(URL,json=request(client,{field:'tamper'}))
    assert r.status_code==422 and client.get(URL).json()==before


@pytest.mark.parametrize('extra',[
 {'changes':{}},{'changes':{'title':None}},{'changes':{'title':' '}},{'changes':{'title':True}},
 {'changes':{'summaryNotes':' '}},{'changes':{'title':'x'*501}},{'changes':{'summaryNotes':'x'*20001}},
 {'sourceLabel':''},{'sourceLabel':'\t'},{'changeReason':' '},{'expectedRevision':'bad'},
 {'expectedRevision':'0'*64+'\n'},{'operationId':' '},{'operationId':'x\n'},
 {'operationId':'x'*65},{'unknown':1},
])
def test_bad_input_atomic(client,extra):
    before=client.get(URL).json();count=len(client.get(C+'/audit').json())
    assert client.patch(URL,json=request(client,**extra)).status_code==422
    assert client.get(URL).json()==before and len(client.get(C+'/audit').json())==count


def test_noop_and_clear_optional(client):
    current=client.get(URL).json()
    body=request(client,{'title':current['case']['title']})
    assert client.patch(URL,json=body).status_code==422
    original=current['case'].get('placeName')
    body=request(client,{'placeName':None})
    if original is not None:
        r=client.patch(URL,json=body);assert r.status_code==200,r.text
        assert 'placeName' not in r.json()['case']
    assert client.patch(URL,json=request(client,{'placeName':None},operationId='new-op')).status_code==422


def test_stale_and_concurrent_never_overwrite(client):
    body=request(client)
    with ThreadPoolExecutor(2) as pool:
        results=list(pool.map(lambda n:client.patch(URL,json={**body,'operationId':'parallel-'+str(n),
            'changes':{'title':'合成 '+str(n)}}).status_code,range(2)))
    assert sorted(results)==[200,409]
    saved=client.get(URL).json()
    assert client.patch(URL,json=body).status_code==409
    assert client.get(URL).json()==saved


def test_aba_and_operation_reuse(client):
    original=client.get(URL).json();a=request(client,{'title':'合成 B'})
    assert client.patch(URL,json=a).status_code==200
    b=request(client,{'title':original['case']['title']},operationId='op-two')
    assert client.patch(URL,json=b).status_code==200
    assert client.get(URL).json()['case']==original['case']
    assert client.get(URL).json()['revision']!=original['revision']
    assert client.patch(URL,json={**a,'operationId':'op-three'}).status_code==409
    reuse=request(client,{'title':'合成 C'})
    assert client.patch(URL,json=reuse).status_code==409


def test_audit_failure_rolls_back(client,monkeypatch):
    before=client.get(URL).json();body=request(client)
    def fail(*a,**kw):raise RuntimeError('synthetic audit failure')
    monkeypatch.setattr(audit,'append',fail)
    with pytest.raises(RuntimeError):client.patch(URL,json=body)
    assert client.get(URL).json()==before


def test_case_isolation_and_restart_long_ids(tmp_path):
    st=make_settings(tmp_path,False);ids=['CASE-'+('a'*100),'CASE-other']
    template={'schemaVersion':'1.0.0','title':'Synthetic','accidentType':'Collision',
      'caseEpochUtc':'2026-01-01T00:00:00Z','incidentTimeUtc':'2026-01-01T00:00:00Z',
      'incidentLocation':{'lonDeg':0,'latDeg':0},'displayTimeZoneOffsetMinutes':0,'isFictionalDemo':True}
    path='/api/v1/cases/'+ids[0]+'/metadata'
    with TestClient(create_app(st)) as c:
        for cid in ids:assert c.post('/api/v1/cases',json={**template,'caseId':cid}).status_code==201
        snap=c.get(path).json();body={'operationId':'restart','expectedRevision':snap['revision'],
          'changes':{'title':'Synthetic revised'},'sourceLabel':'Synthetic input','changeReason':'Test only'}
        r=c.patch(path,json=body);assert r.status_code==200;r_saved=r.json()
        assert c.get('/api/v1/cases/'+ids[1]+'/metadata').json()['case']['title']=='Synthetic'
        assert c.patch('/api/v1/cases/'+ids[1]+'/metadata',json=body).status_code==409
    with TestClient(create_app(st)) as c:
        assert c.get(path).json()==r_saved
        assert c.get('/api/v1/cases/missing/metadata').status_code==404
