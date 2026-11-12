import hashlib,json,os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.evidence.models import EvidenceRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.nomoto_preview import router as r
from test_cli import parameters,run

def url(cid='CASE-A',action='preview'):return f'/api/v1/cases/{cid}/whatif/nomoto:{action}'
@pytest.fixture
def client(tmp_path):
    app=create_app(Settings(data_dir=tmp_path,seed_demo=False))
    with app.state.db.session() as s:
        for cid in ['CASE-A','CASE-B']:
            put_doc(s,CaseRow,cid,cid,{'caseId':cid,'title':cid})
            put_doc(s,EvidenceRow,cid,'EV-001',{'caseId':cid,'evidenceId':'EV-001','title':cid+'合成资料🛳','sha256':'a'*64,'confidentiality':'Normal'})
        put_doc(s,EvidenceRow,'CASE-B','EV-002',{'caseId':'CASE-B','evidenceId':'EV-002','title':'private B','sha256':'b'*64,'confidentiality':'Normal'})
    with TestClient(app) as c:yield c

def snapshot(client):
    with client.app.state.db.session() as s:
        tables=s.execute(text("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")).scalars().all()
        return {t:[tuple(row) for row in s.execute(text(f'SELECT * FROM "{t}" ORDER BY rowid')).all()] for t in tables}

@pytest.mark.parametrize('sources',[[],['EV-001']])
def test_real_cli_api_digest_no_write(client,sources):
    before=snapshot(client);m=parameters()
    out=client.post(url(),json={'parameters':m,'sourceEvidenceIds':sources});assert out.status_code==200,out.text
    d=out.json();assert d['result']==run(m)
    assert d['persisted'] is False and d['assessment']=='hypothetical-single-vessel-response'
    expected=hashlib.sha256(json.dumps({'caseId':'CASE-A','parameters':m,'sources':d['sources']},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    assert d['inputSha256']==expected and out.headers['cache-control']=='no-store'
    assert before==snapshot(client)

@pytest.mark.parametrize('role',['Public','ExternalExpert','InterestedState','AgentService'])
def test_denial_before_case_and_payload(client,role):
    a=client.post(url(),content=b'bad',headers={'X-MCIS-Role':role})
    b=client.post(url('MISSING'),content=b'bad',headers={'X-MCIS-Role':role})
    assert a.status_code==b.status_code==403 and a.json()==b.json()


def test_source_scope_and_only_snapshot_fields(client):
    out=client.get(url(action='sources'));assert out.status_code==200
    assert len(out.json()['sources'])==1 and set(out.json()['sources'][0])=={'evidenceId','title','sha256'}
    assert client.post(url(),json={'parameters':parameters(),'sourceEvidenceIds':['EV-002']}).status_code==403

@pytest.mark.parametrize('change',['source','policy','case'])
def test_recheck_after_real_cli(client,monkeypatch,change):
    original=r.run_core
    def changed(m):
        result=original(m)
        with client.app.state.db.session() as s:
            if change=='source':put_doc(s,EvidenceRow,'CASE-A','EV-001',{'caseId':'CASE-A','evidenceId':'EV-001','title':'changed','sha256':'c'*64,'confidentiality':'Normal'})
            if change=='policy':
                p=default_policy();p['matrix']['Investigator']['personal']='Deny';put_doc(s,AccessPolicyRow,'CASE-A','policy',p)
            if change=='case':put_doc(s,CaseRow,'CASE-A','CASE-A',{'caseId':'CASE-A','title':'changed'})
        return result
    monkeypatch.setattr(r,'run_core',changed)
    out=client.post(url(),json={'parameters':parameters(),'sourceEvidenceIds':['EV-001']})
    assert out.status_code==(403 if change=='policy' else 409),out.text
    assert 'result' not in out.json()

def test_missing_core_no_fallback(client,monkeypatch,tmp_path):
    monkeypatch.setattr(r,'CLI',tmp_path/'absent')
    out=client.post(url(),json={'parameters':parameters(),'sourceEvidenceIds':[]})
    assert out.status_code==503 and 'result' not in out.json()


def test_restricted_source_and_snapshot_visibility(client):
    with client.app.state.db.session() as s:
        put_doc(s,EvidenceRow,'CASE-A','EV-003',{'caseId':'CASE-A','evidenceId':'EV-003','title':'must not leak','sha256':'d'*64,'confidentiality':'Restricted'})
        p=default_policy();p['fieldRules'].append({'ruleId':'DENY-TEST','field':'evidence.restricted','method':'Remove','appliesTo':['Investigator']})
        put_doc(s,AccessPolicyRow,'CASE-A','policy',p)
    out=client.get(url(action='sources'));assert out.status_code==200 and 'must not leak' not in out.text
    out=client.post(url(),json={'parameters':parameters(),'sourceEvidenceIds':['EV-003']})
    assert out.status_code==403 and 'must not leak' not in out.text

@pytest.mark.parametrize('length,status',[(1000,200),(1001,422)])
def test_unicode_scalar_label_limit(client,length,status):
    m=parameters();m['provenanceNote']='🛳'*length
    out=client.post(url(),json={'parameters':m,'sourceEvidenceIds':[]})
    assert out.status_code==status,out.text
    if status==200:assert out.json()['result']==run(m)


def test_decimal_text_not_float_digest(client):
    a=parameters(speedKn='10');b=parameters(speedKn='10.0')
    x=client.post(url(),json={'parameters':a,'sourceEvidenceIds':[]}).json()
    y=client.post(url(),json={'parameters':b,'sourceEvidenceIds':[]}).json()
    assert x['inputSha256']!=y['inputSha256'] and x['result']==y['result']
