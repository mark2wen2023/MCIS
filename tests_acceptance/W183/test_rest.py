"""Independent synthetic-input tests with the actual isolated C# CLI."""
import copy,hashlib,json,os,subprocess
from datetime import datetime,timedelta,timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from mcis_service.main import create_app
from mcis_service.config import Settings,PROJECT_ROOT
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.evidence.models import EvidenceRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
import mcis_service.human_factors_preview.router as r
ROOT=PROJECT_ROOT
CLI=ROOT/'tools/mcis-rest/mcis-rest.sh'
START=datetime(2026,1,1,tzinfo=timezone.utc)
def stamp(h):return (START+timedelta(hours=h)).strftime('%Y-%m-%dT%H:%M:%SZ')
def schedule(hours=24,rest=10):return {'recordStartUtc':stamp(0),'recordEndUtc':stamp(hours),'intervals':[{'startUtc':stamp(0),'endUtc':stamp(rest),'kind':'Rest'}]}
def request_body(**kwargs):return {**schedule(**kwargs),'sourceEvidenceIds':['EV-001']}
def url(cid='CASE-A',action='preview'):return f'/api/v1/cases/{cid}/human-factors/rest:{action}'
def cli(body):
    out=subprocess.run([str(CLI)],input=json.dumps(body).encode(),capture_output=True,timeout=60)
    assert out.returncode==0,out.stderr.decode()
    return json.loads(out.stdout)['result']
@pytest.fixture(autouse=True)
def runtime(monkeypatch,tmp_path):
    monkeypatch.setenv('MCIS_DOTNET',os.environ.get('MCIS_DOTNET',str(Path.home()/'.dotnet/dotnet')))
    monkeypatch.setenv('DOTNET_CLI_HOME',str(tmp_path/'dotnet-home'))
@pytest.fixture
def client(tmp_path):
    app=create_app(Settings(data_dir=tmp_path/'data',seed_demo=False))
    with app.state.db.session() as s:
        for cid in ['CASE-A','CASE-B']:
            put_doc(s,CaseRow,cid,cid,{'caseId':cid,'title':cid})
            put_doc(s,EvidenceRow,cid,'EV-001',{'caseId':cid,'evidenceId':'EV-001','title':cid+' synthetic public record','sha256':('a' if cid=='CASE-A' else 'b')*64,'confidentiality':'Normal'})
        put_doc(s,EvidenceRow,'CASE-B','EV-002',{'caseId':'CASE-B','evidenceId':'EV-002','title':'B only','sha256':'c'*64,'confidentiality':'Normal'})
    with TestClient(app) as c:yield c

def test_short_record_unknown_not_rest_or_compliance():
    x=cli(schedule(hours=12,rest=4))
    assert x['coverage']=={'recordHours':12,'has24hWindow':False,'has7dWindow':False,'unknownHours':8}
    assert x['totals']=={'restHours':4,'workHours':0,'unknownHours':8}
    assert not any(f['rule'] in ['Rest24h','Rest7d'] for f in x['findings'])
    assert 'isCompliant' not in json.dumps(x)
    assert x['assumptions'] and x['mode']=='rest-baseline-no-exceptions'

@pytest.mark.parametrize('rest,violates',[(10,False),(10-1/3600,True)])
def test_actual_10_hour_boundary(rest,violates):
    b=schedule(rest=rest);b['intervals'].append({'startUtc':stamp(rest),'endUtc':stamp(24),'kind':'Watch'})
    x=cli(b)
    assert any(f['rule']=='Rest24h' for f in x['findings'])==violates
    assert not any(f['rule'].startswith('Work') for f in x['findings'])

@pytest.mark.parametrize('rest,violates',[(11,False),(10,True)])
def test_actual_77_hour_boundary(rest,violates):
    b={'recordStartUtc':stamp(0),'recordEndUtc':stamp(168),'intervals':[]}
    for day in range(7):
        b['intervals'] += [{'startUtc':stamp(day*24),'endUtc':stamp(day*24+rest),'kind':'Rest'}, {'startUtc':stamp(day*24+rest),'endUtc':stamp((day+1)*24),'kind':'OtherWork'}]
    x=cli(b);assert x['totals']['restHours']==rest*7
    assert any(f['rule']=='Rest7d' for f in x['findings'])==violates
    assert not any(f['rule'].startswith('Work') for f in x['findings'])

def counts(c):
    with c.app.state.db.session() as s:
        tables=s.execute(text("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")).scalars().all()
        return {t:s.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar() for t in tables}

