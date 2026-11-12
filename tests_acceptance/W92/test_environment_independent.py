"""Independent acceptance: synthetic data, isolated databases, no live services."""
import io
import json
import zipfile
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from mcis_service.config import Settings
from mcis_service.main import create_app
from mcis_service.db import put_doc
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.package.mcase import read_zip, manifest_json

CASE = 'ACCEPTANCE-W92-A'
BASE = '/api/v1/cases/' + CASE
URL = BASE + '/environment-observations'


def metadata(case_id=CASE):
    return dict(caseId=case_id, schemaVersion='1.0.0', title='虚构验收案件', accidentType='Collision',
                incidentTimeUtc='2024-01-01T00:00:00Z', caseEpochUtc='2024-01-01T00:00:00Z',
                displayTimeZoneOffsetMinutes=480, incidentLocation={'lonDeg':123,'latDeg':30}, isFictionalDemo=True)


def record(**updates):
    return dict({'observationId':'OBS-A','caseId':CASE,'observedAtUtc':None,
                 'locationDescription':None,'description':'  虚构原文：能见度良好\n东北风4级；测站/时段未知。  ',
                 'sourceLabel':'虚构验收来源，非真实证据','valueOrigin':'Direct'}, **updates)


def make_app(path):
    settings=Settings();settings.data_dir=path;settings.db_url='sqlite:///'+str(path/'test.db');settings.seed_demo=False
    return create_app(settings)


@pytest.fixture
def app(tmp_path):
    return make_app(tmp_path)


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        assert c.post('/api/v1/cases',json=metadata()).status_code==201
        yield c


def audits(c):
    return c.get(BASE+'/audit').json()


def package(c,records='absent',listed=True,raw=None):
    fs=read_zip(c.get(BASE+'/export').content);fs.pop('manifest.json')
    if records!='absent':fs['environment/observations.json']=json.dumps(records).encode()
    if raw is not None:fs['environment/observations.json']=raw
    listing=dict(fs)
    if not listed:listing.pop('environment/observations.json',None)
    fs['manifest.json']=manifest_json(CASE,listing,'2024-01-01T00:00:00Z').encode()
    buff=io.BytesIO()
    with zipfile.ZipFile(buff,'w') as z:
        for p,b in fs.items():z.writestr(p,b)
    return buff.getvalue()


def imported(tmp_path,data):
    target=make_app(tmp_path/'target')
    with TestClient(target) as c:
        r=c.post('/api/v1/cases:import',content=data,headers={'Content-Type':'application/zip'})
        return r,c.get('/api/v1/cases').json(),c.get(URL)


def test_unknown_original_statement_preserved_and_audited(client):
    before=len(audits(client)); doc=record()
    assert client.get(URL).json()==[]
    assert client.post(URL,json=doc).json()==doc
    assert client.get(URL).json()==[doc]
    assert len(audits(client))==before+1
    assert audits(client)[-1]['action']=='environment.observation.create'
    assert all(k not in client.get(URL).json()[0] for k in ['windSpeedMps','currentSpeedKn','visibilityNm'])


@pytest.mark.parametrize('role,write',[('LeadInvestigator',True),('Investigator',True),('ExternalExpert',False),('InterestedState',False),('AgentService',False),('Public',False)])
def test_role_matrix(client,role,write):
    h={'X-MCIS-Role':role}
    assert client.get(URL,headers=h).status_code==200
    assert client.post(URL,json=record(),headers=h).status_code==(201 if write else 403)
    assert len(client.get(URL).json())==int(write)


@pytest.mark.parametrize('level,get_status',[('Deny',403),('Redacted',403),('ReadOnly',200)])
def test_custom_case_policy_no_raw_leak(client,app,level,get_status):
    assert client.post(URL,json=record()).status_code==201
    policy=default_policy();policy['matrix']['Investigator']['ais_sim']=level
    with app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',policy)
    r=client.get(URL);assert r.status_code==get_status
    if get_status==403:assert '东北风' not in r.text and '虚构验收来源' not in r.text
    assert client.post(URL,json=record(observationId='OBS-B')).status_code==403


@pytest.mark.parametrize('extra',[
 {'observedAtUtc':'2023-02-29T12:00:00Z'}, {'observedAtUtc':'2024-02-30T12:00:00Z'},
 {'observedAtUtc':'2024-01-01T00:00:60Z'}, {'observedAtUtc':'2024-01-01T08:00:00+08:00'},
 {'windFromDirDeg':360.00001}, {'currentToDirDeg':-0.00001}, {'visibilityNm':-0.00001},
 {'windSpeedMps':False}, {'currentSpeedKn':'4'}, {'description':'\n\t'},
 {'sourceLabel':'  '}, {'locationDescription':'\t'}, {'caseId':'OTHER'},
 {'observationId':'OBS-A\n'}, {'weatherPresetId':'Clear'}, {'valueOrigin':'Verified'},
])
def test_reject_invalid_without_record_or_audit(client,extra):
    old=audits(client)
    r=client.post(URL,json=record(**extra));assert r.status_code==422,r.text
    assert client.get(URL).json()==[] and audits(client)==old


@pytest.mark.parametrize('value',['NaN','Infinity','-Infinity','1e500'])
def test_non_finite_cannot_enter_persistence(client,value):
    body=json.dumps(record())[:-1]+',"windSpeedMps":'+value+'}'
    assert client.post(URL,content=body,headers={'Content-Type':'application/json'}).status_code==422
    assert client.get(URL).json()==[]


