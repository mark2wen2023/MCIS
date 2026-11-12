"""W14.4 uses only synthetic cases; fake core tests are separated from real CLI."""
import copy
import hashlib
import importlib
import json
import subprocess

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from .conftest import H, make_settings
from mcis_service.main import create_app
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.evidence.models import EvidenceRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy

api = importlib.import_module('mcis_service.nomoto_preview.router')
CASE='CASE-SYNTHETIC-NOMOTO'
URL=f'/api/v1/cases/{CASE}/whatif/nomoto:preview'
SOURCES=f'/api/v1/cases/{CASE}/whatif/nomoto:sources'


def body():
    return {'parameters':{'headingDeg':'0','speedKn':'10','k':'0.05','tSeconds':'10','referenceSpeedKn':'10',
            'maxRudderDeg':'35','rudderRateDegPerSec':'5','commandRudderDeg':'10','durationSeconds':'3',
            'provenanceNote':'Synthetic parameters, not a real ship','uncertaintyNote':'Not calibrated'},'sourceEvidenceIds':[]}


def source(db,case_id=CASE,**changes):
    doc=dict(evidenceId='EV-981',caseId=case_id,title='Synthetic source',sha256='a'*64,confidentiality='Normal',
             source='DO NOT RETURN',extractedBy='DO NOT RETURN',note='DO NOT RETURN')
    doc.update(changes)
    with db.session() as s: put_doc(s,EvidenceRow,case_id,doc['evidenceId'],doc)
    return doc


@pytest.fixture()
def app(tmp_path): return create_app(make_settings(tmp_path,seed=False))


@pytest.fixture()
def preview(app):
    with TestClient(app) as client:
        with app.state.db.session() as s:
            put_doc(s,CaseRow,CASE,CASE,{'caseId':CASE,'title':'Synthetic nomoto','isFictionalDemo':True})
        source(app.state.db)
        yield client,app.state.db


def valid_result():
    points=[{'timeSeconds':i,'eastM':0,'northM':i*5,'headingDeg':0,'speedKn':10,'rotDegPerSec':0,'rudderDeg':0} for i in range(4)]
    return {'coreVersion':'mcis-nomoto/1','mode':'fixed-rudder-hypothesis','stepSeconds':0.1,'comparisonStepSeconds':0.05,
            'baseline':points,'response':copy.deepcopy(points),'numericalDifference':{'endpointDistanceM':0,'endpointHeadingDifferenceDeg':0,'endpointRotDifferenceDegPerSec':0},'assumptions':['Synthetic test double only']}


@pytest.fixture()
def fake_core(monkeypatch):
    result=valid_result()
    monkeypatch.setattr(api,'run_core',lambda _:copy.deepcopy(result))
    return result


def save_policy(db,policy):
    with db.session() as s: put_doc(s,AccessPolicyRow,CASE,'policy',policy)


@pytest.mark.parametrize('role',['Public','ExternalExpert','InterestedState','AgentService'])
def test_roles_fail_before_parsing_and_case_existence(preview,role):
    client,_=preview
    a=client.post(URL,content=b'bad',headers=H(role)); b=client.post(URL.replace(CASE,'UNKNOWN'),content=b'bad',headers=H(role))
    assert a.status_code==b.status_code==403 and a.json()==b.json()
    assert a.headers['cache-control']=='no-store'
    assert client.get(SOURCES,headers=H(role)).status_code==403


@pytest.mark.parametrize('category',['personal','evidence_meta'])
@pytest.mark.parametrize('level',['Deny','Redacted','Unknown',None])
def test_full_read_gate(preview,category,level):
    client,db=preview; policy=default_policy(); policy['matrix']['Investigator'][category]=level; save_policy(db,policy)
    assert client.post(URL,json=body(),headers=H()).status_code==403
    assert client.get(SOURCES,headers=H()).status_code==403


def test_source_listing_scoped_minimal(preview):
    client,db=preview; source(db,'OTHER-CASE',evidenceId='EV-982')
    response=client.get(SOURCES,headers=H()); assert response.status_code==200
    assert response.headers['cache-control']=='no-store'
    data=response.json(); assert data['profile']=='MCIS-NOMOTO-PREVIEW-1'
    assert data['identityMode']=='local-role-header'
    assert data['sources']==[{'evidenceId':'EV-981','title':'Synthetic source','sha256':'a'*64}]
    assert 'DO NOT RETURN' not in response.text