def test_real_api_binding_no_writes_and_cross_case(client):
    before=counts(client)
    out=client.post(url(),json=request_body());assert out.status_code==200,out.text
    d=out.json();assert d['persisted'] is False and d['assessment']=='technical-preview-only'
    assert d['sources']==[{'evidenceId':'EV-001','title':'CASE-A synthetic public record','sha256':'a'*64}]
    expected=hashlib.sha256(json.dumps({'caseId':'CASE-A','schedule':schedule(),'sources':d['sources']},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    assert d['inputSha256']==expected and out.headers['cache-control']=='no-store'
    b=request_body();b['sourceEvidenceIds']=['EV-002']
    assert client.post(url(),json=b).status_code==403
    assert counts(client)==before

@pytest.mark.parametrize('role',['Public','AgentService','ExternalExpert','InterestedState'])
def test_denied_identity_does_not_leak_case(client,role):
    a=client.post(url(),content=b'bad',headers={'X-MCIS-Role':role})
    b=client.post(url('MISSING'),content=b'bad',headers={'X-MCIS-Role':role})
    assert a.status_code==b.status_code==403 and a.json()==b.json()

@pytest.mark.parametrize('mutation',['source','policy'])
def test_rechecks_source_and_permission_after_real_core(client,monkeypatch,mutation):
    original=r.run_core
    def run(body):
        value=original(body)
        with client.app.state.db.session() as s:
            if mutation=='source':put_doc(s,EvidenceRow,'CASE-A','EV-001',{'caseId':'CASE-A','evidenceId':'EV-001','title':'changed','sha256':'d'*64,'confidentiality':'Normal'})
            else:
                p=default_policy();p['matrix']['Investigator']['personal']='Deny';put_doc(s,AccessPolicyRow,'CASE-A','policy',p)
        return value
    monkeypatch.setattr(r,'run_core',run)
    out=client.post(url(),json=request_body())
    assert out.status_code==(409 if mutation=='source' else 403),out.text
    assert 'result' not in out.json()

@pytest.mark.parametrize('mutation',['overlap','outside','unknown','duplicate','hash'])
def test_invalid_inputs_fail_closed(client,mutation):
    b=request_body()
    if mutation=='overlap':b['intervals'].append({'startUtc':stamp(5),'endUtc':stamp(12),'kind':'Watch'})
    if mutation=='outside':b['intervals'][0]['endUtc']=stamp(25)
    if mutation=='unknown':b['intervals'][0]['kind']='Unknown'
    if mutation=='duplicate':b['sourceEvidenceIds']*=2
    if mutation=='hash':b['sourceSha256']='a'*64
    assert client.post(url(),json=b).status_code==422

def test_missing_cli_is_503_not_fallback(client,monkeypatch,tmp_path):
    monkeypatch.setattr(r,'CLI',tmp_path/'not-installed')
    out=client.post(url(),json=request_body());assert out.status_code==503
    assert 'result' not in out.json()

def test_existing_core_and_rest_source_unchanged_under_concurrent_cli():
    paths=[ROOT/'tools/mcis-core/out/mcis-core.dll',ROOT/'unity/Assets/_Project/Scripts/Domain/HumanFactors/RestHours.cs']
    prior={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    with ThreadPoolExecutor(3) as pool:results=list(pool.map(lambda _:cli(schedule(hours=12,rest=4)),range(3)))
    assert all(x==results[0] for x in results)
    assert prior=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

@pytest.mark.parametrize('mutation',['long-record','too-many','bad-utc','duplicate-json-key'])
def test_engineering_limits_and_strict_json(client,mutation):
    b=request_body()
    if mutation=='long-record':b['recordEndUtc']=stamp(337)
    elif mutation=='too-many':b['intervals']=b['intervals']*257
    elif mutation=='bad-utc':b['recordStartUtc']='2026-01-01T00:00:00+00:00'
    if mutation=='duplicate-json-key':
        raw=json.dumps(b).replace('"recordStartUtc":','"recordStartUtc":"2026-01-01T00:00:00Z","recordStartUtc":',1)
        out=client.post(url(),content=raw,headers={'Content-Type':'application/json'})
    else:out=client.post(url(),json=b)
    assert out.status_code==422 and 'result' not in out.json()


def test_fragmented_rest_real_cli_and_api_agree(client):
    b={'recordStartUtc':stamp(0),'recordEndUtc':stamp(24),'intervals':[]}
    for start,end,kind in [(0,4,'Rest'),(4,6,'Watch'),(6,10,'Rest'),(10,12,'OtherWork'),(12,16,'Rest'),(16,24,'Watch')]:
        b['intervals'].append({'startUtc':stamp(start),'endUtc':stamp(end),'kind':kind})
    core=cli(b)
    splits=[f for f in core['findings']+core['insufficientData'] if f['rule']=='RestSplit']
    assert splits and all(f['limitHours']==10 and f['actualHours']==8 for f in splits)
    out=client.post(url(),json={**b,'sourceEvidenceIds':['EV-001']})
    assert out.status_code==200,out.text
    assert out.json()['result']==core
