"""Independent reserved-field ingress and historical-draft review probes."""
import copy
import pytest
from sqlalchemy import inspect, text
from mcis_service.agents.models import AgentDraftRow
from mcis_service.db import get_doc, put_doc
from .test_timeline_binding_boundary import DRAFT, counts
from .conftest import C, CASE, H


def snapshot(client):
    with client.app.state.db.session() as session:
        return {name:sorted(repr(tuple(row)) for row in session.execute(text('SELECT * FROM "'+name+'"')))
                for name in inspect(session.connection()).get_table_names()}


def submitted(client):
    response = client.post(C+'/agents/drafts', json=DRAFT, headers=H('AgentService'))
    assert response.status_code == 201, response.text
    return response.json()['draftId']


@pytest.mark.parametrize('decision',['Confirmed','Modified','Rejected'])
def test_review_payload_cannot_inject_reserved_binding(client, decision):
    did = submitted(client)
    payload = copy.deepcopy(DRAFT['payload'])
    payload['timelineSourceBinding'] = {'approved':True,'receiptId':'forged-review'}
    before = snapshot(client)
    with client.app.state.db.session() as s:
        old = copy.deepcopy(get_doc(s,AgentDraftRow,CASE,did))
    response = client.post(C+'/agents/drafts/'+did+'/review', json={'decision':decision,'payload':payload}, headers=H('LeadInvestigator'))
    assert response.status_code == 422, response.text
    assert response.json()['code'] == 'TIMELINE_BINDING_LOCAL_ONLY'
    assert snapshot(client) == before
    with client.app.state.db.session() as s:
        assert get_doc(s,AgentDraftRow,CASE,did) == old


@pytest.mark.parametrize('location',['root','payload'])
@pytest.mark.parametrize('decision',['Confirmed','Modified'])
def test_historical_reserved_draft_cannot_be_confirmed(client, location, decision):
    did = submitted(client)
    with client.app.state.db.session() as s:
        old = copy.deepcopy(get_doc(s,AgentDraftRow,CASE,did))
        (old if location=='root' else old['payload'])['timelineSourceBinding'] = {'receiptId':'untrusted-history'}
        put_doc(s,AgentDraftRow,CASE,did,old)
    before = snapshot(client)
    body={'decision':decision}
    if decision=='Modified':body['payload']=DRAFT['payload']
    response=client.post(C+'/agents/drafts/'+did+'/review',json=body,headers=H('LeadInvestigator'))
    assert response.status_code==422,response.text
    assert response.json()['code']=='TIMELINE_BINDING_LOCAL_ONLY'
    assert snapshot(client)==before
    with client.app.state.db.session() as s:
        assert get_doc(s,AgentDraftRow,CASE,did)==old


@pytest.mark.parametrize('location',['root','payload'])
def test_historical_reserved_draft_can_be_rejected_without_new_payload(client,location):
    did=submitted(client)
    with client.app.state.db.session() as s:
        old=copy.deepcopy(get_doc(s,AgentDraftRow,CASE,did))
        (old if location=='root' else old['payload'])['timelineSourceBinding']={'receiptId':'untrusted-history'}
        put_doc(s,AgentDraftRow,CASE,did,old)
    before=counts(client)
    all_before=snapshot(client)
    response=client.post(C+'/agents/drafts/'+did+'/review',json={'decision':'Rejected'},headers=H('LeadInvestigator'))
    if location=='root':
        assert response.status_code==422,response.text
        assert response.json()['code']=='CONTRACT_VIOLATION'
        assert snapshot(client)==all_before
        return
    assert response.status_code==200,response.text
    after=counts(client)
    assert after['timeline_events']==before['timeline_events']
    assert after['evidence_items']==before['evidence_items']
    assert after['custody_events']==before['custody_events']
    with client.app.state.db.session() as s:
        saved=get_doc(s,AgentDraftRow,CASE,did)
        assert saved['status']=='Rejected'
        assert saved['payload']==old['payload']
