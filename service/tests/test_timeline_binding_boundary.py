"""Reserved authority namespace only; not functional source binding acceptance."""
import copy
import io
import hashlib
import json
import zipfile
import pytest
from sqlalchemy import inspect, text
from mcis_service.package.mcase import manifest_json
from mcis_service.agents.binding_boundary import FIELD
from .conftest import C, H

DRAFT = {'draftId':'AD-901','caseId':'CASE-BINDING-BOUNDARY','agent':'timeline',
         'kind':'timeline_anchor','targetEntityType':'timelineEvent',
         'payload':{'timeSec':1,'title':'虚构输入','kind':'Event'},
         'citations':[{'quote':'虚构引用'}],'status':'PendingReview'}


def counts(client):
    with client.app.state.db.session() as s:
        return {n:s.execute(text('SELECT count(*) FROM "'+n+'"')).scalar()
                for n in inspect(s.connection()).get_table_names()}


def package(draft=None, path=None):
    cid=DRAFT['caseId']
    files={'case.json':json.dumps({'caseId':cid,'caseEpochUtc':'2026-01-01T00:00:00Z'}).encode(),
           'agents/drafts.json':json.dumps([DRAFT if draft is None else draft]).encode(),
           'raw/unchanged.bin':b'fictional unchanged source'}
    files['evidence/index.json']=json.dumps([{'evidenceId':'EV-901','caseId':cid,
        'title':'虚构原件','source':'test','extractedBy':'test','extractedUtc':'2026-01-01T00:00:00Z',
        'sha256':hashlib.sha256(files['raw/unchanged.bin']).hexdigest(),
        'relativePath':'raw/unchanged.bin','confidentiality':'Normal'}]).encode()
    if path: files[path]=b'{"approved":true}' 
    files['manifest.json']=manifest_json(cid,files,'2026-01-01T00:00:00Z').encode()
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z:
        for name,data in files.items():z.writestr(name,data)
    return buf.getvalue()


@pytest.mark.parametrize('location',['root','payload'])
@pytest.mark.parametrize('value',[None,{}, {'approved':True,'receiptId':'forged'}])
def test_submit_rejects_reserved_authority_without_writes(client,location,value):
    d=copy.deepcopy(DRAFT);(d if location=='root' else d['payload'])[FIELD]=value
    before=counts(client)
    r=client.post(C+'/agents/drafts',json=d,headers=H('AgentService'))
    assert r.status_code==422 and r.json()['code']=='TIMELINE_BINDING_LOCAL_ONLY',r.text
    assert counts(client)==before


@pytest.mark.parametrize('location',['root','payload'])
def test_import_rejects_forged_authority_before_any_row_or_file(empty_client,location):
    d=copy.deepcopy(DRAFT);(d if location=='root' else d['payload'])[FIELD]={'approved':True}
    before=counts(empty_client);root=empty_client.app.state.settings.blob_dir
    before_files=sorted(str(p) for p in root.rglob('*')) if root.exists() else []
    r=empty_client.post('/api/v1/cases:import',content=package(d),headers=H('LeadInvestigator'))
    assert r.status_code==422 and r.json()['code']=='TIMELINE_BINDING_LOCAL_ONLY',r.text
    assert counts(empty_client)==before
    assert (sorted(str(p) for p in root.rglob('*')) if root.exists() else [])==before_files


@pytest.mark.parametrize('path',['timeline-bindings','timeline-bindings/receipt.json','TIMELINE-BINDINGS/r.json'])
def test_import_rejects_reserved_package_namespace(empty_client,path):
    before=counts(empty_client)
    r=empty_client.post('/api/v1/cases:import',content=package(path=path),headers=H('LeadInvestigator'))
    assert r.status_code==422 and r.json()['code']=='TIMELINE_BINDING_IMPORT_UNSUPPORTED',r.text
    assert counts(empty_client)==before
    assert not (empty_client.app.state.settings.blob_dir/DRAFT['caseId']).exists()


def test_legacy_unbound_package_roundtrip_and_similar_names_preserved(empty_client):
    # No widening into arbitrary nested metadata or similarly named file paths.
    d=copy.deepcopy(DRAFT);d['payload']['notes']={FIELD:'ordinary nested user annotation'}
    d['payload']['timelineSourceBindingNote']='not authority'
    r=empty_client.post('/api/v1/cases:import',content=package(d,path='timeline-bindings-notes/readme.txt'),headers=H('LeadInvestigator'))
    assert r.status_code==201,r.text
    cid=DRAFT['caseId']
    saved=empty_client.get(f'/api/v1/cases/{cid}/agents/drafts',headers=H('LeadInvestigator')).json()
    assert saved==[d]
    out=empty_client.get(f'/api/v1/cases/{cid}/export',headers=H('LeadInvestigator'))
    assert out.status_code==200,out.text
    with zipfile.ZipFile(io.BytesIO(out.content)) as z:
        assert json.loads(z.read('agents/drafts.json'))==[d]
        assert z.read('raw/unchanged.bin')==b'fictional unchanged source'
