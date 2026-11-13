"""Actual intake bytes + SQLite + preview service; controlled core unless marked."""
import base64
import copy
import pytest
from .conftest import C, H
from .test_align_preview_w41 import result
from mcis_service.timeline import align_preview

URL=C+'/timeline/registered-align-preview'
RAW=b'utc,heading\n2026-05-18T06:15:00Z,45\n'


def register(client, raw=RAW, filename='fictional.csv'):
    body={'profile':'mcis-evidence-intake-v1','fileName':filename,'contentBase64':base64.b64encode(raw).decode(),
          'title':'虚构CSV','source':'虚构测试','extractedBy':'测试','extractedUtc':'2026-01-01T00:00:00Z',
          'category':'AIS','confidentiality':'Restricted','note':''}
    preview=client.post(C+'/evidence-intakes:preview',headers=H(),json=body)
    assert preview.status_code==200,preview.text
    response=client.post(C+'/evidence-intakes:commit',headers=H(),json={**body,'confirmed':True,'requestDigest':preview.json()['requestDigest']})
    assert response.status_code==200,response.text
    return response.json()


def request(receipt):
    return {'sources':[{'evidenceId':receipt['evidenceId'],'csvMapping':{'timeColumn':'utc','columns':[{'column':'heading','kind':'Heading'}]}}]}


def test_actual_registered_bytes_are_used_and_not_mutated(client,monkeypatch):
    r=register(client);calls=[]
    def core(*args):
        calls.append(args[2]);return result(args[2])
    monkeypatch.setattr(align_preview,'core_run',core)
    from .test_binding_review_independent import snapshot
    before=snapshot(client)
    response=client.post(URL,headers=H(),json=request(r))
    assert response.status_code==200,response.text
    assert snapshot(client)==before
    assert calls[0]['sources'][0]['text']==RAW.decode()
    assert calls[0]['sources'][0]['sourceId']==r['evidenceId']
    data=response.json()
    assert data['persisted'] is False and data['observationApproval']=='not_assessed'
    assert data['sourceSnapshots'][0]['sourceSha256']==r['sourceSha256']
    assert response.headers['cache-control']=='no-store'
    path=client.app.state.settings.blob_dir/r['caseId']/r['evidence']['relativePath']
    assert path.read_bytes()==RAW


@pytest.mark.parametrize('change',['bytes','revoke','review'])
def test_mid_compute_changes_discard_result(client,monkeypatch,change):
    r=register(client)
    def core(*args):
        if change=='bytes':
            path=client.app.state.settings.blob_dir/r['caseId']/r['evidence']['relativePath']
            path.write_bytes(RAW.replace(b'45',b'90')) # explicit test-only tamper
        elif change=='revoke':
            from mcis_service.redaction.policy import default_policy
            p=default_policy();p['matrix']['Investigator']['evidence_meta']='Deny'
            assert client.put(C+'/access-policy',headers=H('LeadInvestigator'),json=p).status_code==200
        else:
            assert client.patch(C+'/evidence/'+r['evidenceId'],headers=H(),json={'needsReview':True,'reason':'模拟复核'}).status_code==200
        return result(args[2])
    monkeypatch.setattr(align_preview,'core_run',core)
    response=client.post(URL,headers=H(),json=request(r))
    assert response.status_code==(403 if change=='revoke' else 409),response.text
    assert 'result' not in response.json()


@pytest.mark.parametrize('raw,filename',[(b'\xff','x.csv'),(RAW,'x.txt')])
def test_unsupported_files_do_not_call_core(client,monkeypatch,raw,filename):
    r=register(client,raw,filename)
    def unexpected(*_):raise AssertionError('core must not execute')
    monkeypatch.setattr(align_preview,'core_run',unexpected)
    assert client.post(URL,headers=H(),json=request(r)).status_code==422


def test_caller_cannot_supply_source_text_or_approval(client,monkeypatch):
    r=register(client);body=request(r);body['sources'][0]['text']='fake bytes'
    assert client.post(URL,headers=H(),json=body).status_code==422
    body=request(r);body['observationApproval']='approved'
    assert client.post(URL,headers=H(),json=body).status_code==422


@pytest.mark.parametrize('value',['=1+1','NaN','Infinity','-1','361'])
def test_bad_numeric_observation_never_calls_core(client,monkeypatch,value):
    r=register(client,RAW.replace(b'45',value.encode()))
    def unexpected(*_):raise AssertionError('core must not execute')
    monkeypatch.setattr(align_preview,'core_run',unexpected)
    response=client.post(URL,headers=H(),json=request(r))
    assert response.status_code==422 and response.json()['code']=='TIMELINE_SOURCE_CSV'


def test_actual_core_registered_csv_preview(client):
    import os
    wrapper=os.environ.get('MCIS_ACCEPTANCE_CORE')
    if not wrapper: pytest.skip('requires actual built core wrapper')
    client.app.state.settings.core_cmd=wrapper
    a=register(client);b=register(client,RAW.replace(b'45',b'50'), 'fictional-second.csv')
    body={'sources':request(a)['sources']+request(b)['sources']}
    response=client.post(URL,headers=H(),json=body)
    assert response.status_code==200,response.text
    assert response.json()['result']['conflicts'][0]['delta']==5
    assert response.json()['observationApproval']=='not_assessed'


def test_loopback_http_registered_preview_with_actual_core(app):
    import os
    import socket
    import threading
    import time
    import httpx
    import uvicorn
    wrapper=os.environ.get('MCIS_ACCEPTANCE_CORE')
    if not wrapper: pytest.skip('requires actual built core wrapper')
    app.state.settings.core_cmd=wrapper
    sock=socket.socket();sock.bind(('127.0.0.1',0))
    port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,log_level='error'))
    thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True)
    thread.start()
    try:
        deadline=time.monotonic()+10
        while not server.started and thread.is_alive() and time.monotonic()<deadline: time.sleep(.02)
        assert server.started
        with httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=20,trust_env=False) as client:
            a=register(client);b=register(client,RAW.replace(b'45',b'50'),'network-second.csv')
            response=client.post(URL,headers=H(),json={'sources':request(a)['sources']+request(b)['sources']})
            assert response.status_code==200,response.text
            assert response.json()['result']['conflicts'][0]['delta']==5
            assert response.json()['persisted'] is False
    finally:
        server.should_exit=True;thread.join(10);sock.close()
        assert not thread.is_alive()


@pytest.mark.parametrize('value',['1_0','１２','٠١'])
def test_nonportable_numeric_grammar_is_rejected(client,monkeypatch,value):
    r=register(client,RAW.replace(b'45',value.encode()))
    def unexpected(*_):raise AssertionError('core must not execute')
    monkeypatch.setattr(align_preview,'core_run',unexpected)
    response=client.post(URL,headers=H(),json=request(r))
    assert response.status_code==422 and response.json()['code']=='TIMELINE_SOURCE_CSV'


def test_core_import_error_is_not_successful_no_conflict(client,monkeypatch):
    r=register(client)
    def core(*args):
        env=result(args[2]);env['result']['importDiagnostics']=[{'sourceId':r['evidenceId'],
            'severity':'Error','code':'vdr_csv_bad_value','message':'invalid value','lineNumber':2}]
        return env
    monkeypatch.setattr(align_preview,'core_run',core)
    response=client.post(URL,headers=H(),json=request(r))
    assert response.status_code==422,response.text
    assert response.json()['code']=='TIMELINE_SOURCE_CORE_DIAGNOSTIC'
