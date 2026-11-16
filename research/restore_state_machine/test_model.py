"""New pure-function nodes only; fabricated observations, no real persistence/probes."""
from dataclasses import replace
import pytest
from .model import State, observe, decide


def initial():
    return State('SYNTHETIC-CASE','SYNTHETIC-OP',identity='match',classification='restore')


def staged():
    return observe(observe(initial(),'claim_recorded'),'staging_verified')


def attempted():
    return observe(staged(),'attempt_recorded')


def ready():
    s=observe(attempted(),'commit_confirmed')
    s=observe(s,'publication_observed')
    return observe(s,'ready_commit_confirmed')


def closed(s):
    d=decide(s)
    assert not any(d[k] for k in ('restore_ready','product_access_allowed','automatic_retry_allowed','deletion_allowed','task_execution_allowed'))
    return d


def test_claim_and_staging_do_not_open_or_dispatch():
    original=initial();s=observe(original,'claim_recorded');s=observe(s,'staging_verified')
    assert original==initial() and closed(s)['phase']=='staged_waiting_attempt'
    assert not s.attempted and s.commit=='not_attempted'


def test_attempt_without_reply_is_unknown_immediately():
    s=attempted();assert s.commit=='unknown'
    assert closed(s)['phase']=='held_commit_unknown'


def test_unknown_never_retries_same_operation():
    s=attempted()
    for event in ('attempt_recorded','claim_recorded','staging_verified','ready_commit_confirmed','retry','delete'):
        with pytest.raises(ValueError):observe(s,event)
    assert closed(s)['phase']=='held_commit_unknown'


def test_published_files_do_not_prove_commit():
    s=observe(attempted(),'publication_observed')
    assert s.files=='published' and closed(s)['phase']=='held_commit_unknown'
    with pytest.raises(ValueError):observe(s,'ready_commit_confirmed')


def test_confirmed_commit_waits_for_publication_and_ready_record():
    s=observe(attempted(),'commit_confirmed')
    assert closed(s)['phase']=='committed_waiting_publication'
    s=observe(s,'publication_observed')
    assert closed(s)['phase']=='published_waiting_ready'
    s=observe(s,'ready_commit_confirmed')
    assert closed(s)['simulated_ready'] is True


def test_confirmed_rollback_does_not_delete_or_retry():
    s=observe(attempted(),'rollback_confirmed')
    assert closed(s)['phase']=='rollback_recorded_files_retained' and s.files=='staged'
    with pytest.raises(ValueError):observe(s,'attempt_recorded')
    with pytest.raises(ValueError):observe(s,'commit_confirmed')


def test_missing_files_revoke_simulated_readiness():
    s=observe(ready(),'files_missing')
    assert s.ready_record is False and closed(s)['phase']=='held_files_unresolved'
    with pytest.raises(ValueError):observe(s,'ready_commit_confirmed')


def test_inconsistent_files_remain_held_without_repair():
    s=observe(ready(),'files_mismatch')
    assert closed(s)['phase']=='held_files_unresolved'
    with pytest.raises(ValueError):observe(s,'publication_observed')


def test_identity_loss_cannot_leave_ready_case_open():
    s=observe(ready(),'identity_lost')
    assert closed(s)['phase']=='held_unknown' and not s.ready_record
    with pytest.raises(ValueError):observe(s,'ready_commit_confirmed')


def test_legacy_without_explicit_migration_classification_is_unknown():
    for identity,classification in [('unknown','unknown'),('match','unknown'),('unknown','legacy_verified'),('mismatch','legacy_verified')]:
        s=State('SYNTHETIC-OLD',None,identity=identity,classification=classification)
        assert closed(s)['phase']=='held_unknown'
        with pytest.raises(ValueError):observe(s,'claim_recorded')


def test_explicit_ordinary_classification_still_requires_existing_policy():
    for classification in ('legacy_verified','normal_verified'):
        s=State('SYNTHETIC-ORDINARY',None,identity='match',classification=classification)
        d=closed(s)
        assert d['phase']=='ordinary_classification_recorded'
        assert d['proposed_next']=='existing_policy_check_required'
        assert not d['simulated_ready']


def test_impossible_partial_state_is_rejected_not_normalized():
    for s in (replace(initial(),ready_record=True),replace(initial(),commit='confirmed'),
              replace(initial(),files='published'),replace(initial(),attempted=True),
              replace(initial(),claimed=True,operation_id=None)):
        with pytest.raises(ValueError):decide(s)


def test_response_loss_resolution_is_an_observation_not_retry():
    s=observe(attempted(),'publication_observed');before=s
    s=observe(s,'commit_unknown')
    assert closed(s)['phase']=='held_commit_unknown'
    s=observe(s,'commit_confirmed')
    assert closed(s)['phase']=='published_waiting_ready'
    assert before.commit=='unknown'
    with pytest.raises(ValueError):observe(s,'attempt_recorded')
