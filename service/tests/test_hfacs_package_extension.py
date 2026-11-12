"""Synthetic complete HFACS archive restoration, never active replay credentials."""
import base64,copy,hashlib,io,json,uuid,zipfile
from contextlib import contextmanager
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,func
from .conftest import H,make_settings
from .test_package_intake_parser import base as base_files
from mcis_service.main import create_app
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.audit.models import AuditEventRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.package import mcase
from mcis_service.hfacs_drafts import archive
from mcis_service.hfacs_drafts.router import run_core
from mcis_service.hfacs_drafts.models import HfacsWorksheetRow,HfacsAuditRow,HfacsRequestRow,HfacsArchivedRequestRow
CASE='CASE-INTAKE'
BASE=f'/api/v1/cases/{CASE}'

@pytest.fixture(scope='module')
def code(): return run_core({'action':'taxonomy'})['categories'][0]['code']

@contextmanager
def client_at(path,create=False):
    app=create_app(make_settings(path,seed=False))
    with TestClient(app) as client:
        if create:
            with app.state.db.session() as s: put_doc(s,CaseRow,CASE,CASE,json.loads(base_files()['case.json']))
        yield client,app

@pytest.fixture()
def env(tmp_path,code):
    with client_at(tmp_path/'origin',True) as (client,app): yield client,app,code,tmp_path

def save(client,code,previous=None,sources=None):
    body={'requestId':str(uuid.uuid4()),'expectedDigest':previous['digest'] if previous else None,
          'draft':{'scope':'Synthetic context','entries':[{'id':'entry','categoryCode':code,'description':'Hypothesis','rationale':'Not confirmed'}]},'expectedSources':sources or []}
    response=client.post(BASE+'/human-factors/hfacs:save',json=body,headers=H())
    assert response.status_code==200,response.text
    return body,response.json()['document']

def export(client):
    result=client.get(BASE+'/export',headers=H());assert result.status_code==200,result.text
    assert result.headers['cache-control']=='no-store'
    return result.content

