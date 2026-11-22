# FourChair draft attribution — narrow memory candidate

Base: 26451febf955f4b6d7654e9a4b32ca70c2ec4c13.
Reference: 431d9d5ff06d051b9017ae350a5dabaf2ad61e8b cited-excerpt correspondence.
Self-tested only; real ledger, real identity, human confirmation and model execution NOT RUN.

## Scope and limits
Changes the existing research/expert_budget/four_chair.py, not a replacement chair.
Optional bind_draft_simulated is a trusted in-process synthetic host operation.
It copies caseId, version, draftDigest and sourceSetDigest into the issued context,
therefore its existing contextDigest binds the actual active ticket and role.
Submission checks the host's current binding before validating reviews or settling.
Accepted opinions retain the issued draftBinding. No network/product API is added.

The host must compute the digests from the draft and successfully located sources;
the new method only checks metadata shape, not provenance, authority or truth.
The source-set digest is not per-opinion citation validation.
The default pinned packet loader, packet pin, review schema and production identity
are unchanged. No default ECFC source intake has been implemented.

This is the permitted narrow stale-revision fallback. A stale ticket remains active
and unaccepted; there is no retry/reassignment/resume/new revision meeting flow.
Explicit stop is needed. Once any opinion exists, rebinding is rejected, preventing
mixed-version summary aggregation. Host version naming/reuse is not an implemented
revision registry. Changing all metadata back is not independently detected.

## Reproduce
Use an existing Python with standard library only, from this candidate checkout:
```sh
python -I -B research/w20_chair_revision/check.py \
  --ecfc-package /path/to/verified-6996fa05/research/ecfc_pending_handoff \
  --locator /path/to/verified-431d9d5/research/w19_case_ranking/source_traceability/check.py
```
Both arguments may point to fixed Git exports. No fetch/install is performed.
The published ECFC frozen manifest, every listed byte and locator/packet blobs are
checked before use. Dependencies and synthetic originals are not copied into this
commit. The script itself prints its result and does not save opinions/reports.

## Actual test boundary
Calls actual FourChair constructor, issue, submit_simulated, receipt and stop.
Only Ledger, constructor file open/close, and the packet-loading pair are mocked.
The test-only packet uses the same fixed 6996fa05 synthetic source excerpts after
actual locate succeeds. It never opens the default public accident packet.
This is not a real initialized ledger meeting or production evidence integration.

Two negative revision cases: v1 ticket after host binds v2; same draft version with
changed source-set digest. Both fail before ledger settlement, retain the original
ticket and accept no opinion. Four subsequent v2 role opinions preserve actual
attempt IDs and both opposed inspection excerpts. Wrong ticket and a quote from
another item's excerpt are rejected by existing binding/_validate checks.
Each item's sourceText is one exact located excerpt, never concatenated excerpts,
matching the limited principle checked in 431d9d5; receive() is not rerun or wired.
All summaries keep factVerified=false. Optional binding absent preserves existing
context/opinion shape. Neither counting byte positions nor disagreement proves
independent evidence, source authenticity, professional accuracy or causal truth.

## Developer result
2026-11-22: check.py exited 0, no skipped assertions.
Local command used the verified ECFC export and locator export; output included
stale_draft_rejected_before_settle=true, changed_source_set_rejected=true,
current_attributed_opinions=4, located_byte_positions=3,
opposed_excerpts_preserved=true, default_binding_absent=true.
No existing database fault/concurrency/model/browser tests were run.
Pending independent review. No W19 blind inputs/answers were read.
