"""Independent synthetic contract tests, no production or public-report edits."""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

import pytest
import yaml
from fastapi.testclient import TestClient
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'service'))
from mcis_service.config import Settings
from mcis_service.main import create_app
from mcis_service.db import put_doc
from mcis_service.audit import service as audit
from mcis_service.cases.models import VesselRow,TrackPointRow
from mcis_service.environment.models import EnvironmentObservationRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy

CID='CASE-ACCEPT-W84-A'
P='/api/v1/cases/'+CID
U=P+'/metadata'


def seed_case(cid):
    return {'caseId':cid,'schemaVersion':'1.0.0','title':'虚构独立验收原名','accidentType':'Collision',
      'accidentGrade':'SyntheticClass','caseEpochUtc':'2024-01-01T00:00:00Z',
      'incidentTimeUtc':'2024-01-01T00:02:00Z','incidentLocation':{'lonDeg':1,'latDeg':2,'heightM':3},
      'displayTimeZoneOffsetMinutes':480,'isFictionalDemo':True,'placeName':'虚构水域',
      'seaLevelOffsetM':5,'durationSec':120,'summaryNotes':'既有合成说明'}


@pytest.fixture
def env(tmp_path):
    settings=Settings(data_dir=tmp_path/'db',seed_demo=False)
    app=create_app(settings)
    with TestClient(app) as c:
        for cid in [CID,'CASE-ACCEPT-W84-B']:
            r=c.post('/api/v1/cases',json=seed_case(cid));assert r.status_code==201
        yield c,app,settings


def read(c,cid=CID):return c.get('/api/v1/cases/'+cid+'/metadata').json()
def body(c,changes=None,op='accept-op',**kwargs):
    return {'operationId':op,'expectedRevision':read(c)['revision'],
      'changes':{'title':'虚构独立验收新名'} if changes is None else changes,
      'sourceLabel':'合成来源，不是真实资料','changeReason':'独立验证修改理由',**kwargs}


def test_full_text_audit_clear_roundtrip(env,tmp_path):
    c,app,settings=env;initial=read(c)
    changes={'title':' 原文新标题 ','placeName':None,'leadInvestigator':'合成调查员',
      'agencyName':'合成机构','summaryNotes':'长文\n'+'\U0001f30a'*10000}
    b=body(c,changes,sourceLabel=' 来源原文\n第二行 ',changeReason=' 理由原文\n第二行 ')
    r=c.patch(U,json=b);assert r.status_code==200,r.text
    saved=r.json();assert saved['case']['title']==changes['title'] and 'placeName' not in saved['case']
    assert saved['lastChange']['sourceLabel']==b['sourceLabel'] and saved['lastChange']['changeReason']==b['changeReason']
    events=c.get(P+'/audit').json();ev=[e for e in events if e['action']=='case.metadata.update'][0]
    data=json.loads(json.loads(ev['line'])['reason'])
    assert data['after']['summaryNotes']['value']==changes['summaryNotes']
    assert data['before']['placeName']=={'present':True,'value':'虚构水域'}
    assert data['after']['placeName']=={'present':False,'value':None}
    assert audit.verify_chain([e['line'] for e in events])['valid']
    package=c.get(P+'/export').content
    other=create_app(Settings(data_dir=tmp_path/'other',seed_demo=False))
    with TestClient(other) as d:
        assert d.post('/api/v1/cases:import',content=package).status_code==201
        restored=read(d)
        for key in changes:
            assert restored['case'].get(key)==saved['case'].get(key)
        for key,value in initial['case'].items():
            if key not in changes:assert restored['case'][key]==value
        assert restored['case']['accidentCode']==''  # Existing case.json normalization, not invented fact.
        assert restored['lastChange']==saved['lastChange']
        assert restored['revision']!=saved['revision']
        stale={**b,'operationId':'after-import','expectedRevision':saved['revision'],'changes':{'title':'Should reject'}}
        assert d.patch(U,json=stale).status_code==409
        latest=next(e for e in d.get(P+'/audit').json() if e['action']=='case.metadata.update')
        assert json.loads(latest['line'])['reason']==json.loads(ev['line'])['reason']
    assert initial['revision']!=saved['revision']