def test_hidden_and_cross_case_sources(preview):
    client,db=preview; source(db,confidentiality='Restricted'); source(db,'OTHER-CASE',evidenceId='EV-982')
    policy=default_policy(); policy['matrix']['Investigator']['testimony']='Deny'; save_policy(db,policy)
    assert client.get(SOURCES,headers=H()).json()['sources']==[]
    for eid in ['EV-981','EV-982','EV-999']:
        value=body(); value['sourceEvidenceIds']=[eid]
        assert client.post(URL,json=value,headers=H()).status_code==403


@pytest.mark.parametrize('raw',[b'NaN',b'1e999',b'{"model":1,"model":2}',b'"\\ud800"',b'['*70+b'0'+b']'*70])
def test_strict_json(preview,raw):
    client,_=preview
    assert client.post(URL,content=raw,headers={**H(),'Content-Type':'application/json'}).status_code==422


def test_content_type_and_size(preview):
    client,_=preview
    assert client.post(URL,content=json.dumps(body()),headers=H()).status_code==415
    assert client.post(URL,content=b' '*(api.MAX_BYTES+1),headers={**H(),'Content-Type':'application/json'}).status_code==413




@pytest.mark.parametrize('key,value',[('headingDeg',360),('headingDeg','360'),('headingDeg','-0'),('headingDeg','-0.000'),
 ('speedKn','41'),('k','0'),('k','0.500001'),('tSeconds','0'),('tSeconds','1001'),('referenceSpeedKn','0.09'),
 ('maxRudderDeg','46'),('rudderRateDegPerSec','0.001'),('commandRudderDeg','36'),('commandRudderDeg','-36'),
 ('durationSeconds','3.0'),('durationSeconds','301'),('durationSeconds','0'),('speedKn','01'),('speedKn','1e1'),
 ('speedKn','+10'),('speedKn','10.0000001'),('speedKn',True),('k','NaN'),('k','Infinity'),('speedKn',' 10'),
 ('provenanceNote',''),('uncertaintyNote',' x '),('provenanceNote','x'*1001)])
def test_input_boundaries(preview,key,value):
    client,_=preview; payload=body(); payload['parameters'][key]=value
    assert client.post(URL,json=payload,headers=H()).status_code==422


def test_unknown_missing_ratio_and_sources(preview):
    client,_=preview
    mutations=[]
    p=body(); p['parameters']['referenceSpeedKn']='0.1'; mutations.append(p)
    p=body(); p['parameters']['extra']='x'; mutations.append(p)
    p=body(); del p['parameters']['k']; mutations.append(p)
    p=body(); p['sourceEvidenceIds']=['EV-981']*2; mutations.append(p)
    p=body(); p['sourceEvidenceIds']=[f'EV-{i:03}' for i in range(9)]; mutations.append(p)
    for payload in mutations: assert client.post(URL,json=payload,headers=H()).status_code==422


@pytest.mark.parametrize('ids',[[],['EV-981']])
def test_hash_preserves_original_decimal_strings_no_write(preview,fake_core,ids):
    client,db=preview; payload=body(); payload['sourceEvidenceIds']=ids; payload['parameters']['speedKn']='10.00'; statements=[]
    def capture(conn,cursor,statement,parameters,context,executemany): statements.append(statement.strip().split()[0].upper())
    event.listen(db.engine,'before_cursor_execute',capture)
    try: response=client.post(URL,json=payload,headers=H())
    finally: event.remove(db.engine,'before_cursor_execute',capture)
    assert response.status_code==200,response.text
    data=response.json()
    assert data['inputSha256']==hashlib.sha256(api.canonical({'caseId':CASE,'parameters':payload['parameters'],'sources':data['sources']})).hexdigest()
    assert data['assessment']=='hypothetical-single-vessel-response' and data['persisted'] is False
    assert response.headers['cache-control']=='no-store'
    assert not {'INSERT','UPDATE','DELETE','REPLACE','CREATE','DROP','ALTER'}.intersection(statements)
    payload['parameters']['speedKn']='10'
    changed=client.post(URL,json=payload,headers=H()).json()
    assert changed['inputSha256']!=data['inputSha256']


