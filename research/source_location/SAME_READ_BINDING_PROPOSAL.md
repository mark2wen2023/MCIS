# Same-read binding: bounded proposal, NOT enabled

Parent assessment: 3b4e8fe0e5be7c65a1cfe21b0c8f93e6c81f60d8.
Current main checked again: 94d5e38c926fda232bb987b60fa9145e4bcf01a7.
Only ordinary public-source HTTP characterization was executed. No restricted
security test, policy bypass probe or historical integrity review was attempted.

## Smallest viable server change after existing blockers are resolved

Keep the existing access policy and its case-scoped enforcement; do not invent a
new viewer role or permit a repository-file fallback. The intended location of a
future binding is evidence/router.py:get_content inside its current WRITE_LOCK /
Database.session / reports.access.begin transaction, after authorization and before
Access is appended. An optional expected-source digest from a citation should only
narrow a permitted read; it can never authorize it.

1. Read the case-scoped item and custody-derived currentSha256 in that transaction.
   Validate the available trusted digest; absence or unsupported legacy binding is
   an explicit failure, not an empty string treated as a match. The initial
   item.sha256 and currentSha256 are not interchangeable after Change events.
2. Use an approved bounded, path-safe reader to materialize exactly one bytes value.
   Compute its SHA256 once. Compare it to the trusted current digest and, when
   supplied, the requested source version. Reject mismatch before returning any
   source or appending successful Access. Hashing a newly read value alone is not
   proof of registration-time consistency. Do not reopen or stream the file after
   checking a different buffer.
3. Retain protect_container and all existing authorization checks. Append Access
   with the digest of the exact checked response bytes, not an independently
   derived value that may differ. Do not append Verify or change evidence.status:
   this operation proves only equality of the served bytes to a selected digest.
4. Construct a response from that same buffer with explicit case/evidence/source
   binding. It must leave Database.session successfully (commit included) before
   delivery. The current Python contextmanager commits on exit even when the body
   uses return; preserve that ordering. Do not use a background task for audit or
   a generator that reads the file after the transaction ends.
5. A read-time version assertion is not perpetual freshness. A later Change/revoke
   may occur after commit. A reader must clear stale UI responses on case/selection
   changes and must not label source-text equality as verified quotation content,
   factual truth, a PDF page open, or production-authenticated identity.

## Failure semantics to specify before implementation

- Ordinary forbidden/not-found behavior remains unchanged and must not disclose
  source bytes or digest details to an unauthorized caller.
- Malformed request digest: validation error; missing trusted digest, unsupported
  binding or mismatch: explicit version unavailable/conflict. Never silently use
  repository bytes or a historical version that is not stored/authorized.
- Preserve zero successful Access on known precommit validation failure. A failed
  or uncertain commit must produce no source response; do not claim rollback was
  certain, nor instruct automatic retry when commit outcome is unknown. A failed
  transport after successful commit may have recorded Access without delivering
  all bytes; no exactly-once delivery claim.
- Retain existing lock/transaction semantics. No performance claim: bounded reads
  still retain memory and writer-lock costs. SQLite's transaction does not prevent
  external filesystem writers; trusted digest comparison and one response buffer
  are necessary, and the safe-reader prerequisite remains separate.

## Why there is no runtime patch in this branch

Main still has the source-observed content-vs-metadata policy inconsistency and
unbounded legacy path read recorded in INTERNAL_READINESS.md. Adding digest equality
alone cannot fix those prerequisites, and enabling another viewer would expand use
of that path. This task does not authorize changing policy or repeating restricted
security verification. Stop at the proposal until the minimal reader/policy safety
dependencies are separately reviewed on the current base. This is not a claim that
all concurrency or filesystem behavior has been verified.

## Ordinary tests and later acceptance

Existing new test checks exact seeded public bytes, response hash, metadata hash,
Unverified status, one new Access, lack of intake receipt, wrong-case 404 and Public
403. Extended ordinary test checks the returned public source's Access digest and
that no Verify is emitted. This is the unchanged normal path, not evidence of
adversarial consistency. Later accepted implementation would require explicitly
approved failure/concurrency acceptance; it is not executed by this proposal.
