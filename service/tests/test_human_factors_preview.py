import copy
import hashlib
import importlib
import json
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from .conftest import H, make_settings
from mcis_service.main import create_app
from mcis_service.cases.models import CaseRow

CASE = "CASE-SYNTHETIC-REST"
from mcis_service.db import put_doc
from mcis_service.evidence.models import EvidenceRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy

api = importlib.import_module('mcis_service.human_factors_preview.router')
URL = f'/api/v1/cases/{CASE}/human-factors/rest:preview'
SOURCES = f'/api/v1/cases/{CASE}/human-factors/rest:sources'


def body():
    return {'recordStartUtc': '2026-01-01T00:00:00Z', 'recordEndUtc': '2026-01-02T00:00:00Z',
            'intervals': [{'startUtc': '2026-01-01T00:00:00Z', 'endUtc': '2026-01-01T10:00:00Z', 'kind': 'Rest'},
                          {'startUtc': '2026-01-01T10:00:00Z', 'endUtc': '2026-01-02T00:00:00Z', 'kind': 'Watch'}],
            'sourceEvidenceIds': ['EV-981']}


def source(db, case_id=CASE, **changes):
    doc = dict(evidenceId='EV-981', caseId=case_id, title='Synthetic rest source', sha256='a'*64,
               confidentiality='Normal', source='DO NOT RETURN', extractedBy='DO NOT RETURN', note='DO NOT RETURN')
    doc.update(changes)
    with db.session() as s: put_doc(s, EvidenceRow, case_id, doc['evidenceId'], doc)
    return doc


@pytest.fixture()
def app(tmp_path):
    # Never load demo seed or public real-case reports in this feature suite.
    return create_app(make_settings(tmp_path, seed=False))


@pytest.fixture()
def preview(app):
    if not any(getattr(r, "path", "") == "/api/v1/cases/{case_id}/human-factors/rest:preview" for r in app.routes):
        app.include_router(api.router)
    with TestClient(app) as client:
        with app.state.db.session() as session:
            put_doc(session, CaseRow, CASE, CASE, {"caseId": CASE, "title": "Synthetic rest fixture", "isFictionalDemo": True})
        source(app.state.db)
        yield client, app.state.db


@pytest.fixture()
def fake_core(monkeypatch):
    # Test double only for permission/race tests; real CLI has a separate test below.
    result = {'coreVersion':'test-double','mode':'rest-baseline-no-exceptions','totals':{},'coverage':{},
              'findings':[], 'insufficientData':[], 'assumptions':[]}
    monkeypatch.setattr(api, 'run_core', lambda _: copy.deepcopy(result))
    return result


def save_policy(db, policy):
    with db.session() as s: put_doc(s, AccessPolicyRow, CASE, 'policy', policy)


def test_source_listing_minimal_and_scoped(preview):
    client, db = preview
    source(db, 'CASE-OTHER', evidenceId='EV-982')
    result = client.get(SOURCES, headers=H())
    assert result.status_code == 200 and result.headers['cache-control'] == 'no-store'
    assert result.json()['sourceBinding'] == 'registered-metadata-only'
    docs = result.json()['sources']
    assert all(set(item) == {'evidenceId','title','sha256'} for item in docs)
    assert 'EV-982' not in [item['evidenceId'] for item in docs]
    assert 'DO NOT RETURN' not in result.text


@pytest.mark.parametrize('role', ['Public','ExternalExpert','InterestedState','AgentService'])
def test_role_denied_before_input_or_case_details(preview, role):
    client, _ = preview
    a = client.post(URL, content=b'broken', headers=H(role))
    b = client.post(URL.replace(CASE, 'MISSING'), content=b'broken', headers=H(role))
    assert a.status_code == b.status_code == 403 and a.json() == b.json()
    assert a.headers['cache-control'] == 'no-store'
    assert client.get(SOURCES, headers=H(role)).status_code == 403


@pytest.mark.parametrize('category', ['personal','evidence_meta'])
@pytest.mark.parametrize('level', ['Deny','Redacted',None,'Unknown'])
def test_full_permission_required(preview, category, level):
    client, db = preview
    policy = default_policy(); policy['matrix']['Investigator'][category] = level; save_policy(db, policy)
    assert client.post(URL, json=body(), headers=H()).status_code == 403
    assert client.get(SOURCES, headers=H()).status_code == 403


@pytest.mark.parametrize('raw', [b'{"recordStartUtc":1,"recordStartUtc":2}', b'NaN', b'1e999', b'"\\ud800"', b'['*80+b'0'+b']'*80])
def test_bad_json(preview, raw):
    client, _ = preview
    assert client.post(URL, content=raw, headers={**H(), 'Content-Type':'application/json'}).status_code == 422


