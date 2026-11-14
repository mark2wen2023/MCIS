"""Synthetic W9.2 inputs. No observations of a real accident."""
import io
import json
import zipfile
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from .conftest import C, H, CASE, make_settings
from mcis_service.main import create_app
from mcis_service.audit import service as audit
from mcis_service.db import put_doc
from mcis_service.package.mcase import read_zip, manifest_json
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy

URL = C + '/environment-observations'


@pytest.fixture()
def app(tmp_path):
    # Environment archive coverage must not depend on unrelated demo content.
    return create_app(make_settings(tmp_path, seed=False))


@pytest.fixture()
def client(app):
    with TestClient(app) as client:
        case = {
            'schemaVersion': '1.0.0', 'caseId': CASE,
            'title': 'Synthetic environment-only case', 'accidentType': 'Collision',
            'caseEpochUtc': '2026-01-01T00:00:00Z',
            'incidentTimeUtc': '2026-01-01T00:00:00Z',
            'incidentLocation': {'lonDeg': 0, 'latDeg': 0},
            'displayTimeZoneOffsetMinutes': 0, 'isFictionalDemo': True,
        }
        response = client.post('/api/v1/cases', json=case)
        assert response.status_code == 201, response.text
        yield client


def export_package(client):
    response = client.get(C + '/export')
    assert response.status_code == 200, response.text
    return response.content


def test_seeded_restricted_content_export_still_denied(tmp_path):
    with TestClient(create_app(make_settings(tmp_path, seed=True))) as client:
        response = client.get(C + '/export', headers=H())
        assert response.status_code == 403
        assert response.json()['code'] == 'FORBIDDEN'
        assert response.headers['content-type'].startswith('application/json')


def observation(**extra):
    return dict(observationId='ENV-test', caseId=CASE, observedAtUtc=None,
                locationDescription=None, description='Synthetic: qualitative visibility only',
                sourceLabel='Synthetic source p.1; not actual evidence', valueOrigin='Direct', **extra)


def changed(**extra):
    return {**observation(), **extra}


def test_empty_create_unknown_roundtrip(client, empty_client):
    assert client.get(URL).json() == []
    body=changed(windSpeedMps=0, windFromDirDeg=None, visibilityNm=0, currentToDirDeg=360)
    r=client.post(URL,json=body)
    assert r.status_code==201,r.text
    assert r.json()==body
    assert client.get(URL).json()==[body]
    assert 'currentSpeedKn' not in client.get(URL).json()[0]
    data=export_package(client)
    files=read_zip(data)
    assert json.loads(files['environment/observations.json'])==[body]
    r=empty_client.post('/api/v1/cases:import',files={'file':('test.mcase',data,'application/zip')})
    assert r.status_code==201,r.text
    assert empty_client.get(URL).json()==[body]
    ev=client.get(C+'/audit').json()
    matching=[e for e in ev if e['action']=='environment.observation.create']
    assert len(matching)==1 and matching[0]['entityId']=='ENV-test'


@pytest.mark.parametrize('role',['LeadInvestigator','Investigator'])
def test_writer(client,role):
    assert client.post(URL,json=observation(),headers=H(role)).status_code==201


@pytest.mark.parametrize('role',['ExternalExpert','InterestedState','AgentService','Public'])
def test_readers(client,role):
    assert client.get(URL,headers=H(role)).status_code==200
    assert client.post(URL,json=observation(),headers=H(role)).status_code==403


@pytest.mark.parametrize('level',['ReadOnly','Redacted','Deny'])
def test_case_policy(client,app,level):
    policy=default_policy();policy['matrix']['Investigator']['ais_sim']=level
    with app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',policy)
    assert client.post(URL,json=observation()).status_code==403
    assert client.get(URL).status_code==(403 if level in ('Deny','Redacted') else 200)


@pytest.mark.parametrize('extra',[
 {'caseId':'other'},{'observationId':'x\n'},{'observationId':'../path'},
 {'observationId':''},{'description':'\t '},{'sourceLabel':' '},{'locationDescription':' '},
 {'observedAtUtc':'2026-02-30T00:00:00Z'},{'observedAtUtc':'2026-01-01T00:00:00+00:00'},
 {'observedAtUtc':'2026-01-01T00:00:60Z'},{'observedAtUtc':'0000-01-01T00:00:00Z'},
 {'observedAtUtc':'2026-01-01T00:00:00Z\n'},{'observedAtUtc':'2026-01-01'},
 {'windSpeedMps':-0.00001},{'windFromDirDeg':360.00001},{'currentToDirDeg':-0.00001},
 {'visibilityNm':-1},{'currentSpeedKn':True},{'windSpeedMps':'2'},
 {'weatherPresetId':'Clear'},{'valueOrigin':'AI'},{'description':'x'*4001},
])
def test_invalid_no_write(client,extra):
    before=client.get(C+'/overview').json()['counts']['auditEvents']
    r=client.post(URL,json=changed(**extra))
    assert r.status_code==422,r.text
    assert client.get(URL).json()==[]
    assert client.get(C+'/overview').json()['counts']['auditEvents']==before


@pytest.mark.parametrize('field',['windSpeedMps','windFromDirDeg','currentSpeedKn','currentToDirDeg','visibilityNm'])
@pytest.mark.parametrize('number',['NaN','Infinity','-Infinity','1e400'])
def test_finite(client,field,number):
    body=json.dumps(observation())[:-1]+',"'+field+'":'+number+'}'
    assert client.post(URL,content=body,headers={'Content-Type':'application/json'}).status_code==422