@pytest.mark.parametrize('change,status',[('policy',409),('source',409),('deny',403)])
def test_policy_source_rechecked(preview,fake_core,monkeypatch,change,status):
    client,db=preview; payload=body(); payload['sourceEvidenceIds']=['EV-981']
    def changed(_):
        if change=='source': source(db,title='Changed')
        else:
            policy=default_policy()
            if change=='deny': policy['matrix']['Investigator']['personal']='Deny'
            else: policy['version']='changed'
            save_policy(db,policy)
        return fake_core
    monkeypatch.setattr(api,'run_core',changed)
    response=client.post(URL,json=payload,headers=H())
    assert response.status_code==status and 'result' not in response.json()


def test_core_unavailable(preview,monkeypatch,tmp_path):
    client,_=preview; monkeypatch.setattr(api,'CLI',tmp_path/'missing')
    assert client.post(URL,json=body(),headers=H()).status_code==503


@pytest.mark.parametrize('mutation',['version','mode','step','nan','bool','length','timestamp','initial_position','initial_heading',
 'initial_rot','initial_rudder','speed','heading','rudder','diff','negative_diff','empty_assumptions','unknown'])
def test_bad_core_output(preview,monkeypatch,mutation):
    client,_=preview; result=valid_result()
    if mutation=='version': result['coreVersion']='unknown'
    elif mutation=='mode': result['mode']='collision'
    elif mutation=='step': result['stepSeconds']=1
    elif mutation=='nan': result['response'][1]['eastM']=float('nan')
    elif mutation=='bool': result['response'][1]['timeSeconds']=True
    elif mutation=='length': result['response'].pop()
    elif mutation=='timestamp': result['response'][1]['timeSeconds']=2
    elif mutation=='initial_position': result['response'][0]['eastM']=1
    elif mutation=='initial_heading': result['response'][0]['headingDeg']=1
    elif mutation=='initial_rot': result['response'][0]['rotDegPerSec']=1
    elif mutation=='initial_rudder': result['response'][0]['rudderDeg']=1
    elif mutation=='speed': result['response'][1]['speedKn']=11
    elif mutation=='heading': result['response'][1]['headingDeg']=360
    elif mutation=='rudder': result['response'][1]['rudderDeg']=36
    elif mutation=='diff': result['numericalDifference']['endpointHeadingDifferenceDeg']=181
    elif mutation=='negative_diff': result['numericalDifference']['endpointDistanceM']=-1
    elif mutation=='empty_assumptions': result['assumptions']=[]
    else: result['safe']=True
    monkeypatch.setattr(api.subprocess,'run',lambda *a,**kw:subprocess.CompletedProcess(a,0,json.dumps({'ok':True,'result':result}).encode(),b''))
    response=client.post(URL,json=body(),headers=H())
    assert response.status_code==503 and 'result' not in response.json()


@pytest.mark.parametrize('changes',[{}, {'commandRudderDeg':'-10'}, {'speedKn':'0'}, {'commandRudderDeg':'0'},
 {'durationSeconds':'300','speedKn':'40','referenceSpeedKn':'8','k':'0.5','tSeconds':'1','maxRudderDeg':'45','commandRudderDeg':'45','rudderRateDegPerSec':'20'}])
def test_real_cli_response(preview,changes):
    client,_=preview
    if not api.CLI.is_file(): pytest.skip('CLI not yet built')
    payload=body(); payload['parameters'].update(changes)
    response=client.post(URL,json=payload,headers=H()); assert response.status_code==200,response.text
    data=response.json(); result=data['result']; duration=int(payload['parameters']['durationSeconds'])
    assert len(result['response'])==len(result['baseline'])==duration+1
    assert result['response'][0]['rudderDeg']==0 and result['response'][-1]['timeSeconds']==duration
    assert result['coreVersion']=='mcis-nomoto/1' and data['persisted'] is False
