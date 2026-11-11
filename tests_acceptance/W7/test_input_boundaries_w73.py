"""Additional W7.3 acceptance, separate from unchanged eight-test red baseline.
In-process TestClient / temporary DB, not real HTTP or concurrent validation.
Unicode expectations independently checked by net8 console (see logs).
"""
import pytest
from test_input_parity_w73 import client, C, H, snapshot, reject_unchanged


def open_one(client):
    r=client.post(C+'/consultation/rounds',headers=H,json={'draftVersion':'v1','parties':[{'partyId':'A','name':''}]})
    assert r.status_code==201,r.text


def unchanged_error(client,path,body,status,code,role='Investigator'):
    before=snapshot(client,C)
    r=client.post(C+path,headers={'X-MCIS-Role':role},json=body)
    assert (r.status_code,r.json().get('code'))==(status,code),r.text
    assert snapshot(client,C)==before


def test_unknown_round_before_blank_reason(client):
    unchanged_error(client,'/consultation/rounds/999/waivers',{'partyId':'A','reason':' \t'},404,'consultation_round_not_found')


def test_closed_round_before_blank_reason(client):
    open_one(client)
    assert client.post(C+'/consultation/rounds/1/waivers',headers=H,json={'partyId':'A','reason':'confirmed'}).status_code==201
    assert client.post(C+'/consultation/rounds/1:close',headers=H).status_code==200
    unchanged_error(client,'/consultation/rounds/1/waivers',{'partyId':'A','reason':' \t'},409,'consultation_round_closed')


@pytest.mark.parametrize('parties',[[{'partyId':' ','name':''}],[{'partyId':'A','name':''},{'partyId':'A','name':''}]])
def test_open_round_before_invalid_parties(client,parties):
    open_one(client)
    unchanged_error(client,'/consultation/rounds',{'draftVersion':'v2','parties':parties},409,'consultation_round_open')


def test_blank_draft_before_open_round(client):
    open_one(client)
    reject_unchanged(client,C,'/consultation/rounds',{'draftVersion':' ','parties':[{'partyId':'A','name':''}]})


def test_blank_reason_before_unknown_party(client):
    open_one(client)
    reject_unchanged(client,C,'/consultation/rounds/1/waivers',{'partyId':'unknown','reason':' '})


@pytest.mark.parametrize('path,body',[
    ('/consultation/rounds',{'draftVersion':' ','parties':[{'partyId':' ','name':''}]}),
    ('/consultation/rounds/1/waivers',{'partyId':'A','reason':' '})])
def test_readonly_permission_before_blank_domain_input(client,path,body):
    open_one(client)
    before=snapshot(client,C)
    r=client.post(C+path,headers={'X-MCIS-Role':'InterestedState'},json=body)
    assert r.status_code==403,r.text
    assert snapshot(client,C)==before


@pytest.mark.parametrize('value',['\u0085','\u00a0','\u2028'])
@pytest.mark.parametrize('field',['draftVersion','partyId','reason'])
def test_dotnet_unicode_whitespace_rejected(client,value,field):
    if field=='reason':
        open_one(client)
        reject_unchanged(client,C,'/consultation/rounds/1/waivers',{'partyId':'A','reason':value})
    else:
        body={'draftVersion':'v1','parties':[{'partyId':'A','name':''}]}
        if field=='draftVersion': body[field]=value
        else: body['parties'][0][field]=value
        reject_unchanged(client,C,'/consultation/rounds',body)


@pytest.mark.parametrize('value',['\u001c','\u001d','\u001e','\u001f'])
def test_non_dotnet_blank_controls_preserved(client,value):
    body={'draftVersion':value,'parties':[{'partyId':value,'name':''}]}
    r=client.post(C+'/consultation/rounds',headers=H,json=body)
    assert r.status_code==201,r.text
    r=client.post(C+'/consultation/rounds/1/waivers',headers=H,json={'partyId':value,'reason':value})
    assert r.status_code==201,r.text
    stored=client.get(C+'/consultation/rounds',headers=H).json()[0]
    assert stored['draftVersion']==value and stored['parties']==body['parties']
    assert stored['waivers'][0]['partyId']==value and stored['waivers'][0]['reason']==value
    assert client.get(C+'/audit:verify',headers=H).json()['valid']
