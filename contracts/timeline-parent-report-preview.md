# Optional transient registered parent-report reference

Proposal and implementation scope: each registered CSV source may optionally send
parentReport={evidenceId, sourceSha256}. It requires comparisonContext.sourceNature
report_extract. No path, URL, caller bytes, approval or cross-case selector accepted.
Resolve the parent through the same case's local evidence-intake receipt, require
existing full-source access, .pdf filename and Document category, and verify exact
SHA and review state before and after W2. Existing intake8MiB limit applies. Four
sources maximum; no remote fetch or PDF parser is invoked. This verifies registered
file bytes, NOT that a file is a valid PDF or that its content supports the CSV.

Return separate reportSnapshots, one per declared CSV association, with registered
parent byte metadata and relationshipStatus=user_declared_not_verified. The same
parent may support several extracts; this does NOT mean independent corroboration.
No source mutation, durable relation/approval, database or archive schema change.
Legacy requests without parentReport continue with reportSnapshots=[]. Existing
sourceSnapshots shape remains unchanged. Existing authorization race limitations
remain; not an atomic lease or production authentication.


## Transient registered parent-report reference
Native implementation and separate native reviewer. Registered CSV preview accepts an optional same-case locally registered Document/.pdf ID+SHA declaration; verifies parent bytes/registration/permissions/review state before and after W2. Separate reportSnapshots bind checked parent byte versions to extract IDs but relationshipStatus remains user_declared_not_verified. No semantic extraction, valid-PDF, independent-source or fact-approval certification. Shared parent remains explicit; no mutation, receipt table/archive changes or durable approval.

Independent24/24 tests pass (20 primary +3 independent +1 public-report HTTP/W2). Final selected79/79 local regressions pass with zero skips, including actual W2/loopback tests. Pinned YANGZE22 public PDF now actually registered and referenced by known report extracts; unknown AIS heading vs true VDR remains rejected, single VDR preview unapproved. A separate synthetic CSV deliberately attached to real PDF verifies that semantic relation is NOT validated. No browser/UI parent chooser, real LLM, CI/full-system, merge or deployment claim. Legacy no-parent requests remain supported. See contracts/timeline-parent-report-preview.md.
