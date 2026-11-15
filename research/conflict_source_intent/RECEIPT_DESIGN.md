# Source-observation receipt design — NOT IMPLEMENTED

Base652ef41; product/permissions unchanged. Existing reproduction remains valid.
This document does not enable a route, write receipt rows, certify reading, or
silently fix current auto-binding. Requires scoped contract/integration review.

## Verified interface prerequisites
- timeline/router.py editable_conflicts checks timeline and returns conflict-version
  only; write_version covers conflict/current journal, not evidence registry.
- evidence/router.py get_evidence checks evidence_meta and filter_evidence and
  returns derived registry metadata. It does not establish a source-byte read.
- evidence/router.py get_content returns X-Sha256 for returned bytes and records
  separately derived currentSha256. No unified receipt binds both to judgment.
  This is static interface inspection, NOT a new file-integrity/security probe.
- timeline/revisions.py history uses reports full-content gate plus source gate;
  interviews/access.py source requires that full-content policy and same-case
  registration visibility. These are not interchangeable with timeline permission.
- Existing EvidencePage has no observation-specific source receipt capture/submission.
  Header actor is self-reported; cannot bind receipt to a verified human identity.

## Proposed meaning and issuance
Name it source-observation receipt, never 'proof the human read/approved'. Separate:
1 registry-only observation: authorized server returned digest/registration view;
2 returned-byte observation: same authorized read returned bytes and actual digest.
Second mode depends on independently reviewed same-read binding; do not implement
it by combining unrelated metadata and file requests. No re-running restricted
file/history probes to manufacture confidence. For current scope only registry
mode could be considered after source-policy integration is explicitly reviewed.

A server-owned immutable receipt would contain random receiptId, case/evidence ID,
kind, returned registry/current digest, custody version marker, observation UTC,
nullable actualReturnedBytesSha256 and bytesVerified=false for registry mode.
Store binding to the exact candidate observation content digest on submission;
not arbitrary user-provided 'read=true'. Receipt records server response preparation,
not proof of delivery/human attention or trusted actor. No source contents needed.
A shared receipt token is not authorization: recheck current case/write/source
permissions every time, including all sources; reject before leaking source state.

## Transactional submission and compatibility
Keep existing conflict expectedVersion check. For EACH new/changed observation
with registered source require an explicit applicable receipt (missing428).
Within the existing reserved SQLite write transaction: authorize, load receipt,
check case/evidence/binding/schema, compare current registry version against receipt,
then write current conflict + full revision + receipt association + audit atomically.
Any changed source gives412 and zero writes, no automatic refresh-and-resubmit.
The error instructs preserve draft, reopen source and explicitly review/compare.
Multiple sources: exact expected set, no missing/extra/swapped IDs; any mismatch
rejects the whole write, preserving all prior history. Digest equality alone does
not certify original bytes, semantic correctness or human approval.

Unchanged observations/resolution-only notes preserve historical A association even
if registry nowB; never silently rebind. This means a status change cannot be claimed
as renewed validation of B. An explicit re-review operation needs its own contract.
Unknown legacy source history stays unknown; never create a historic receipt from
current registry. New edits to unknown/missing sources must either remain explicitly
unverified under an agreed workflow, or reject; do not silently guess a version.
This choice and affected old clients are not yet specified, so no production change.
Old reads stay compatible; old source-changing writes would fail428 intentionally.
Client must preserve draft and receipt across selection, not fetch latest token to
retry. No expansion of existing archive support or source visibility.

## Required ordinary synthetic acceptance matrix (planned, not executed)
- Unchanged A: receipt and current match; current+revision+audit commit together.
- A→B: old receipt rejected412, no row/audit/receipt-link mutation; preserve draft.
- A→B→A: use custody/version marker to detect intervening change, not sha alone.
- Two sources: one changed, missing/swapped/cross-case receipt reject all; both
  unchanged succeeds. Permission denial must precede revealing current digest.
- Old missing history: no invented beforeSources/receipt; explicit unknown remains.
- Resolution-only: retains A, does not claim B was read or checked.
- Policy tightened before submit: existing gate rejects; no automatic privilege gain.
- Failure during association/capture: ordinary injected transaction rollback.
- Concurrent registration change/write: serialize reads/comparison/write, no gap.
- Returned-byte mode excluded until permitted independently reviewed prerequisite.

Decision: remain DESIGN BLOCKED on policy-equivalent source read/receipt issuance,
old-client and unknown-source workflow, same-read original binding if demanded,
and persistent receipt lifetime/archive treatment. Do not add a loose caller digest
field and call the problem solved. No tests run this design-only turn; previous
3 ordinary synthetic tests are evidence of current gap, not verification of this
proposal. No real model/browser/production acceptance; no merge/deploy.