@pytest.mark.parametrize('role',['LeadInvestigator','Investigator','ExternalExpert','InterestedState','AgentService','Public'])
def test_roles(env,role):
    c,_,_=env;b=body(c);h={'X-MCIS-Role':role}
    assert c.get(U,headers=h).status_code==200
    assert c.patch(U,json=b,headers=h).status_code==(200 if role in ('LeadInvestigator','Investigator') else 403)


@pytest.mark.parametrize('level',['ReadOnly','Redacted','Deny'])
def test_case_override(env,level):
    c,app,_=env;b=body(c);policy=default_policy();policy['matrix']['Investigator']['ais_sim']=level
    with app.state.db.session() as s:put_doc(s,AccessPolicyRow,CID,'policy',policy)
    assert c.get(U).status_code==(200 if level=='ReadOnly' else 403)
    assert c.patch(U,json=b).status_code==403


@pytest.mark.parametrize('name',['caseId','schemaVersion','accidentType','accidentGrade','incidentTimeUtc',
 'caseEpochUtc','incidentLocation','displayTimeZoneOffsetMinutes','seaLevelOffsetM','durationSec','isFictionalDemo','accidentCode'])
def test_locked_fields(env,name):
    c,_,_=env;before=read(c);b=body(c,{name:seed_case(CID).get(name)})
    assert c.patch(U,json=b).status_code==422
    assert read(c)==before


@pytest.mark.parametrize('mutation',[
 {'changes':{}},{'changes':{'title':None}},{'changes':{'title':'\n\t'}},{'changes':{'title':42}},
 {'changes':{'placeName':''}},{'changes':{'summaryNotes':'x'*20001}},
 {'sourceLabel':' '},{'changeReason':'\n'},{'expectedRevision':'a'*64+'\n'},
 {'operationId':'bad/id'},{'operationId':'x\n'},{'intruder':'x'},
])
def test_invalid_is_atomic(env,mutation):
    c,_,_=env;before=read(c);a=c.get(P+'/audit').json()
    assert c.patch(U,json={**body(c),**mutation}).status_code==422
    assert read(c)==before and c.get(P+'/audit').json()==a


def test_noop_and_optional_missing(env):
    c,_,_=env;before=read(c)
    assert c.patch(U,json=body(c,{'title':before['case']['title']})).status_code==422
    assert c.patch(U,json=body(c,{'agencyName':None})).status_code==422
    assert read(c)==before


def test_concurrency_aba_operation_id_and_lost_reply(env):
    c,_,_=env;start=read(c);b=body(c)
    with ThreadPoolExecutor(2) as pool:
        result=list(pool.map(lambda i:c.patch(U,json={**b,'operationId':'parallel-'+str(i),'changes':{'title':'虚构新 '+str(i)}}),range(2)))
    assert sorted(r.status_code for r in result)==[200,409]
    saved=read(c);assert saved['lastChange']['operationId'].startswith('parallel-')
    assert c.patch(U,json=b).status_code==409
    assert read(c)==saved
    revert=body(c,{'title':start['case']['title']},op='revert')
    assert c.patch(U,json=revert).status_code==200
    assert read(c)['case']==start['case'] and read(c)['revision']!=start['revision']
    assert c.patch(U,json={**b,'operationId':'stale-aba'}).status_code==409
    assert c.patch(U,json=body(c,op='revert')).status_code==409
    # Successful write with response intentionally ignored: a GET identifies its operation, not just matching text.
    assert c.patch(U,json=body(c,op='lost-reply')).status_code==200
    assert read(c)['lastChange']['operationId']=='lost-reply'
    assert read(c)['lastChange']['operationId']!='unrelated-operation'


