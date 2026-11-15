# Product receipt integration gate: STOP, policy not equivalent

Base781ca9e on existing unmerged conflict/archive stack; current remote main94d5e38.
No production implementation or policy changed. New ordinary synthetic tests prove
an actual compatibility blocker rather than treating an in-memory receipt as a fix.

Same synthetic case/registered source: Investigator GET conflicts:editable returns
200, but existing full-content/source gate used by RegistryReceipts.issue returns403.
Hence replacing the current source-changing workflow with that receipt is NOT an
equivalent policy-preserving integration. Do not weaken source gate or silently
require receipt for all currently permitted conflict work. No production route added.

Confirmed useful existing transaction boundary: POST/PATCH reserve SQLite writer
before current/policy reads, then current conflict, audit append and full revision
(including afterSources) share Database.session commit/rollback. The resolution-only injected failure preserves existing source A rather than
creating any new receipt association. Original cafcdf2 assertions inside the fault
callback could themselves become500: that run was insufficient to prove the intended
fault point. The corrected test records capture return, copied revision/current/audit
and an explicit injection marker, checks all outside the route, then checks rollback. This is actual temporary SQLite/HTTP execution with
synthetic data, not proof of crash durability or untested concurrency scenarios.

Legacy missing expectedVersion returns428 with current document unchanged. Existing
EvidencePage catches412/428 without acknowledging local draft, using previously
reviewed draft state helper. Static inspection only this turn: no frontend/browser
rerun. This protects current conflict versions, NOT new source receipts. Editor edits
resolution/status, and has no source-observation receipt refresh/compare/submit path.
Old source-changing POST callers would need an explicit migration contract.

Lowest-risk future route: separate explicitly opt-in source-confirmation workflow
under already authorized evidence/source access, with authoritative durable receipt
and immutable association recorded inside SAME existing conflict transaction. Keep
resolution-only historic bindings. The current broader timeline workflow cannot be
silently reclassified as source-confirmed. Need approved handling for users denied
source receipt, unknown source changes, old client writes, and receipt archive/lifetime.
Original-byte receipt remains out of scope. No new automatic 'human read' flag.
Without these prerequisites a new endpoint would be either unusable for existing
allowed users or an unauthorized disclosure expansion. Thus stop wiring now.

From service:
PYTHONPATH=.. .venv/bin/pytest -q tests/test_source_receipt_integration_gates.py tests/test_conflict_revisions.py::test_failure_rolls_back_row_revision_and_audit tests/test_conflict_source_intent_gap.py
5 passed in0.83s, includes3 new tests and2 existing; initial4 before adding explicit
registered-source rollback case. All developer synthetic, independent review pending.
No restricted history/security/ECFC operations, original files, network model or
credentials. Original A→B source intent gap still reproduced, not repaired. No
production/real browser acceptance, no deployment/merge/push this turn.

## Correction after independent static review
Only the corrected ordinary rollback node was rerun:
PYTHONPATH=.. .venv/bin/pytest -q tests/test_source_receipt_integration_gates.py::test_resolution_only_registered_source_revision_audit_rollback_together
1 passed in0.47s. No permission/security/ECFC test rerun. External assertions require
new revision ordinal, changed resolution, in-transaction current/postimage agreement,
actual conflict.update audit row, retained exact prior afterSources A and
bytesVerified=false. Missing observations or an earlier exception cannot be hidden
by the route500. History/current state then remain unchanged after rollback.
This does NOT test new source receipt persistence/consumption or source-change
submission. A→B gap and production integration blockers remain unchanged.
Original five-test report remains historical, with its callback false-positive
weakness disclosed above; it is not the corrected candidate's test count.
