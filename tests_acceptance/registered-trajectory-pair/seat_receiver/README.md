# Portable single-seat receiver acceptance candidate

Baseline: 1095e67e2d5c1564bfaf82b8e0552dc2d99e7080. Offline synthetic tests only; disabled without an explicit mode. No model, service, production change, save/export, Git mutation, dependency installation or fetch.

## Proposed Git paths (five files only)
Place this directory's receiver.py, fixed_objects.py, check.py, run.py and README.md under:
`tests_acceptance/registered-trajectory-pair/seat_receiver/`
Do not commit copies of old modules, original JSON, or local adapter logs.

## Commands in the registration environment
Use its EXISTING Python and checkout with the pinned objects present:
```bash
/path/to/existing/python -I -B tests_acceptance/registered-trajectory-pair/seat_receiver/run.py --check /absolute/MCIS
/path/to/existing/python -I -B tests_acceptance/registered-trajectory-pair/seat_receiver/run.py --handoff /absolute/MCIS
```
Single integration: run.py loads verified fixed objects in memory, then calls actual fixed seat_handoff.py:run_handoff with receiver.consumer bound to those dependencies. The callback has no incoming label or caller-selected clock. Its returned note remains in memory and is ignored by the existing host; failed assertions propagate. No automatic retry.

The checkout seat_handoff.py must match blob e43290ccf27af8e7126ac3edd6ab87d6236c61b1. Its existing sibling fixtures and fixed Git objects must also be present as required by A's harness. No private task directory is referenced. Existing jsonschema is required; actual handoff additionally needs A's existing SQLAlchemy/FastAPI environment.

## Fixed inputs, without copying originals
fixed_objects.py lists full commits, Git paths and blob IDs:
- actual projection + validation from 0dc1226364524977a4155e480d96436443cd8967;
- actual host packet validator from 420284ab5fd44c94b737f8c1cf51bc0ef09aea29;
- A/B synthetic original JSON from 2048c60fd6650c6f2c99a76a16be463a3895655d.
Git reads are read-only show operations, with replacement objects and lazy fetch disabled. All source/blob checks complete before module execution. Missing object, wrong byte, unavailable dependency or malformed record fails; no current/latest fallback. Existing modules execute unmodified in memory. Their computed file paths are virtual; the called pure functions do not read those paths or execute the service. No V1 schema validation claim is added.

## Semantics
Exact original projection and raw pin SHAs, two evidence IDs, registration digests and cross-frame consistency are checked at T100 and T124.250. B's displayed +12 seconds remains pending/undetermined. Gap and absent point remain distinct; no neighboring pointer is borrowed. Four reviews are derived as insufficient because calibration basis/reviewer confirmation is absent. Existing host shape validator runs on those derived reviews.
Pin fields are not copied into note output. No human signature, fact activation or saved report.

This is not authentication. The trustworthy source of record is the actual synchronous A host call, not dictionary shape, SHA, or accessCount. Direct synthetic calls cannot prove permission. A commits two reads separately; consumer rejection does not roll back earlier Access and must not trigger retry.

## What B actually ran
1. New receiver/check modules with blob-verified original bytes supplied in memory: 3 tests passed, including 8 rejection variants; altered original bytes rejected with BLOB_MISMATCH:a. This is a test adapter, not actual Git-loading success or registration/permission execution.
2. Actual run.py --check against the local existing checkout: failed with FIXED_OBJECT_MISSING for baseline1095e67's SEAT-HANDOFF.md, exit1. No objects were installed/fetched/created.
The B checkout lacks the required objects and B lacks SQLAlchemy. Successful Git-object loading and real SQLite/Access handoff remain for root/A to run. No push performed.