@pytest.mark.parametrize('stamp',['2024-02-29T23:59:59Z','2026-11-12T00:00:00Z'])
def test_valid_dates_direction_boundaries(client,stamp):
    body=changed(observedAtUtc=stamp,windFromDirDeg=0,currentToDirDeg=360,visibilityNm=None)
    assert client.post(URL,json=body).status_code==201
    assert client.get(URL).json()==[body]


def test_concurrent_duplicate_never_overwrites(client):
    with ThreadPoolExecutor(2) as pool:
        codes=list(pool.map(lambda n:client.post(URL,json=changed(description='synthetic '+str(n))).status_code,range(2)))
    assert sorted(codes)==[201,409]
    saved=client.get(URL).json()
    assert client.post(URL,json=observation()).status_code==409
    assert len(saved)==1 and client.get(URL).json()==saved


def test_atomic_audit_failure(client,monkeypatch):
    before=client.get(C+'/overview').json()['counts']['auditEvents']
    def fail(*args,**kwargs):raise RuntimeError('synthetic failure')
    monkeypatch.setattr(audit,'append',fail)
    with pytest.raises(RuntimeError):client.post(URL,json=observation())
    assert client.get(URL).json()==[]
    assert client.get(C+'/overview').json()['counts']['auditEvents']==before


def test_case_isolation_and_restart(tmp_path):
    settings=make_settings(tmp_path,False)
    template={'schemaVersion':'1.0.0','caseId':'A','title':'Synthetic','accidentType':'Collision',
      'caseEpochUtc':'2026-01-01T00:00:00Z','incidentTimeUtc':'2026-01-01T00:00:00Z',
      'incidentLocation':{'lonDeg':0,'latDeg':0},'displayTimeZoneOffsetMinutes':0,'isFictionalDemo':False}
    with TestClient(create_app(settings)) as c:
        for name in ['CASE-A','CASE-B']:assert c.post('/api/v1/cases',json={**template,'caseId':name}).status_code==201
        assert c.post('/api/v1/cases/CASE-A/environment-observations',json=changed(caseId='CASE-A')).status_code==201
        assert c.get('/api/v1/cases/CASE-B/environment-observations').json()==[]
    with TestClient(create_app(settings)) as c:
        assert c.get('/api/v1/cases/CASE-A/environment-observations').json()==[changed(caseId='CASE-A')]
        assert c.get('/api/v1/cases/CASE-B/environment-observations').json()==[]
        assert c.get('/api/v1/cases/missing/environment-observations').status_code==404


def package(client,items=None,raw=None,path='environment/observations.json',listed=True):
    files=read_zip(export_package(client));files.pop('manifest.json')
    if raw is not None:files[path]=raw
    elif items is not None:files[path]=json.dumps(items).encode()
    listing=files if listed else {k:v for k,v in files.items() if k!=path}
    files['manifest.json']=manifest_json(CASE,listing,'2026-01-01T00:00:00Z').encode()
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as z:
        for key,val in files.items():z.writestr(key,val)
    return out.getvalue()


@pytest.mark.parametrize('items',[
 {},[None],[changed(caseId='other')],[observation(),observation()],
 [changed(windSpeedMps=-1)],[changed(observedAtUtc='2026-02-30T00:00:00Z')],
])
def test_bad_package_environment_atomic(client,empty_client,items):
    data=package(client,items)
    r=empty_client.post('/api/v1/cases:import',files={'file':('test.mcase',data)})
    assert r.status_code==422,r.text
    assert empty_client.get('/api/v1/cases').json()==[]
    assert empty_client.get(URL).status_code==404


@pytest.mark.parametrize('raw,listed',[(b'{oops',True),(b'\xff',True),(b'[]',False)])
def test_bad_encoding_or_unlisted_environment(client,empty_client,raw,listed):
    data=package(client,raw=raw,listed=listed)
    assert empty_client.post('/api/v1/cases:import',files={'file':('test.mcase',data)}).status_code==422
    assert empty_client.get('/api/v1/cases').json()==[]


def test_legacy_absence(client,empty_client):
    data=package(client)
    assert 'environment/observations.json' not in read_zip(data)
    assert empty_client.post('/api/v1/cases:import',files={'file':('test.mcase',data)}).status_code==201
    assert empty_client.get(URL).json()==[]


def test_case_insensitive_package_extension(client,empty_client):
    data=package(client,[observation()],path='Environment/Observations.JSON')
    assert empty_client.post('/api/v1/cases:import',files={'file':('test.mcase',data)}).status_code==201
    assert empty_client.get(URL).json()==[observation()]


def test_existing_long_case_id_compatible(tmp_path):
    case_id='CASE-'+('x'*80)
    template={'schemaVersion':'1.0.0','caseId':case_id,'title':'Synthetic long ID',
      'accidentType':'Collision','caseEpochUtc':'2026-01-01T00:00:00Z',
      'incidentTimeUtc':'2026-01-01T00:00:00Z','incidentLocation':{'lonDeg':0,'latDeg':0},
      'displayTimeZoneOffsetMinutes':0,'isFictionalDemo':False}
    with TestClient(create_app(make_settings(tmp_path,False))) as c:
        assert c.post('/api/v1/cases',json=template).status_code==201
        path='/api/v1/cases/'+case_id+'/environment-observations'
        assert c.post(path,json=changed(caseId=case_id)).status_code==201
        assert c.get(path).json()==[changed(caseId=case_id)]
