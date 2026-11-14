import pytest
from sqlalchemy import select
from .test_internal_unreviewed_save import setup,counts
from .test_local_authority import provision
from .test_identity_http_trial import trial,headers
from .conftest import CASE
from mcis_service.identity import local
URL='/api/v1/trial/cases'


def test_case_and_source_projection(client,empty_client,monkeypatch):
    target,receipt,_=setup(client,empty_client,monkeypatch);subject,token=provision(target)
    with target.app.state.db.session() as s:local.set_membership(s,subject,CASE,role='LeadInvestigator',can_save_unreviewed=False)
    with trial(target) as api:
        c=api.get(URL,headers=headers(token));r=api.get(URL+'/'+CASE+'/sources',headers=headers(token))
    assert c.status_code==r.status_code==200,(c.text,r.text)
    assert c.json()['items'][0]['caseId']==CASE
    assert set(c.json()['items'][0])=={'caseId','caseIncarnation','caseEpochUtc'}
    source=r.json()['items'][0]
    assert source['evidenceId']==receipt['evidenceId'] and source['sourceSha256']==receipt['sourceSha256']
    assert source['mediaKind']=='csv' and source['observationApproval']=='not_assessed'
    assert set(source)=={'evidenceId','sourceSha256','registrationDigest','byteLength','registeredUtc','sourceIncarnation','mediaKind','observationApproval'}
    assert 'relativePath' not in r.text and token not in r.text and subject not in r.text
    assert c.headers['cache-control']==r.headers['cache-control']=='no-store' and counts(target)==(0,0)


@pytest.mark.parametrize('change',['member','revoke','expired','disabled','policy'])
def test_denied_catalog(client,empty_client,monkeypatch,change):
    target,_,_=setup(client,empty_client,monkeypatch);subject,token=provision(target)
    with target.app.state.db.session() as s:
        local.begin(s)
        if change=='member':local.set_membership(s,subject,CASE,role='LeadInvestigator',enabled=False)
        elif change=='revoke':local.revoke_session(s,token)
        elif change=='disabled':local.disable_subject(s,subject)
        elif change=='expired':s.scalar(select(local.SessionRecord)).expires_at=0
        else:
            from mcis_service.redaction.models import AccessPolicyRow
            from mcis_service.redaction.policy import default_policy
            p=default_policy();p['matrix']['LeadInvestigator']['evidence_meta']='Deny'
            row=s.scalar(select(AccessPolicyRow).where(AccessPolicyRow.case_id==CASE,AccessPolicyRow.key=='policy'))
            if row:row.doc=p
            else:s.add(AccessPolicyRow(case_id=CASE,key='policy',doc=p))
    with trial(target) as api:
        c=api.get(URL,headers=headers(token));r=api.get(URL+'/'+CASE+'/sources',headers=headers(token))
    assert r.status_code==403,r.text
    if change in ('member','policy'):assert c.status_code==200 and c.json()['items']==[]
    else:assert c.status_code==403
    assert CASE not in c.text and 'EV-001' not in r.text


@pytest.mark.parametrize('suffix',['?role=LeadInvestigator','/','/unknown'])
def test_exact_catalog_route(client,empty_client,monkeypatch,suffix):
    target,_,_=setup(client,empty_client,monkeypatch);_,token=provision(target)
    with trial(target) as api:assert api.get(URL+suffix,headers=headers(token)).status_code==404


def test_foreign_source_and_spoofed_header(client,empty_client,monkeypatch):
    target,_,_=setup(client,empty_client,monkeypatch);_,token=provision(target)
    with trial(target) as api:
        assert api.get(URL+'/FOREIGN/sources',headers=headers(token)).status_code==403
        assert api.get(URL,headers={'X-MCIS-Role':'LeadInvestigator'}).status_code==400
        assert api.get(URL,headers={**headers(token),'Origin':'https://evil.test'}).status_code==400


def test_corrupt_source_no_partial_metadata(client,empty_client,monkeypatch):
    target,receipt,_=setup(client,empty_client,monkeypatch);_,token=provision(target)
    (target.app.state.settings.blob_dir/CASE/receipt['evidence']['relativePath']).write_bytes(b'changed')
    with trial(target) as api:r=api.get(URL+'/'+CASE+'/sources',headers=headers(token))
    assert r.status_code==409 and receipt['evidenceId'] not in r.text