def test_zero_null_and_direction_endpoints_distinct(client):
    doc=record(observedAtUtc='2024-02-29T23:59:59Z',windSpeedMps=0,windFromDirDeg=360,currentSpeedKn=None,currentToDirDeg=0,visibilityNm=0)
    assert client.post(URL,json=doc).status_code==201
    assert client.get(URL).json()==[doc]


def test_no_update_or_delete_route(client):
    doc=record();assert client.post(URL,json=doc).status_code==201
    for method in [client.put,client.patch,client.delete]:
        assert method(URL+'/OBS-A').status_code in (404,405)
    assert client.get(URL).json()==[doc]


def test_same_id_concurrency_and_cross_case_isolation(client):
    with ThreadPoolExecutor(2) as pool:
        results=list(pool.map(lambda i:client.post(URL,json=record(description=f'虚构竞争 {i}')).status_code,range(2)))
    assert sorted(results)==[201,409]
    original=client.get(URL).json(); assert len(original)==1
    assert client.post('/api/v1/cases',json=metadata('ACCEPTANCE-W92-B')).status_code==201
    other='/api/v1/cases/ACCEPTANCE-W92-B/environment-observations'
    assert client.get(other).json()==[]
    assert client.post(other,json=record(caseId='ACCEPTANCE-W92-B')).status_code==201
    assert client.get(URL).json()==original


def test_atomic_audit_failure(client,monkeypatch):
    from mcis_service.environment import router
    before=audits(client)
    def failed(*args,**kwargs):raise RuntimeError('synthetic audit failure')
    monkeypatch.setattr(router.audit,'append',failed)
    with pytest.raises(RuntimeError):client.post(URL,json=record())
    assert client.get(URL).json()==[] and audits(client)==before


def test_restart(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        assert c.post('/api/v1/cases',json=metadata()).status_code==201
        assert c.post(URL,json=record()).status_code==201
    with TestClient(make_app(tmp_path)) as c:assert c.get(URL).json()==[record()]


def test_roundtrip_and_old_package(client,tmp_path):
    doc=record(visibilityNm=None,windSpeedMps=0)
    assert client.post(URL,json=doc).status_code==201
    r,cases,result=imported(tmp_path,client.get(BASE+'/export').content)
    assert r.status_code==201 and result.json()==[doc]
    old=package(client,records=[])
    # Old packages genuinely omit the new extension.
    fs=read_zip(old);fs.pop('environment/observations.json');fs.pop('manifest.json')
    fs['manifest.json']=manifest_json(CASE,fs,'2024-01-01T00:00:00Z').encode()
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z:
        for p,b in fs.items():z.writestr(p,b)
    r,_,result=imported(tmp_path/'old',buf.getvalue())
    assert r.status_code==201 and result.json()==[]


@pytest.mark.parametrize('docs',[[record(),record()], [record(caseId='OTHER')], [record(observedAtUtc='2024-02-30T00:00:00Z')], [record(visibilityNm=-1)], {}, [None]])
def test_bad_import_is_atomic(client,tmp_path,docs):
    r,cases,read=imported(tmp_path,package(client,docs))
    assert r.status_code==422,r.text
    assert cases==[] and read.status_code==404


@pytest.mark.parametrize('raw,listed',[(b'{invalid',True),(b'\xff',True),(b'[]',False)])
def test_bad_extension_encoding_or_manifest_coverage(client,tmp_path,raw,listed):
    r,cases,read=imported(tmp_path,package(client,listed=listed,raw=raw))
    assert r.status_code==422 and cases==[] and read.status_code==404


def test_declared_openapi_matches_runtime_environment_paths(app):
    from pathlib import Path
    import yaml
    spec=yaml.safe_load((Path(__file__).resolve().parents[2]/'contracts/openapi.yaml').read_text())
    canonical='/api/v1/cases/{caseId}/environment-observations'
    assert canonical in spec['paths']
    assert {'get','post'} <= set(spec['paths'][canonical])
    runtime={p.replace('{case_id}','{caseId}') for p in app.openapi()['paths']}
    assert canonical in runtime


def test_long_legacy_case_id_create_read_and_package_roundtrip(client,tmp_path):
    # Original common caseId has no 64-character ceiling; SQLite preserves this identifier.
    case_id='LEGACY-'+('x'*150)
    base='/api/v1/cases/'+case_id
    url=base+'/environment-observations'
    response=client.post('/api/v1/cases',json=metadata(case_id))
    assert response.status_code==201,response.text
    doc=record(caseId=case_id,windSpeedMps=0,visibilityNm=None)
    response=client.post(url,json=doc)
    assert response.status_code==201,response.text
    assert response.json()==doc and client.get(url).json()==[doc]
    data=client.get(base+'/export').content
    assert json.loads(read_zip(data)['environment/observations.json'])==[doc]
    with TestClient(make_app(tmp_path/'legacy-target')) as target:
        response=target.post('/api/v1/cases:import',content=data,headers={'Content-Type':'application/zip'})
        assert response.status_code==201,response.text
        assert response.json()['caseId']==case_id
        assert target.get(url).json()==[doc]
        assert target.get(base).json()['caseId']==case_id