@pytest.mark.parametrize('mutation', ['unknown','interval_unknown','no_sources','too_many_sources','duplicate_source','threshold',
    'naive','fraction','year','too_long','zero_window','no_intervals','too_many_intervals','overlap','kind','out_of_bounds'])
def test_strict_schedule(preview, mutation):
    client, _ = preview; value = body()
    if mutation in ('unknown','threshold'): value[mutation] = 10
    elif mutation == 'interval_unknown': value['intervals'][0]['extra'] = 'value'
    elif mutation == 'no_sources': value['sourceEvidenceIds'] = []
    elif mutation == 'too_many_sources': value['sourceEvidenceIds'] = [f'EV-{i:03}' for i in range(9)]
    elif mutation == 'duplicate_source': value['sourceEvidenceIds'] *= 2
    elif mutation == 'naive': value['recordStartUtc'] = '2026-01-01T00:00:00'
    elif mutation == 'fraction': value['recordStartUtc'] = '2026-01-01T00:00:00.0Z'
    elif mutation == 'year': value['recordStartUtc'] = '1899-01-01T00:00:00Z'
    elif mutation == 'too_long': value['recordEndUtc'] = '2026-02-01T00:00:00Z'
    elif mutation == 'zero_window': value['recordEndUtc'] = value['recordStartUtc']
    elif mutation == 'no_intervals': value['intervals'] = []
    elif mutation == 'too_many_intervals': value['intervals'] *= 129
    elif mutation == 'overlap': value['intervals'][1]['startUtc'] = '2026-01-01T09:00:00Z'
    elif mutation == 'kind': value['intervals'][0]['kind'] = 'Sleep'
    else: value['intervals'][0]['startUtc'] = '2025-12-31T00:00:00Z'
    assert client.post(URL, json=value, headers=H()).status_code == 422


def test_size_bound(preview):
    client, _ = preview
    assert client.post(URL, content=b' '* (api.MAX_BYTES+1), headers={**H(), 'Content-Type':'application/json'}).status_code == 413


def test_cross_case_missing_source_denied(preview):
    client, db = preview
    source(db,'CASE-OTHER', evidenceId='EV-982')
    value=body(); value['sourceEvidenceIds']=['EV-982']
    assert client.post(URL, json=value, headers=H()).status_code == 403


def test_confidentiality_filter(preview):
    client, db = preview; source(db, confidentiality='Restricted')
    policy = default_policy(); policy['matrix']['Investigator']['testimony']='Deny'; save_policy(db,policy)
    docs = client.get(SOURCES,headers=H()).json()['sources']
    assert 'EV-981' not in [d['evidenceId'] for d in docs]
    assert client.post(URL,json=body(),headers=H()).status_code == 403


def test_bound_hash_no_writes(preview,fake_core):
    client, db = preview; statements=[]
    def capture(conn,cursor,statement,parameters,context,executemany): statements.append(statement.strip().split()[0].upper())
    event.listen(db.engine,'before_cursor_execute',capture)
    try:
        result=client.post(URL,json=body(),headers=H())
    finally: event.remove(db.engine,'before_cursor_execute',capture)
    assert result.status_code == 200 and result.headers['cache-control']=='no-store'
    doc=result.json(); schedule={k:v for k,v in body().items() if k!='sourceEvidenceIds'}
    assert doc['inputSha256']==hashlib.sha256(api.canonical({'caseId':CASE,'schedule':schedule,'sources':doc['sources']})).hexdigest()
    assert doc['persisted'] is False and doc['assessment']=='technical-preview-only'
    assert doc['sourceRole']=='Investigator' and doc['limitations']
    assert not {'INSERT','UPDATE','DELETE','REPLACE','CREATE','DROP','ALTER'}.intersection(statements)


@pytest.mark.parametrize('change,status', [('deny',403),('policy',409),('source',409)])
def test_context_rechecked_after_computation(preview, fake_core, monkeypatch, change, status):
    client, db=preview
    def changed(_):
        if change=='source': source(db,title='new title')
        else:
            policy=default_policy()
            if change=='deny': policy['matrix']['Investigator']['personal']='Deny'
            else: policy['version']='changed'
            save_policy(db,policy)
        return fake_core
    monkeypatch.setattr(api,'run_core',changed)
    response=client.post(URL,json=body(),headers=H())
    assert response.status_code==status and 'result' not in response.json()
    assert response.headers['cache-control']=='no-store'


def test_cli_unavailable_no_fallback(preview,monkeypatch,tmp_path):
    client,_=preview; monkeypatch.setattr(api,'CLI',tmp_path/'absent-command')
    response=client.post(URL,json=body(),headers=H())
    assert response.status_code==503 and 'result' not in response.json()