def test_fail_audit_rolls_back(env,monkeypatch):
    c,_,_=env;b=body(c);before=read(c)
    def fail(*a,**kw):raise RuntimeError('synthetic audit fail')
    monkeypatch.setattr(audit,'append',fail)
    with pytest.raises(RuntimeError):c.patch(U,json=b)
    assert read(c)==before


def test_related_data_and_blob_are_untouched(env):
    c,app,settings=env
    blob=settings.blob_dir/'synthetic-evidence.txt';blob.write_bytes(b'Synthetic immutable source')
    with app.state.db.session() as s:
        put_doc(s,VesselRow,CID,'v1',{'caseId':CID,'vesselId':'v1','name':'Synthetic'})
        put_doc(s,EnvironmentObservationRow,CID,'env1',{'caseId':CID,'observationId':'env1','observedAtUtc':None,
          'locationDescription':None,'description':'Synthetic','sourceLabel':'Synthetic','valueOrigin':'Direct'})
        s.add(TrackPointRow(case_id=CID,vessel_id='v1',time_sec=1,doc={'vesselId':'v1','timeSec':1,'latDeg':2,'lonDeg':1,'sogKn':0,'cogDeg':0}))
    before={suffix:c.get(P+suffix).json() for suffix in ['/vessels','/environment-observations','/tracks','/evidence']}
    blob_sha=hashlib.sha256(blob.read_bytes()).hexdigest()
    assert c.patch(U,json=body(c)).status_code==200
    assert all(c.get(P+k).json()==v for k,v in before.items())
    assert hashlib.sha256(blob.read_bytes()).hexdigest()==blob_sha
    assert read(c,'CASE-ACCEPT-W84-B')['case']==seed_case('CASE-ACCEPT-W84-B')


def test_restart_long_id_and_cross_case_token(env):
    c,app,settings=env;cid='CASE-'+('long'*40)
    assert c.post('/api/v1/cases',json=seed_case(cid)).status_code==201
    path='/api/v1/cases/'+cid+'/metadata';before=read(c,cid)
    b={**body(c),'expectedRevision':before['revision'],'operationId':'long-id'}
    assert c.patch(U,json=b).status_code==409
    r=c.patch(path,json=b);assert r.status_code==200
    with TestClient(create_app(settings)) as restarted:assert read(restarted,cid)==r.json()


def test_openapi_exact_endpoints_and_freeze(env):
    _,app,_=env;spec=yaml.safe_load((ROOT/'contracts/openapi.yaml').read_text())
    assert {'get','patch'} <= set(spec['paths']['/api/v1/cases/{caseId}/metadata'])
    assert {'get','patch'} <= set(app.openapi()['paths']['/api/v1/cases/{case_id}/metadata'])
    for line in (ROOT/'logs/w84-backend-hashes-frozen-v2.txt').read_text().splitlines():
        digest,path=line.split('  ',1);assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path


@pytest.mark.parametrize('field',['leadInvestigator','agencyName','summaryNotes'])
def test_cleared_optional_fields_package_normalization(env,tmp_path,field):
    c,_,_=env
    assert c.patch(U,json=body(c,{field:'Synthetic value'},op='set-value')).status_code==200
    r=c.patch(U,json=body(c,{field:None},op='clear-value'));assert r.status_code==200
    assert field not in r.json()['case']
    package=c.get(P+'/export').content
    with TestClient(create_app(Settings(data_dir=tmp_path/'cleared',seed_demo=False))) as d:
        assert d.post('/api/v1/cases:import',content=package).status_code==201
        restored=read(d)
        assert restored['case'][field]==''
        assert restored['lastChange']==r.json()['lastChange']
        event=next(e for e in d.get(P+'/audit').json() if e['action']=='case.metadata.update' and json.loads(json.loads(e['line'])['reason'])['operationId']=='clear-value')
        detail=json.loads(json.loads(event['line'])['reason'])
        assert detail['before'][field]=={'present':True,'value':'Synthetic value'}
        assert detail['after'][field]=={'present':False,'value':None}
        assert restored['revision']!=r.json()['revision']
