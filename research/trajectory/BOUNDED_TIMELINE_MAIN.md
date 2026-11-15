# Current-main bounded timeline archive candidate

Base: freshly fetched main94d5e38c926fda232bb987b60fa9145e4bcf01a7.
Selected existing slice: timeline event rows alongside the already-supported working
record v1 report/interview archive. This is a reuse of existing unmerged candidate
7aa9b9fb657ee118eddba0d278b94c9c2f589aaa (origin/research/archive-main-73fc800),
NOT a new incompatible format competing with its existing 1.4 contract.
The four existing archive implementation files were unchanged between its73fc800
base and current main. Selected backend/schema/contract files reused; no old commit
stack, old progress files, unrelated modules or web changes copied.

## Inventory / deliberate bounds

- 1.0: existing case/vessel/evidence/environment/audit members; legacy normalization
  unchanged. Existing generic legacy behavior is not widened or certified here.
- 1.1: optional HFACS extension; core execution not tested in this turn.
- 1.2: working-record v1 reports/interviews/snapshots/inactive receipts/history.
- 1.3: working-record v2 track source/receipt history.
- Proposed1.4: working-record v1 PLUS nonempty timeline events; exact version and
  extension pairing. It is NOT support for v2 track history + timeline.

Timeline is the smallest existing candidate because events have a case timebase,
optional vessel/evidence references, source labels and recorded draft flags, without
a new mutable response lifecycle. Conflicts, COLREG, recommendations, consultation,
agent drafts and unknown tables remain unsupported in this profile. The complex
Lily/Mary seed still has multiple such tables and is not enabled by this increment.
No ECFC/W11 state is traversed or enabled.

## Implementation, beyond table admission

Version1.4 requires timeline/records.v1.json with 1–256 exact key/createdUtc/updatedUtc/doc
rows. Validate row schema/identity, same-case vessel/evidence membership, duplicate
references, finite time bounds and utc vs caseEpochUtc+timeSec. Preserve original
submillisecond timeSec and current API UTC semantics; do not silently round documents.
analysis/timeline.json must exactly mirror these authoritative rows. Unsupported
combinations fail rather than omit content. Full existing content authorization runs
before collection. No role policy/defaults/read permissions changed.

Restore timeline rows under the existing package transaction and validate the entire
working package before mutation; original audit-line history and source package
artifacts are retained by the existing working archive. No regenerate-report step.
Confirmed/presumptive flags remain historical claims, not new approval or facts.
Old1.0–1.3 meanings remain. Existing legacy import refuses1.4; explicit package intake
is required. Old webpage model still rejects1.4, because frontend changes from the
old candidate were deliberately not imported; this is API-only, not UI completion.

## Actual verification

First ordinary synthetic subset:5 passed in3.26s (no restricted integrity probes).
Includes three stores, unchanged report and exact timeline rows, audit prefix,
retained original source package, evidence bytes/links, submillisecond points and
whole refusal after an unsupported recommendation is added; old import still422.
Added ordinary injected post-restore RuntimeError test checks unchanged pre-import
snapshot, no timeline rows and no published case directory. It does not establish
process-crash or cross-filesystem atomicity.

Selected final command (repository root):
```
service/.venv/bin/pytest -q service/tests/test_bounded_timeline_archive_increment.py service/tests/test_contracts.py service/tests/test_environment_w92.py service/tests/test_working_record_archive.py::test_three_store_roundtrip_and_inactive_receipts
```
Final result below. Tests use synthetic source files and local HTTP/SQLite, no model
or live maritime records. These are development tests, not independent acceptance.
No restricted historical snapshot mutation/integrity tests, denied protection query,
concurrent security test, ECFC operation or SDK installation performed.

## Remaining limits / review gate

No full security acceptance, production identity, browser, current-reader race fixes,
load/long-lock/memory measurement or HFACS execution claim. Existing header identity
and file/transaction safety limitations have not been solved by format support.
Negative-reference/version/budget validators are reused code but their old full
adversarial suite was NOT rerun here; review must distinguish code reuse from fresh
acceptance. Do not merge/deploy this candidate or call complex-case export solved.
The original190 suite was not rerun; prior187 pass/3 failure remains its last result.

Final selected developer regression:81 passed in22.87s, zero failures/skips in that
selection. This count includes6 new subset/fault tests,4 contracts,70 environment
cases and1 existing old1.2 three-store ordinary roundtrip. Original190 not included.