def test_real_cli_synthetic_integration(preview):
    client,_=preview
    if not api.CLI.is_file(): pytest.skip('real CLI not installed yet')
    response=client.post(URL,json=body(),headers=H())
    assert response.status_code==200, response.text
    doc=response.json()
    assert doc['result']['coreVersion']=='mcis-rest/1'
    assert doc['result']['totals']['restHours']==10
    assert doc['result']['coverage']['has24hWindow'] is True
    assert doc['result']['coverage']['has7dWindow'] is False
    # Missing complete 7-day windows are declared by coverage, not invented core findings.
    assert isinstance(doc['result']['insufficientData'], list)
    assert 'iscompliant' not in response.text.lower()


def test_requires_json_content_type(preview):
    client,_=preview
    assert client.post(URL,content=json.dumps(body()),headers=H()).status_code==415


def valid_result():
    return {'coreVersion':'mcis-rest/1','mode':'rest-baseline-no-exceptions',
            'totals':{'restHours':10,'workHours':14,'unknownHours':0},
            'coverage':{'recordHours':24,'has24hWindow':True,'has7dWindow':False,'unknownHours':0},
            'findings':[],'insufficientData':[],'assumptions':['Project technical assumptions, not legal compliance.']}


@pytest.mark.parametrize('mutation',['version','mode','nan','bool','totals','coverage','unknownHours','legal','empty_assumptions',
    'unknown_rule','bad_stamp','oversize_findings','bad_error_envelope'])
def test_bad_core_output_fails_closed(preview,monkeypatch,mutation):
    import subprocess
    client,_=preview; result=valid_result(); rc=0
    if mutation=='version': result['coreVersion']='unknown'
    elif mutation=='mode': result['mode']='work-limits'
    elif mutation=='nan': result['totals']['restHours']=float('nan')
    elif mutation=='bool': result['totals']['restHours']=True
    elif mutation=='totals': result['totals']['restHours']=9
    elif mutation=='coverage': result['coverage']['has7dWindow']=True
    elif mutation=='unknownHours': result['coverage']['unknownHours']=1
    elif mutation=='legal': result['isCompliant']=True
    elif mutation=='empty_assumptions': result['assumptions']=[]
    elif mutation=='oversize_findings': result['findings']=[{}]*4097
    elif mutation=='bad_error_envelope': rc=4
    else:
        result['findings']=[dict(rule='Rest24h',windowStartUtc='2026-01-01T00:00:00.0000000Z',
            windowEndUtc='2026-01-02T00:00:00.0000000Z', actualHours=9,limitHours=10,
            violatingFromUtc='2026-01-01T00:00:00.0000000Z',violatingToUtc='2026-01-01T00:00:00.0000000Z',clause='x',detail='x')]
        if mutation=='unknown_rule': result['findings'][0]['rule']='UnknownRule'
        else: result['findings'][0]['windowStartUtc']='bad time'
    monkeypatch.setattr(api.subprocess,'run',lambda *a,**k:subprocess.CompletedProcess(a,rc,json.dumps({'ok':True,'result':result}).encode(),b''))
    response=client.post(URL,json=body(),headers=H())
    assert response.status_code==503 and 'result' not in response.json()


def test_real_cli_short_record_and_unknown_gap(preview):
    client,_=preview
    if not api.CLI.is_file(): pytest.skip('real CLI not installed yet')
    value=body(); value['recordEndUtc']='2026-01-01T12:00:00Z'; value['intervals']=value['intervals'][:1]
    response=client.post(URL,json=value,headers=H())
    assert response.status_code==200,response.text
    result=response.json()['result']
    assert result['coverage']['has24hWindow'] is False and result['coverage']['has7dWindow'] is False
    assert result['totals']=={'restHours':10,'workHours':0,'unknownHours':2}


def test_mismatched_source_row_identifier_rejected(preview):
    client,db=preview
    doc=source(db); doc['evidenceId']='EV-982'
    with db.session() as s: put_doc(s,EvidenceRow,CASE,'EV-981',doc)
    value=body(); value['sourceEvidenceIds']=['EV-981','EV-982']
    assert client.post(URL,json=value,headers=H()).status_code==403


def test_real_cli_split_limit_is_hours_not_number_of_segments(preview):
    client,_=preview
    if not api.CLI.is_file(): pytest.skip('real CLI not installed yet')
    value=body()
    edges=[(0,4,'Rest'),(4,6,'Watch'),(6,10,'Rest'),(10,12,'Watch'),(12,16,'Rest'),(16,24,'Watch')]
    def stamp(hour):
        return '2026-01-02T00:00:00Z' if hour==24 else f'2026-01-01T{hour:02}:00:00Z'
    value['intervals']=[{'startUtc':stamp(a),'endUtc':stamp(b),'kind':kind} for a,b,kind in edges]
    response=client.post(URL,json=value,headers=H())
    assert response.status_code==200,response.text
    result=response.json()['result']
    split=[row for row in result['findings']+result['insufficientData'] if row['rule']=='RestSplit']
    assert split and all(row['limitHours']==10 for row in split)
