"""Immutable simulated observations, not persistence or authorization evidence.
No I/O, database, filesystem, worker, clock, random source or executable callbacks.
"""
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class State:
    case_id: str
    operation_id: str | None
    identity: str = 'unknown'
    classification: str = 'unknown'
    claimed: bool = False
    attempted: bool = False
    commit: str = 'not_attempted'
    files: str = 'absent'
    ready_record: bool = False


def valid(s):
    if not isinstance(s, State) or type(s.case_id) is not str or not s.case_id:
        raise ValueError('case identity required')
    if s.operation_id is not None and (type(s.operation_id) is not str or not s.operation_id):
        raise ValueError('operation identity')
    if s.identity not in ('unknown','match','mismatch') or s.classification not in ('unknown','legacy_verified','normal_verified','restore'):
        raise ValueError('unknown classification label')
    if any(type(v) is not bool for v in (s.claimed,s.attempted,s.ready_record)):
        raise ValueError('boolean declaration')
    if s.commit not in ('not_attempted','unknown','confirmed','rolled_back') or s.files not in ('absent','staged','published','missing','mismatch'):
        raise ValueError('unknown observation label')
    if s.claimed and (s.operation_id is None or s.classification!='restore'):
        raise ValueError('unbound claim')
    if s.attempted != (s.commit!='not_attempted') or (s.attempted and not s.claimed):
        raise ValueError('attempt/commit association')
    if s.files in ('staged','published') and not s.claimed:
        raise ValueError('unowned files')
    if s.ready_record and not (s.identity=='match' and s.classification=='restore' and s.claimed and s.attempted and s.commit=='confirmed' and s.files=='published'):
        raise ValueError('invalid ready declaration')
    return s


def observe(s, event):
    """Apply one explicit simulated observation; never carry out its named operation."""
    valid(s)
    if event=='identity_lost':
        return replace(s,identity='unknown',ready_record=False)
    if s.identity!='match' or s.classification!='restore':
        raise ValueError('identity/classification unresolved; observe outside this protocol')
    changes = None
    if event=='claim_recorded' and not s.claimed and s.operation_id is not None and s.files=='absent':
        changes=dict(claimed=True)
    elif event=='staging_verified' and s.claimed and not s.attempted and s.files=='absent':
        changes=dict(files='staged')
    elif event=='attempt_recorded' and s.claimed and not s.attempted and s.files=='staged':
        # Before dispatch, persist attempted; lack of a reply is immediately unknown.
        changes=dict(attempted=True,commit='unknown')
    elif event=='commit_unknown' and s.attempted and s.commit=='unknown':
        changes=dict(commit='unknown',ready_record=False)
    elif event=='commit_confirmed' and s.attempted and s.commit=='unknown':
        changes=dict(commit='confirmed')
    elif event=='rollback_confirmed' and s.attempted and s.commit=='unknown':
        changes=dict(commit='rolled_back',ready_record=False)
    elif event=='publication_observed' and s.attempted and s.files in ('staged','missing') and s.commit in ('unknown','confirmed'):
        # Also represent external publication before commit confirmation, without permitting it.
        changes=dict(files='published',ready_record=False)
    elif event in ('files_missing','files_mismatch') and s.claimed:
        changes=dict(files='missing' if event=='files_missing' else 'mismatch',ready_record=False)
    elif event=='ready_commit_confirmed' and s.commit=='confirmed' and s.files=='published' and not s.ready_record:
        changes=dict(ready_record=True)
    if changes is None:
        raise ValueError('transition refused; no retry, overwrite or inferred completion')
    return valid(replace(s,**changes))


def decide(s):
    valid(s)
    phase, next_step = 'held_unknown', 'read_only_reconcile'
    if s.identity=='match':
        if s.classification in ('legacy_verified','normal_verified') and not s.claimed and s.operation_id is None and s.files=='absent':
            phase,next_step='ordinary_classification_recorded','existing_policy_check_required'
        elif s.classification=='restore':
            if s.files in ('missing','mismatch'):
                phase='held_files_unresolved'
            elif s.commit=='rolled_back':
                phase='rollback_recorded_files_retained'
            elif s.commit=='unknown':
                phase='held_commit_unknown'
            elif s.ready_record:
                phase,next_step='simulated_ready','existing_policy_check_required'
            elif s.commit=='confirmed' and s.files=='published':
                phase,next_step='published_waiting_ready','verify_and_record_ready_candidate'
            elif s.commit=='confirmed' and s.files=='staged':
                phase,next_step='committed_waiting_publication','verify_owned_publication_candidate'
            elif s.files=='staged':
                phase,next_step='staged_waiting_attempt','record_attempt_before_single_dispatch_candidate'
            elif s.claimed:
                phase,next_step='claimed','prepare_staging_candidate'
    return dict(phase=phase,proposed_next=next_step,simulated_ready=(phase=='simulated_ready'),
                restore_ready=False,product_access_allowed=False,automatic_retry_allowed=False,
                deletion_allowed=False,task_execution_allowed=False)
