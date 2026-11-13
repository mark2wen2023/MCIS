"""Non-browser investigator save/read/revoke acceptance; actual W2 opt-in."""
import os
import pytest
from .conftest import C,CASE
from .test_source_incarnation import fresh
from .test_registered_align_preview import register,request
from .test_local_authority import provision
from .test_identity_http_trial import trial,headers
from .test_internal_unreviewed_save import OP,counts
from mcis_service.identity import local


def test_actual_w2_http_save_read_replay_revoke(client,empty_client):
    command=os.getenv('MCIS_PREFLIGHT_REAL_CORE')
    if not command:pytest.skip('explicit actual W2 command required')
    target=fresh(client,empty_client);target.app.state.settings.core_cmd=command
    receipt=register(target);body={'operationId':OP,'request':request(receipt)}
    subject,token=provision(target)
    with trial(target) as api:
        post=api.post(C+'/timeline/unreviewed-runs',headers=headers(token),json=body)
        assert post.status_code==200,post.text
        run=post.json()['runId'];path=C+'/timeline/unreviewed-runs/'+run
        read=api.get(path,headers=headers(token));assert read.status_code==200,read.text
        data=read.json();assert data['runId']==run and data['caseId']==CASE
        assert data['status']=='unreviewed' and data['observationApproval']=='not_assessed'
        assert data['generationSnapshot']['sourceSnapshots'][0]['sourceSha256']==receipt['sourceSha256']
        assert data['serverPreview']['result']['stats']['sourcesImported']==1
        retry=api.post(C+'/timeline/unreviewed-runs',headers=headers(token),json=body)
        assert retry.status_code==200 and retry.json()['runId']==run and retry.json()['replayed']
        # Browser-style POST remains explicitly disabled, even with a valid token.
        browser=api.post(C+'/timeline/unreviewed-runs',headers={**headers(token),'Origin':'https://mcis.invalid'},json=body)
        assert browser.status_code==400
        with target.app.state.db.session() as session:
            local.set_membership(session,subject,CASE,role='LeadInvestigator',can_save_unreviewed=False)
        assert api.get(path,headers=headers(token)).status_code==200
        assert api.post(C+'/timeline/unreviewed-runs',headers=headers(token),json=body).status_code==403
        with target.app.state.db.session() as session:local.revoke_session(session,token)
        denied=api.get(path,headers=headers(token))
        assert denied.status_code==403 and 'serverPreview' not in denied.text
    assert counts(target)==(1,1)
