"""W15.3 uses only synthetic cases; fake core tests are separated from real CLI."""
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

api = importlib.import_module('mcis_service.bowtie_preview.router')
CASE='CASE-SYNTHETIC-BOWTIE'
URL=f'/api/v1/cases/{CASE}/systemic/bowtie:preview'
SOURCES=f'/api/v1/cases/{CASE}/systemic/bowtie:sources'


def body():
    return {'model':{'hazard':'Synthetic navigation energy','topEvent':{'id':'top','label':'Hypothetical loss of control'},
        'nodes':[{'id':'threat','label':'Hypothetical threat','kind':'Threat','barrierId':None},
                 {'id':'consequence','label':'Hypothetical consequence','kind':'Consequence','barrierId':None}],
        'edges':[{'fromId':'threat','toId':'top'},{'fromId':'top','toId':'consequence'}]},'sourceEvidenceIds':[]}


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
            put_doc(s,CaseRow,CASE,CASE,{'caseId':CASE,'title':'Synthetic bowtie','isFictionalDemo':True})
        source(app.state.db)
        yield client,app.state.db


def valid_result():
    return {'coreVersion':'mcis-bowtie/1','mode':'hypothesis-structure-only','constructionErrors':[],
            'validationIssues':[],'structureValid':True,'notCheckedRefCount':0,'nodeCount':3,'edgeCount':2}


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
    data=response.json(); assert data['profile']=='MCIS-BOWTIE-PREVIEW-1'
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


@pytest.mark.parametrize('mutation',['unknown','status','refs','untrimmed','empty','long','id','kind','null_barrier',
    'unexpected_barrier','too_many_nodes','too_many_edges','too_many_sources','duplicate_source','bad_source'])
def test_schema_rejects_not_graph_algorithm(preview,mutation):
    client,_=preview; value=body(); model=value['model']
    if mutation=='unknown': value['extra']=1
    elif mutation in ('status','refs'): model['nodes'][0][mutation]='Strong'
    elif mutation=='untrimmed': model['hazard']=' x '
    elif mutation=='empty': model['topEvent']['label']=''
    elif mutation=='long': model['hazard']='x'*501
    elif mutation=='id': model['topEvent']['id']='bad.id'
    elif mutation=='kind': model['nodes'][0]['kind']='TopEvent'
    elif mutation=='null_barrier': model['nodes'][0]['kind']='EscalationFactor'
    elif mutation=='unexpected_barrier': model['nodes'][0]['barrierId']='barrier'
    elif mutation=='too_many_nodes': model['nodes']*=33
    elif mutation=='too_many_edges': model['edges']*=65
    elif mutation=='too_many_sources': value['sourceEvidenceIds']=[f'EV-{i:03}' for i in range(9)]
    elif mutation=='duplicate_source': value['sourceEvidenceIds']=['EV-981','EV-981']
    else: value['sourceEvidenceIds']=['bad']
    assert client.post(URL,json=value,headers=H()).status_code==422


@pytest.mark.parametrize('ids',[[],['EV-981']])
def test_zero_or_bound_sources_hash_and_no_writes(preview,fake_core,ids):
    client,db=preview; value=body(); value['sourceEvidenceIds']=ids; statements=[]
    def capture(conn,cursor,statement,parameters,context,executemany): statements.append(statement.strip().split()[0].upper())
    event.listen(db.engine,'before_cursor_execute',capture)
    try: response=client.post(URL,json=value,headers=H())
    finally: event.remove(db.engine,'before_cursor_execute',capture)
    assert response.status_code==200,response.text
    result=response.json()
    assert result['inputSha256']==hashlib.sha256(api.canonical({'caseId':CASE,'model':value['model'],'sources':result['sources']})).hexdigest()
    assert result['persisted'] is False and result['assessment']=='hypothesis-structure-only'
    assert result['sourceRole']=='Investigator' and result['limitations']
    assert response.headers['cache-control']=='no-store'
    assert not {'INSERT','UPDATE','DELETE','REPLACE','CREATE','DROP','ALTER'}.intersection(statements)


@pytest.mark.parametrize('change,status',[('policy',409),('source',409),('revoke',403)])
def test_changes_during_core_suppress_results(preview,fake_core,monkeypatch,change,status):
    client,db=preview; value=body(); value['sourceEvidenceIds']=['EV-981']
    def changed(_):
        if change=='source': source(db,title='changed')
        else:
            policy=default_policy()
            if change=='revoke': policy['matrix']['Investigator']['personal']='Deny'
            else: policy['version']='new'
            save_policy(db,policy)
        return fake_core
    monkeypatch.setattr(api,'run_core',changed)
    response=client.post(URL,json=value,headers=H())
    assert response.status_code==status and 'result' not in response.json()


