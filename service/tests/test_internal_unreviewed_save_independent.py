"""Independent audit-safe actor and replay-integrity boundaries."""
import pytest
from fastapi import HTTPException
from .conftest import CASE,C,H
from .test_internal_unreviewed_save import setup,save,counts
from .test_binding_review_independent import snapshot
from mcis_service.timeline import align_preview,unreviewed_storage as storage

@pytest.mark.parametrize('operator',['bad\x85actor','bad\u2028actor','bad\u2029actor','bad\ud800actor'])
def test_unexportable_actor_rejected_before_compute_or_write(client,empty_client,monkeypatch,operator):
    target,r,body=setup(client,empty_client,monkeypatch)
    before=snapshot(target)
    monkeypatch.setattr(align_preview,'core_run',lambda *_:pytest.fail('actor must be rejected before compute'))
    with pytest.raises(HTTPException) as error:save(target,body,operator=operator)
    assert error.value.status_code==422
    assert snapshot(target)==before and counts(target)==(0,0)


def test_same_operation_changed_role_never_replays(client,empty_client,monkeypatch):
    target,r,body=setup(client,empty_client,monkeypatch)
    # Give both fixture roles full content access so this tests scope binding,
    # not the default Investigator medical/PII denial which correctly wins first.
    from mcis_service.redaction.policy import default_policy
    p=default_policy();p['matrix']['Investigator']=dict(p['matrix']['LeadInvestigator'])
    for rule in p['fieldRules']:
        rule['appliesTo']=[role for role in rule['appliesTo'] if role!='Investigator']
    assert target.put(C+'/access-policy',headers=H('LeadInvestigator'),json=p).status_code==200
    save(target,body)
    before=snapshot(target)
    monkeypatch.setattr(align_preview,'core_run',lambda *_:pytest.fail('role mismatch must not recompute'))
    with pytest.raises(HTTPException) as error:save(target,body,role='Investigator')
    assert error.value.status_code==409
    assert snapshot(target)==before and counts(target)==(1,1)


@pytest.mark.parametrize('field',['operation_id','run_id'])
def test_corrupt_identity_index_does_not_replay(client,empty_client,monkeypatch,field):
    target,r,body=setup(client,empty_client,monkeypatch);first=save(target,body)
    with target.app.state.db.session() as s:
        row=s.get(storage.UnreviewedRunRow,(CASE,first['runId']))
        setattr(row,field,'90000000-0000-4000-8000-000000000001')
    before=snapshot(target)
    monkeypatch.setattr(align_preview,'core_run',lambda *_:pytest.fail('corruption must not compute'))
    with pytest.raises(HTTPException) as error:save(target,body)
    assert error.value.status_code==409
    assert snapshot(target)==before
