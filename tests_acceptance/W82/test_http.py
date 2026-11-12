"""Run with service/.venv/bin/pytest; actual localhost sockets, no TestClient/mock."""
import uuid
import pytest
from harness import servers,request,payload
@pytest.fixture(scope='module')
def api():
    with servers() as (base,_):yield base
@pytest.mark.parametrize('role',['LeadInvestigator','Investigator'])
def test_create_list_metadata_evidence_and_single_audit(api,role):
    body=payload('W82-'+role)
    assert request(api,'/cases',body,role)==(201,body)
    status,listing=request(api,'/cases'); assert status==200
    row=next(c for c in listing if c['caseId']==body['caseId'])
    assert all(row[k]==body[k] for k in body if k in row)
    p='/cases/'+body['caseId']
    assert request(api,p)==(200,body)
    for endpoint in ['/evidence','/conflicts','/vessels']:
        assert request(api,p+endpoint)==(200,[])
    assert request(api,p+'/tracks')==(200,{'caseId':body['caseId'],'tracks':[]})
    status,tl=request(api,p+'/timeline'); assert status==200 and tl['events']==[] and tl['durationSec'] is None and tl['caseEpochUtc']==body['caseEpochUtc']
    status,chain=request(api,p+'/custody:verify-chain'); assert status==200
    status,events=request(api,p+'/audit'); assert status==200 and len(events)==1 and events[0]['action']=='case.create'
    assert events[0]['role']==role and events[0]['operator']=='W82-independent'
    altered={**body,'title':'must not overwrite'}
    assert request(api,'/cases',altered,role)[0]==409
    assert request(api,p)==(200,body)
    assert len(request(api,p+'/audit')[1])==1
@pytest.mark.parametrize('role',['ExternalExpert','InterestedState','AgentService','Public'])
def test_roles_rejected_without_creation(api,role):
    b=payload('W82-denied-'+role)
    assert request(api,'/cases',b,role)[0]==403
    assert request(api,'/cases/'+b['caseId'])[0]==404
@pytest.mark.parametrize('change',[{'caseId':'ab'},{'caseId':'bad/route'},{'title':''},{'incidentLocation':{'latDeg':90.00001,'lonDeg':0}},{'incidentLocation':{'latDeg':0,'lonDeg':-180.00001}},pytest.param({'incidentTimeUtc':'not-date'},marks=pytest.mark.xfail(strict=True,reason='Existing API schema validator does not enforce date-time format; W82 UI must reject it')),{'isFictionalDemo':'false'},{'extra':'forbidden'}])
def test_schema_rejects_invalid(api,change):
    case_id='W82-invalid-'+uuid.uuid4().hex
    b={**payload(case_id),**change}
    assert request(api,'/cases',b)[0]==422
    assert request(api,'/cases/'+case_id)[0]==404
