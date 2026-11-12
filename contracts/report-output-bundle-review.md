# Report output bundle A — independent contract pre-review

Reviewed candidate SHA256: `fcb89f170936ef67b278289acb2d479d10dac7fe065c8fae4c22c9b8863f7e02`.
Review only; no new implementation, runtime acceptance or security fix is claimed.

## Verdict

Design is feasible, but **revise the two contract gaps below before freeze**. No need for a new persistent receipt/table, a package version change or a change to global locks.

### Required clarification 1: source gate actually implemented

`reports.router.check_access` currently calls full-category policy gating, case availability and `report_draft` permission. `reports.service.get_report` only returns a deep copy. Neither performs per-citation evidence/interview resolution or confidentiality validation. Therefore the candidate's phrase “existing source confidentiality visibility checks” does not identify an existing reusable report check.

Specify the new endpoint's precise source scope and failure semantics. A conservative all-current-case evidence/interview visibility gate is possible, but must be named as such rather than described as citation provenance verification. If resolving references instead, specify supported citation kinds, same-case resolution, unregistered/missing references, deleted historical sources and opaque sourceRef/href fields. Do not follow URLs or assert that cited source originals match historical report text. Apply the defined gate at preview and both POST phases. A source-content change alone need not invalidate a deliberately stored report snapshot unless the contract expressly requires source-content freshness; source authorization changes must be rechecked.

### Required clarification 2: browser validation and identity lifecycle

Define whether client validation is merely whole-ZIP SHA verification or includes structural/member verification. The acceptance matrix currently says HTTP/ZIP validation, malformed ZIP/hash mismatch and exact four members without defining the browser acceptance boundary. If full validation is promised, require bounded ZIP_STORED parsing, exact unique names/count, no unsupported metadata/extra paths, manifest format/version and current case/report/format/language match, report member digest equal the chosen preview digest, member byte lengths/hashes and audit association checks. Use exact bytes for JSON member hashes, never JS canonical reconstruction. State strict JSON duplicate-key/non-finite handling or explicitly limit browser validation and reserve deeper checks to the server. SHA is consistency, not authentication.

Require generation tokens/identity binding for preview, POST response and download delivery: switching case/report/operator/role while pending must not display or save old response bytes. Preserve metadata-only unknown attempt under its original identity, not new identity. A late response must not silently resolve a different attempt. Local reload metadata is untrusted input and must be validated; no automatic POST after reload or preview refresh.

## Implementation safeguards / test priorities

- Existing `append_operation` returns actual seq; read the case-scoped row and exact snapshot_ref after flush. Its reason is untruncated; summary before/after is not a full-document proof. No need to extend old afterValue.
- Keep canonical report bytes captured before render immutable. Pass a separate deep copy to renderer, or detect renderer mutation, so report.json remains the input snapshot rather than a modified object after render.
- Both short phases must use fresh Sessions and WR then real SQLite BEGIN IMMEDIATE. Close phase 1 before renderer. Controlled second-connection report/policy updates during render must complete and produce 409/403 with no export audit, not timeout under a long lock.
- At phase 2 recheck row key/case and report.doc caseId/reportId consistency as well as schema. Include stored row timestamps in the server fingerprint as specified. Snapshot equality does not detect exact ABA, as correctly disclosed.
- Budget-check the preview's serialization too; otherwise an oversized stored document has an unbounded preview path despite POST limits. Define 64-depth checks before serialization/recursion failure becomes an uncontrolled error. The existing stated lack of a hard renderer CPU/RSS sandbox is honest.
- Prepare and validate the in-memory ZIP before commit, then construct/release the response after successful commit. Inject append/snapshot/ZIP/commit faults and a separate post-commit response fault; do not claim all errors imply rollback.
- Exercise both real PDF and DOCX with changed requested language; no stored doc mutation. Test new report.export reason through existing working-record archive runtime, not only schema validation.
- Preserve old export route semantics. New endpoint limits must not become editing, old export or general audit restrictions.
- Plain `application/json` media-type handling should state whether standard `; charset=utf-8` parameters are accepted; reject unsupported encoding rather than guessing.

## Accepted boundaries

Local role/operator headers are not authentication. A one-line unsigned audit association is not a verified full chain or evidence of actual commit to a trusted server. A successful response/download invocation does not establish durable browser save. Lost output cannot be recovered from server audit. New user-authorized generation can create a second event and different bytes. No hidden `.mcase` output preservation, full source archive, professional approval or automatic retry is promised.

## Second-round disposition — Design PASS

Re-read and SHA-verified revised candidate `cc4f5b9f988dfb08305f273ba8f383b768cbcff900cdc0bcdf3f792e4359559c` against the actual source. **Both first-round contract blockers are closed.** This supersedes the earlier revise-before-freeze verdict for that older candidate only.

- Section 3 now expressly adds `working_records_archive.service.full_access` at preview and both POST phases, with same-case row/document ID validation. The code has that reusable full-case helper. The contract accurately distinguishes conservative current-case authorization from citation closure, historical source availability and source-content freshness. Implementation must perform the additional row/document binding validation; the existing helper alone does not establish it.
- Sections 4/7 now define the exact bounded binary ZIP profile, strict JSON and member/request/preview/digest/audit associations, and late-response identity/scope isolation before any save. This is an implementable narrow protocol, not a claim that a generic ZIP library already enforces it.
- Preview budgeting and immutable pre-render canonical bytes plus separate renderer copy close the relevant safeguards. The audit line has no case field: case-scoped server queries and transitive reason digest -> report.json binding are now correctly stated. No fabricated audit fields or authentication claim is needed.

No remaining design blocker identified in this review. The implementation and independent runtime tests must still prove the protocol, short transactions, both real renderers, current-source refusals, rollback/ambiguous delivery behavior and old archive compatibility. **Design PASS is not product acceptance or a report that any new endpoint currently works.** The first-round review and its rationale remain above rather than being erased.