def unpack(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z: return {n:z.read(n) for n in z.namelist()}

def repack(files,version='1.1.0'):
    files={k:v for k,v in files.items() if k!='manifest.json'}
    files['manifest.json']=mcase.manifest_json(CASE,files,'2026-01-01T00:00:00Z',version).encode()
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
        for n,v in files.items(): z.writestr(n,v)
    return b.getvalue()

def preview(client,data): return client.post('/api/v1/packages/intakes:preview',json={'contentBase64':base64.b64encode(data).decode()},headers=H())

def commit(client,data):
    return client.post('/api/v1/packages/intakes:commit',json={'contentBase64':base64.b64encode(data).decode(),'sourceSha256':hashlib.sha256(data).hexdigest(),'confirmed':True},headers=H())

def counts(app):
    with app.state.db.session() as s: return tuple(s.scalar(select(func.count()).select_from(t)) for t in (CaseRow,HfacsWorksheetRow,HfacsAuditRow,HfacsRequestRow,HfacsArchivedRequestRow))

def test_complete_roundtrip_inert_receipts_then_continue_history(env):
    client,app,code,tmp=env
    first_request,first=save(client,code);_,second=save(client,code,first)
    data=export(client);files=unpack(data);original=json.loads(files[archive.PATH])
    assert json.loads(files['manifest.json'])['packageVersion']=='1.1.0'
    assert original['currentDocument']==second and len(original['revisionAudit'])==len(original['requestReceipts'])==2
    with client_at(tmp/'restore') as (restored,other_app):
        check=preview(restored,data);assert check.status_code==200,check.text
        summary=check.json()['hfacsExtension'];assert summary['revisionCount']==2 and summary['receiptMode']=='archive-only'
        done=commit(restored,data);assert done.status_code==200,done.text
        assert done.json()['hfacsExtension']==summary and counts(other_app)==(1,1,2,0,2)
        assert restored.get(BASE+'/human-factors/hfacs:draft',headers=H()).json()['document']==second
        replay=restored.post(BASE+'/human-factors/hfacs:save',json=first_request,headers=H())
        assert replay.status_code==409 and replay.json()['code']=='REQUEST_ARCHIVED'
        recovered=restored.get('/api/v1/packages/intakes/'+hashlib.sha256(data).hexdigest(),headers=H())
        assert recovered.status_code==200 and recovered.json()['hfacsExtension']==summary
        assert json.loads(unpack(export(restored))[archive.PATH])==original
        _,third=save(restored,code,second)
        assert third['revision']==3 and counts(other_app)==(1,1,3,1,2)
        second_package=export(restored);union=json.loads(unpack(second_package)[archive.PATH])
        assert len(union['requestReceipts'])==3 and all(r in union['requestReceipts'] for r in original['requestReceipts'])
    with client_at(tmp/'restore-again') as (restored,other_app):
        assert commit(restored,second_package).status_code==200
        assert counts(other_app)==(1,1,3,0,3)
        assert json.loads(unpack(export(restored))[archive.PATH])==union

def test_legacy_absence_and_old_entry_rejection(env):
    client,app,code,tmp=env
    basic=export(client);assert archive.PATH not in unpack(basic)
    with client_at(tmp/'old') as (target,_):
        result=preview(target,basic);assert result.status_code==200
        assert result.json()['packageVersion']=='1.0.0' and result.json()['hfacsExtension'] is None
    save(client,code);data=export(client)
    with client_at(tmp/'target') as (target,target_app):
        for version in ('1.1.0','1.0.0'):
            disguised=repack(unpack(data),version)
            assert target.post('/api/v1/cases:import',content=disguised,headers=H()).status_code==422
        files=unpack(data);files['HFACS/unknown.json']=files.pop(archive.PATH)
        assert target.post('/api/v1/cases:import',content=repack(files,'1.0.0'),headers=H()).status_code==422
        assert counts(target_app)==(0,0,0,0,0)

@pytest.mark.parametrize('mutation',['version','field','missing_history','hash','document_digest','source','receipt_id','receipt_response','receipt_digest','unknown_member','outer_version'])
def test_invalid_archive_rejected_without_partial_restore(env,mutation):
    client,app,code,tmp=env;save(client,code);files=unpack(export(client));doc=json.loads(files[archive.PATH])
    if mutation=='version': doc['version']=2
    elif mutation=='field':doc['extra']=1
    elif mutation=='missing_history':doc['revisionAudit']=[]
    elif mutation=='hash':doc['revisionAudit'][0]['hash']='1'*64
    elif mutation=='document_digest':doc['currentDocument']['digest']='1'*64
    elif mutation=='source':doc['currentDocument']['sources']=[{'evidenceId':'EV-999','title':'missing','sha256':'a'*64}]
    elif mutation=='receipt_id':doc['requestReceipts'][0]['request_id']=str(uuid.uuid4())
    elif mutation=='receipt_response':doc['requestReceipts'][0]['response']['persisted']=False
    elif mutation=='receipt_digest':doc['requestReceipts'][0]['request_digest']='invalid'
    elif mutation=='unknown_member':files['hfacs/unknown.json']=b'{}'
    files[archive.PATH]=json.dumps(doc).encode();data=repack(files,'2.0.0' if mutation=='outer_version' else '1.1.0')
    with client_at(tmp/'target') as (target,target_app):
        assert preview(target,data).status_code==422
        assert commit(target,data).status_code==422
        assert counts(target_app)==(0,0,0,0,0)

def test_resealed_unsupported_classification_rejected(env):
    client,app,code,tmp=env;save(client,code);files=unpack(export(client));data=json.loads(files[archive.PATH]);ev=data['revisionAudit'][0]
    ev['after']['classification']['taxonomyVersion']='unknown/2'
    ev['after']['digest']=archive.digest({k:ev['after'][k] for k in ('caseId','revision','draft','sources','classification')})
    ev['afterDigest']=ev['after']['digest'];ev['hash']=archive.digest({k:v for k,v in ev.items() if k!='hash'})
    data['currentDocument']=copy.deepcopy(ev['after']);data['requestReceipts'][0]['response']['document']=copy.deepcopy(ev['after'])
    files[archive.PATH]=json.dumps(data).encode()
    with client_at(tmp/'target') as (target,_):assert preview(target,repack(files)).status_code==422

@pytest.mark.parametrize('category',['personal','evidence_meta','agent_drafts','audit'])
def test_denied_export_leaves_no_export_audit(env,category):
    client,app,code,tmp=env;save(client,code)
    policy=default_policy();policy['matrix']['Investigator'][category]='Deny'
    with app.state.db.session() as s:
        put_doc(s,AccessPolicyRow,CASE,'policy',policy);before=s.scalar(select(func.count()).select_from(AuditEventRow))
    result=client.get(BASE+'/export',headers=H());assert result.status_code==403,result.text
    with app.state.db.session() as s: assert s.scalar(select(func.count()).select_from(AuditEventRow))==before

def test_nondefault_policy_and_other_business_complete_rejection(env):
    from mcis_service.timeline.models import TimelineEventRow
    client,app,code,tmp=env;save(client,code)
    policy=default_policy();policy['version']='custom'
    with app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',policy)
    assert client.get(BASE+'/export',headers=H()).status_code==422
    with app.state.db.session() as s:
        put_doc(s,AccessPolicyRow,CASE,'policy',default_policy());put_doc(s,TimelineEventRow,CASE,'test',{'eventId':'test'})
        before=s.scalar(select(func.count()).select_from(AuditEventRow))
    assert client.get(BASE+'/export',headers=H()).status_code==422
    with app.state.db.session() as s:assert s.scalar(select(func.count()).select_from(AuditEventRow))==before

def test_failure_after_archive_inserts_rolls_back_all(env,monkeypatch):
    client,app,code,tmp=env;save(client,code);data=export(client);original=archive.restore
    def failed(session,payload):
        original(session,payload)
        raise RuntimeError('synthetic failure after archive flush')
    monkeypatch.setattr(archive,'restore',failed)
    with client_at(tmp/'target') as (target,target_app):
        with pytest.raises(RuntimeError):commit(target,data)
        assert counts(target_app)==(0,0,0,0,0)
        assert not (target_app.state.settings.blob_dir/CASE).exists()

def test_all_historical_sources_checked_before_export(env):
    client,app,code,tmp=env
    registered=client.post(BASE+'/evidence',headers=H(),json={'title':'Synthetic source','source':'Synthetic fixture',
        'extractedBy':'Synthetic operator','fileName':'source.txt','contentBase64':base64.b64encode(b'synthetic source').decode()})
    assert registered.status_code==201,registered.text
    evidence=registered.json();snapshot={k:evidence[k] for k in ('evidenceId','title','sha256')}
    _,first=save(client,code,sources=[snapshot]);save(client,code,first)
    data=export(client)
    with client_at(tmp/'source-restore') as (target,_): assert commit(target,data).status_code==200
    # Current draft is source-free. A source used only in retained history must still gate export.
    from mcis_service.evidence.models import EvidenceRow
    with app.state.db.session() as s:
        row=s.scalars(select(EvidenceRow).where(EvidenceRow.case_id==CASE,EvidenceRow.key==evidence['evidenceId'])).one()
        doc=dict(row.doc);doc['confidentiality']='Restricted';row.doc=doc
        policy=default_policy();policy['matrix']['Investigator']['testimony']='Deny';put_doc(s,AccessPolicyRow,CASE,'policy',policy)
        before=s.scalar(select(func.count()).select_from(AuditEventRow))
    result=client.get(BASE+'/export',headers=H());assert result.status_code==403,result.text
    with app.state.db.session() as s: assert s.scalar(select(func.count()).select_from(AuditEventRow))==before

def test_archive_budget_rejects_whole_export_without_truncation(env,monkeypatch):
    client,app,code,tmp=env;_,one=save(client,code);save(client,code,one)
    with app.state.db.session() as s: before=s.scalar(select(func.count()).select_from(AuditEventRow))
    monkeypatch.setattr(archive,'MAX_REVISIONS',1)
    result=client.get(BASE+'/export',headers=H());assert result.status_code==422
    with app.state.db.session() as s: assert s.scalar(select(func.count()).select_from(AuditEventRow))==before

def test_export_includes_more_than_ui_fifty_history_records(env):
    client,app,code,tmp=env
    previous=None
    for _ in range(51): _,previous=save(client,code,previous)
    # UI summary is limited, archive is not sourced from that summary.
    summary=client.get(BASE+'/human-factors/hfacs:audit',headers=H()).json()['events'];assert len(summary)==50
    data=export(client);payload=json.loads(unpack(data)[archive.PATH])
    assert len(payload['revisionAudit'])==len(payload['requestReceipts'])==51
    assert payload['revisionAudit'][0]['revision']==1 and payload['revisionAudit'][-1]['revision']==51
    with client_at(tmp/'long-restore') as (target,target_app):
        result=commit(target,data);assert result.status_code==200,result.text
        assert counts(target_app)==(1,1,51,0,51)
