"""Independent W9.1 black-box real-HTTP acceptance; temporary database only."""
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'W82'))
from harness import servers, request, payload

@pytest.fixture()
def api():
    with servers() as (url,_):
        for cid in ['W91-A','W91-B']:
            assert request(url,'/cases',payload(cid))[0]==201
        yield url

def ship(cid='W91-A',**kw):
    return {'caseId':cid,'vesselId':'独立船-1','name':'虚构 <b>船</b>',**kw}


def test_http_two_cases_persistent_records_and_audit(api):
    a=ship(loaM=200.125,draftForeM=0,mmsi='001234567',parameterSources={'loaM':{'sourceLabel':'Independent synthetic source, page 4','kind':'Derived'}})
    assert request(api,'/cases/W91-A/vessels',a)==(201,a)
    assert request(api,'/cases/W91-B/vessels')==(200,[])
    b=ship('W91-B',name='B synthetic')
    assert request(api,'/cases/W91-B/vessels',b)==(201,b)
    assert request(api,'/cases/W91-A/vessels')==(200,[a])
    assert request(api,'/cases/W91-B/vessels')==(200,[b])
    events=request(api,'/cases/W91-A/audit')[1]
    created=[e for e in events if e['action']=='vessel.create']
    assert len(created)==1 and created[0]['entityId']==a['vesselId']
    assert request(api,'/cases/W91-A/vessels',ship(name='overwrite'))[0]==409
    assert request(api,'/cases/W91-A/vessels')==(200,[a])
    assert request(api,'/cases/W91-A/audit')[1]==events

@pytest.mark.parametrize('role',['LeadInvestigator','Investigator','ExternalExpert','InterestedState','AgentService','Public'])
def test_http_roles(api,role):
    code,_=request(api,'/cases/W91-A/vessels',ship(),role)
    assert code==(201 if role in ['LeadInvestigator','Investigator'] else 403)
    assert request(api,'/cases/W91-A/vessels',role=role)[0]==200

@pytest.mark.parametrize('key,value',[
 ('loaM',0),('loaM',-1),('loaM',True),('loaM','10'),('loaM',float('inf')),('loaM',float('nan')),('loaM',10**400),
 ('beamM',-0.0000001),('draftForeM',-0.0000001),('draftAftM',-1),('displacementTons',0),
 ('caseId','W91-B'),('vesselId','  '),('name',''),('name','ship '),('mmsi','123456789\n'),('colorHex','#112233\n'),
 ('parameterSources',{'name':{'sourceLabel':' ','kind':'Direct'}}),
 ('parameterSources',{'beamM':{'sourceLabel':'orphan','kind':'Direct'}}),
 ('parameterSources',{'name':{'sourceLabel':'x','kind':'Invented'}}),
 ('parameterSources',{'anything':{'sourceLabel':'x','kind':'Direct'}}),
])
def test_http_invalid_is_atomic(api,key,value):
    before=request(api,'/cases/W91-A/audit')[1]
    assert request(api,'/cases/W91-A/vessels',ship(**{key:value}))[0]==422
    assert request(api,'/cases/W91-A/vessels')==(200,[])
    assert request(api,'/cases/W91-A/audit')[1]==before

@pytest.mark.parametrize('kind',['Direct','Derived','Estimated'])
def test_http_nonfiction_requires_every_source(api,kind):
    case=payload('W91-real');case['isFictionalDemo']=False
    assert request(api,'/cases',case)[0]==201
    body=ship('W91-real',draftAftM=0)
    endpoint='/cases/W91-real/vessels'
    assert request(api,endpoint,body)[0]==422
    body['parameterSources']={'name':{'sourceLabel':'Synthetic fixture name source','kind':kind}}
    assert request(api,endpoint,body)[0]==422
    body['parameterSources']['draftAftM']={'sourceLabel':'Synthetic fixture draft source','kind':kind}
    assert request(api,endpoint,body)==(201,body)
    assert request(api,endpoint)==(200,[body])

def test_http_unknown_case_no_fallback(api):
    assert request(api,'/cases/W91-missing/vessels',ship('W91-missing'))[0]==404
    assert request(api,'/cases/W91-A/vessels')==(200,[])