def test_core_absent_no_fallback(preview,monkeypatch,tmp_path):
    client,_=preview; monkeypatch.setattr(api,'CLI',tmp_path/'missing')
    assert client.post(URL,json=body(),headers=H()).status_code==503


@pytest.mark.parametrize('mutation',['version','mode','nan','bool_count','count','refs','unknown','contradiction','severity','code','partial'])
def test_bad_core_output_rejected(preview,monkeypatch,mutation):
    client,_=preview; result=valid_result()
    if mutation=='version': result['coreVersion']='unknown'
    elif mutation=='mode': result['mode']='confirmed'
    elif mutation=='nan': result['nodeCount']=float('nan')
    elif mutation=='bool_count': result['nodeCount']=True
    elif mutation=='count': result['edgeCount']=1
    elif mutation=='refs': result['notCheckedRefCount']=1
    elif mutation=='unknown': result['isValid']=True
    elif mutation=='contradiction': result['structureValid']=False
    elif mutation in ('severity','code'):
        result['validationIssues']=[{'code':'sys_orphan_threat','elementId':'threat','message':'orphan','severity':'Error'}]
        result['structureValid']=False
        result['validationIssues'][0]['severity' if mutation=='severity' else 'code']='unknown'
    else:
        result['constructionErrors']=[{'code':'sys_unknown_node','elementId':'missing','message':'missing'}]
        result['structureValid']=False
    monkeypatch.setattr(api.subprocess,'run',lambda *a,**kw:subprocess.CompletedProcess(a,0,json.dumps({'ok':True,'result':result}).encode(),b''))
    response=client.post(URL,json=body(),headers=H())
    assert response.status_code==503 and 'result' not in response.json()


@pytest.mark.parametrize('mode',['valid','empty','duplicate_node','duplicate_edge','unknown_endpoint','escalation'])
def test_real_cli_graph_diagnostics(preview,mode):
    client,_=preview
    if not api.CLI.is_file(): pytest.skip('CLI not yet built')
    value=body(); model=value['model']
    if mode=='empty': model['nodes']=[]; model['edges']=[]
    elif mode=='duplicate_node': model['nodes'].append(copy.deepcopy(model['nodes'][0]))
    elif mode=='duplicate_edge': model['edges'].append(copy.deepcopy(model['edges'][0]))
    elif mode=='unknown_endpoint': model['edges'][0]['fromId']='missing'
    elif mode=='escalation':
        model['nodes'].insert(0,{'id':'esc','label':'Hypothetical escalation','kind':'EscalationFactor','barrierId':'barrier'})
        model['nodes'].append({'id':'barrier','label':'Hypothetical barrier','kind':'PreventionBarrier','barrierId':None})
    response=client.post(URL,json=value,headers=H()); assert response.status_code==200,response.text
    result=response.json()['result']
    assert result['coreVersion']=='mcis-bowtie/1' and result['notCheckedRefCount']==0
    if mode=='valid': assert result['structureValid'] and result['nodeCount']==3 and result['edgeCount']==2
    elif mode in ('duplicate_node','duplicate_edge','unknown_endpoint'):
        assert result['constructionErrors'] and not result['structureValid'] and not result['validationIssues']
    else: assert result['validationIssues'] and not result['structureValid']


@pytest.mark.parametrize('top_id,count',[('_top',0),('top',1)])
def test_real_cli_core_id_rejection_preserved(preview,top_id,count):
    client,_=preview
    if not api.CLI.is_file(): pytest.skip('CLI not yet built')
    value=body(); value['model']['topEvent']['id']=top_id; value['model']['nodes'][0]['id']='_threat'
    response=client.post(URL,json=value,headers=H()); assert response.status_code==200,response.text
    result=response.json()['result']
    assert result['constructionErrors'][0]['code']=='sys_invalid_id'
    assert result['nodeCount']==count and result['edgeCount']==0 and result['structureValid'] is False


def test_real_cli_unicode_scalar_label(preview):
    client,_=preview
    if not api.CLI.is_file(): pytest.skip('CLI not yet built')
    value=body(); value['model']['hazard']='🚢'*500
    assert client.post(URL,json=value,headers=H()).status_code==200
