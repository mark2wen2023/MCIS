# Pure offline recovery observation state machine, research v1

Base0410121aa65929200039308053908876a0d1d3d7. Independent branch research/offline-restore-state-machine. No product integration, permissions, SQL, filesystem, process, network, clock, worker or dependency installation. Immutable dataclass inputs/outputs only. This is a model of the proposed rules, not durable recovery or a production safety proof.

## Input contract

State includes case_id, operation_id (or null for ordinary cases), identity (`unknown`, `match`, `mismatch`), classification (`unknown`, `legacy_verified`, `normal_verified`, `restore`), claimed, attempted, commit, files and ready_record. Booleans and enum values are checked; impossible attempt/commit/ownership/readiness combinations reject without normalization. Case and operation IDs are never changed by a transition.

All observations are **synthetic declarations supplied by the caller**, not trusted external identity or actual commit evidence. `identity=match` and `legacy_verified` do not authenticate anything. A future trusted adapter must derive those declarations from the agreed external identity and persistent transaction/ownership evidence. There is no adapter here, and absence of protocol metadata never implies legacy compatibility.

## Transitions

| Explicit simulated observation | Preconditions / effect |
|---|---|
| claim_recorded | matching identity, restore classification, operation ID, no prior claim or files |
| staging_verified | claimed, no dispatch attempt, absent files → staged |
| attempt_recorded | staged and not previously attempted → commit unknown immediately |
| commit_unknown | attempted/unknown remains unknown; never failure or success |
| commit_confirmed | previously unknown attempt → confirmed observation |
| rollback_confirmed | previously unknown attempt → recorded rollback; retain staged/published files |
| publication_observed | existing attempt and staged/missing files; confirmed or unknown commit. Records external observation, does not authorize publication. |
| ready_commit_confirmed | matching identity, confirmed commit and published files → simulated ready |
| files_missing / files_mismatch | retain operation/commit state, revoke current readiness eligibility and hold |
| identity_lost | identity unknown; revoke current readiness eligibility |

Events outside these transitions reject. Reusing the same attempt, silently staging again, switching a confirmed rollback to a commit, or applying a ready declaration before confirmation reject. Mismatched files have no automatic repair transition. After files reappear, a fresh explicit publication observation and readiness confirmation are needed; this does not itself establish their real authenticity. `ready_record` represents eligibility of the current observation, not deletion of a prior persistent readiness record: every input State remains immutable. No historical event store exists or is silently synthesized.

`decide` returns held phases, or descriptive future candidate steps such as verify_owned_publication_candidate. Those labels are NOT execution permission or callbacks. Its flags ALWAYS remain:
```
restore_ready = false
product_access_allowed = false
automatic_retry_allowed = false
deletion_allowed = false
task_execution_allowed = false
```
Only simulated_ready may become true. Explicit legacy/normal classification with matching identity and no operation routes conceptually toward `existing_policy_check_required`; it does not open a case or replace authorization. Missing/unknown/mismatched migration identity remains held_unknown even if the caller describes an old case. Existing product cases are not modified or hidden.

## Developer-only validation

Exactly13 new individually named nodes in `nodeids.txt` were executed once. Prefix:
```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider --rootdir=/workspace/mcis-sensevoice-review
```
Append the13 nodeids verbatim, then `--tb=short`. No test file/directory selection or collection run was used. Result: **13 passed in0.03s**, no failures/skips. Each test supplies fabricated immutable states; no actual file, SQLite connection, rollback, process crash or uncertain commit was exercised. `retry`/`delete` appear solely as rejected string events, never operations. No paused tests or write-refusal probe were imported or executed. Not combined with prior test totals and not independent acceptance.

Remaining: durable operation ownership, external identity binding, actual commit observation, complete file inventories/byte validation, no-replace publication and durability, all entry gates, authorization recheck, restart/concurrency/crash handling and retained history. Real response loss or SQLite uncertainty is NOT reproduced. Do not enable restore on the basis of this model.
