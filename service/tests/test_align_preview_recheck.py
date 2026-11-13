"""Real SQLite/FastAPI boundary tests; core response mocked except opt-in cases."""
import copy
import os
import pytest
from sqlalchemy import delete
from mcis_service.timeline import align_preview as module
from mcis_service.db import get_doc, put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from .conftest import C, CASE, H
from .test_align_preview_w41 import BODY, URL, result


def change_case(client, **values):
    with client.app.state.db.session() as s:
        case=get_doc(s, CaseRow, CASE, CASE)
        case.update(values)
        put_doc(s, CaseRow, CASE, CASE, case)


def deny(client):
    with client.app.state.db.session() as s:
        policy=get_doc(s, AccessPolicyRow, CASE, 'policy') or default_policy()
        policy['matrix']['Investigator']['timeline']='Deny'
        put_doc(s, AccessPolicyRow, CASE, 'policy', policy)


def test_policy_revoked_in_second_transaction_drops_result(client, monkeypatch):
    def run(*args):
        deny(client)
        return result(args[2])
    monkeypatch.setattr(module,'core_run',run)
    r=client.post(URL,json=BODY,headers=H())
    assert r.status_code==403 and r.json()['code']=='FORBIDDEN'
    assert 'result' not in r.json()


def test_epoch_changed_in_second_transaction_drops_result(client, monkeypatch):
    def run(*args):
        change_case(client,caseEpochUtc='2026-05-19T06:15:00Z')
        return result(args[2])
    monkeypatch.setattr(module,'core_run',run)
    r=client.post(URL,json=BODY,headers=H())
    assert r.status_code==409 and r.json()['code']=='ALIGN_PREVIEW_CASE_CHANGED'
    assert 'result' not in r.json()


def test_case_removed_after_computation_drops_result(client, monkeypatch):
    def run(*args):
        with client.app.state.db.session() as s:
            s.execute(delete(CaseRow).where(CaseRow.case_id==CASE))
        return result(args[2])
    monkeypatch.setattr(module,'core_run',run)
    r=client.post(URL,json=BODY,headers=H())
    assert r.status_code==404 and 'result' not in r.json()


def test_unrelated_case_title_change_does_not_rebase_time(client, monkeypatch):
    def run(*args):
        change_case(client,title='updated title')
        return result(args[2])
    monkeypatch.setattr(module,'core_run',run)
    r=client.post(URL,json=BODY,headers=H())
    assert r.status_code==200 and r.json()['persisted'] is False


@pytest.mark.parametrize('revoke',[False,True])
@pytest.mark.skipif(not os.environ.get('MCIS_ACCEPTANCE_CORE'),reason='requires real built core wrapper')
def test_real_core_and_real_db_response_boundary(client, monkeypatch, revoke):
    # Wrapper path is trusted test configuration, never HTTP input.
    client.app.state.settings.core_cmd=os.environ['MCIS_ACCEPTANCE_CORE']
    original=module.core_run
    def run(*args):
        env=original(*args)
        assert env['result']['conflicts'][0]['delta']==5
        if revoke: deny(client)
        return env
    monkeypatch.setattr(module,'core_run',run)
    body=copy.deepcopy(BODY)
    body['sources'].append({**body['sources'][0],'sourceId':'B',
        'text':body['sources'][0]['text'].replace(',45',',50')})
    before=client.get(C+'/conflicts',headers=H()).json()
    r=client.post(URL,json=body,headers=H())
    assert r.status_code==(403 if revoke else 200),r.text
    # Investigator may lose read access, so inspect persisted rows as lead.
    assert client.get(C+'/conflicts',headers=H('LeadInvestigator')).json()==before
    if not revoke:
        assert r.json()['result']['conflicts'][0]['delta']==5
        assert r.json()['persisted'] is False
