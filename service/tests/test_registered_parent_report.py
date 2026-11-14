"""Transient byte linkage, not fact or PDF-content validation."""
import base64
import copy
import os
from pathlib import Path
import pytest
from .conftest import C, H
from .test_registered_align_preview import register, request, URL, RAW
from .test_align_preview_w41 import result
from .test_binding_review_independent import snapshot
from mcis_service.timeline import align_preview

PDF=b'%PDF-1.7\nsynthetic opaque fixture, not an actual report\n'
CTX={'vesselLabel':'fictional vessel','sourceNature':'report_extract','sourceTitle':'fixture report','citation':'p1','timeBasis':'declared UTC','headingReference':'true'}

def parent(client,raw=PDF,filename='fixture.pdf',category='Document',case=C):
    b={'profile':'mcis-evidence-intake-v1','fileName':filename,'contentBase64':base64.b64encode(raw).decode(),'title':'parent byte fixture','source':'synthetic','extractedBy':'test','extractedUtc':'2026-01-01T00:00:00Z','category':category,'confidentiality':'Restricted','note':''}
    p=client.post(case+'/evidence-intakes:preview',headers=H(),json=b);assert p.status_code==200,p.text
    r=client.post(case+'/evidence-intakes:commit',headers=H(),json={**b,'confirmed':True,'requestDigest':p.json()['requestDigest']});assert r.status_code==200,r.text
    return r.json()

def body(r,p):
    b=request(r);b['sources'][0].update(comparisonContext=CTX.copy(),parentReport={'evidenceId':p['evidenceId'],'sourceSha256':p['sourceSha256']});return b

def stub(monkeypatch):
    monkeypatch.setattr(align_preview,'core_run',lambda *args:result(args[2]))

def deny_core(monkeypatch):
    def unexpected(*args):raise AssertionError('must not compute')
    monkeypatch.setattr(align_preview,'core_run',unexpected)

def test_parent_snapshot_is_transient_declared_only_and_read_only(client,monkeypatch):
    r=register(client);p=parent(client);stub(monkeypatch);before=snapshot(client)
    res=client.post(URL,headers=H(),json=body(r,p));assert res.status_code==200,res.text
    assert snapshot(client)==before
    v=res.json();assert v['persisted'] is False and v['observationApproval']=='not_assessed'
    assert v['reportSnapshots']==[{'extractEvidenceId':r['evidenceId'],'evidenceId':p['evidenceId'],'sourceSha256':p['sourceSha256'],'registrationDigest':p['requestDigest'],'byteLength':len(PDF),'registeredUtc':p['registeredUtc'],'relationshipStatus':'user_declared_not_verified'}]
    assert 'parentReport' not in v['sourceSnapshots'][0]
    assert res.headers['cache-control']=='no-store'
    assert (client.app.state.settings.blob_dir/p['caseId']/p['evidence']['relativePath']).read_bytes()==PDF

@pytest.mark.parametrize('change',['wrong_sha','review','bytes','extension','category','legacy','foreign'])
def test_unacceptable_parent_stops_before_core(client,monkeypatch,change):
    r=register(client);p=parent(client,filename='fixture.txt' if change=='extension' else 'fixture.pdf',category='AIS' if change=='category' else 'Document',case='/api/v1/cases/CJK-2024-1230-YangZe22-VegaDream' if change=='foreign' else C)
    b=body(r,p)
    if change=='wrong_sha':b['sources'][0]['parentReport']['sourceSha256']='0'*64
    if change=='review':assert client.patch(C+'/evidence/'+p['evidenceId'],headers=H(),json={'needsReview':True,'reason':'test'}).status_code==200
    if change=='bytes':(client.app.state.settings.blob_dir/p['caseId']/p['evidence']['relativePath']).write_bytes(PDF+b'tampered')
    if change=='legacy':b['sources'][0]['parentReport']['evidenceId']='EV-001'
    deny_core(monkeypatch);res=client.post(URL,headers=H(),json=b)
    assert res.status_code in (404,409,422),res.text
    assert 'result' not in res.json()

@pytest.mark.parametrize('change',['bytes','review','revoke'])
def test_parent_change_during_compute_discards_preview(client,monkeypatch,change):
    r=register(client);p=parent(client)
    def core(*args):
        if change=='bytes':(client.app.state.settings.blob_dir/p['caseId']/p['evidence']['relativePath']).write_bytes(PDF+b'tampered')
        elif change=='review':assert client.patch(C+'/evidence/'+p['evidenceId'],headers=H(),json={'needsReview':True,'reason':'test'}).status_code==200
        else:
            from mcis_service.redaction.policy import default_policy
            policy=default_policy();policy['matrix']['Investigator']['testimony']='Deny'
            assert client.put(C+'/access-policy',headers=H('LeadInvestigator'),json=policy).status_code==200
        return result(args[2])
    monkeypatch.setattr(align_preview,'core_run',core)
    res=client.post(URL,headers=H(),json=body(r,p));assert res.status_code==(403 if change=='revoke' else 409),res.text
    assert 'result' not in res.json()

@pytest.mark.parametrize('change',['self','no_context','not_extract','cross_case','approval','bad_sha'])
def test_parent_declaration_shape_is_strict(client,monkeypatch,change):
    r=register(client);p=parent(client);b=body(r,p);s=b['sources'][0]
    if change=='self':s['parentReport']['evidenceId']=r['evidenceId']
    elif change=='no_context':s.pop('comparisonContext')
    elif change=='not_extract':s['comparisonContext']['sourceNature']='sensor_export'
    elif change=='cross_case':s['parentReport']['caseId']='other'
    elif change=='approval':s['parentReport']['approved']=True
    elif change=='bad_sha':s['parentReport']['sourceSha256']='0'*63
    deny_core(monkeypatch);assert client.post(URL,headers=H(),json=b).status_code==422

def test_legacy_without_parent_remains_supported(client,monkeypatch):
    r=register(client);stub(monkeypatch)
    res=client.post(URL,headers=H(),json=request(r));assert res.status_code==200,res.text
    assert res.json()['reportSnapshots']==[]

def test_shared_parent_is_two_unverified_links_not_independent_sources(client,monkeypatch):
    a=register(client);b=register(client,RAW.replace(b'45',b'50'),'second.csv');p=parent(client);stub(monkeypatch)
    res=client.post(URL,headers=H(),json={'sources':body(a,p)['sources']+body(b,p)['sources']});assert res.status_code==200,res.text
    links=res.json()['reportSnapshots'];assert len(links)==2
    assert len({x['evidenceId'] for x in links})==1
    assert all(x['relationshipStatus']=='user_declared_not_verified' for x in links)

def test_real_public_pdf_bytes_and_actual_w2(client):
    wrapper=os.environ.get('MCIS_ACCEPTANCE_CORE')
    if not wrapper:pytest.skip('actual W2 required')
    client.app.state.settings.core_cmd=wrapper
    pdf=(Path(__file__).resolve().parents[2]/'reports/yangze22/report.pdf').read_bytes()
    p=parent(client,pdf,'public-report.pdf');r=register(client)
    # Fixture CSV is deliberately NOT a true extraction of that report.
    # Server verifies bytes, not semantic relation; outcome must remain unverified.
    res=client.post(URL,headers=H(),json=body(r,p));assert res.status_code==200,res.text
    assert res.json()['reportSnapshots'][0]['byteLength']==len(pdf)
    assert res.json()['reportSnapshots'][0]['relationshipStatus']=='user_declared_not_verified'
    assert res.json()['observationApproval']=='not_assessed'
