"""W7.3 input parity; in-process TestClient, fresh temporary SQLite per test.
No concurrency guarantee and no production/source mutation.
"""
from pathlib import Path
import sys
import pytest
from fastapi.testclient import TestClient
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'service'))
from mcis_service.config import Settings
from mcis_service.main import create_app
C='/api/v1/cases/CASE-2025-HAILI5-WANA17'
DEMO='/api/v1/cases/CASE-2026-DEMO-LILY-MARY'
H={'X-MCIS-Role':'Investigator'}

@pytest.fixture()
def client(tmp_path):
    with TestClient(create_app(Settings(data_dir=tmp_path,db_url=f'sqlite:///{tmp_path}/case.db',seed_demo=True))) as c:
        assert c.get(C+'/consultation/rounds',headers=H).json()==[]
        yield c

def snapshot(c,base):
    return (c.get(base+'/consultation/rounds',headers=H).json(),c.get(base+'/audit',headers=H).json())

def reject_unchanged(c,base,path,payload,code='consultation_invalid_argument'):
    before=snapshot(c,base)
    r=c.post(base+path,headers=H,json=payload)
    after=snapshot(c,base)
    # Report both contract and mutation drift when reproducing the original bug.
    assert (r.status_code,r.json().get('code'),after==before)==(422,code,True), (r.status_code,r.json(),after==before)

@pytest.mark.parametrize('value',['',' \t\n'])
def test_blank_draft_version_rejected(client,value):
    reject_unchanged(client,C,'/consultation/rounds',{'draftVersion':value,'parties':[{'partyId':'A','name':'a'}]})

@pytest.mark.parametrize('value',['',' \t\n'])
def test_blank_party_id_rejected(client,value):
    reject_unchanged(client,C,'/consultation/rounds',{'draftVersion':'v1','parties':[{'partyId':value,'name':'a'}]})

def test_exact_duplicate_party_id_rejected(client):
    reject_unchanged(client,C,'/consultation/rounds',{'draftVersion':'v1','parties':[{'partyId':'A','name':'first'},{'partyId':'A','name':'second'}]})

def test_whitespace_waiver_reason_rejected(client):
    reject_unchanged(client,DEMO,'/consultation/rounds/2/waivers',{'partyId':'FLAG-B','reason':' \t\n'})

def test_existing_empty_reason_validation_error_preserved(client):
    reject_unchanged(client,DEMO,'/consultation/rounds/2/waivers',{'partyId':'FLAG-B','reason':''},'VALIDATION_ERROR')

def test_ordinal_ids_empty_names_and_valid_text_preserved(client):
    body={'draftVersion':'  v1  ','parties':[{'partyId':' A ','name':''},{'partyId':'A','name':' name '},{'partyId':'a','name':''}]}
    before=len(client.get(C+'/audit',headers=H).json())
    r=client.post(C+'/consultation/rounds',headers=H,json=body)
    assert r.status_code==201,r.text
    doc=r.json();assert doc['parties']==body['parties'] and doc['draftVersion']==body['draftVersion']
    reason='  Already confirmed waiver  '
    r=client.post(C+'/consultation/rounds/1/waivers',headers=H,json={'partyId':' A ','reason':reason})
    assert r.status_code==201,r.text
    assert r.json()['waivers'][0]['partyId']==' A ' and r.json()['waivers'][0]['reason']==reason
    assert [x['partyId'] for x in r.json()['parties']]==[' A ','A','a']
    again=client.get(C+'/consultation/rounds',headers=H).json()[0]
    assert again['draftVersion']==body['draftVersion'] and again['parties']==body['parties']
    assert again['waivers'][0]['reason']==reason
    assert len(client.get(C+'/audit',headers=H).json())==before+2
    assert client.get(C+'/audit:verify',headers=H).json()['valid']
