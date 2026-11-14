# Session recovery marker — independent review

Target `/workspace/mcis-evidence-refresh-recovery`, parent `d1a4424`. Read repository rules/handoff, pending.ts and Panel delta against prior failure-feedback change. No product edits, browser run, commit, push, merge or deployment by reviewer.

## Actual execution

Bundled independent `pending.ts` against the tree's real pending.ts, ApiError and commitFailure with existing esbuild, then executed Node: **60 independent assertions passed** (`results.txt`). Synthetic storage implementation permits deterministic quota/read/remove failures and silent dropped writes/removals. This is not a browser persistence/React interaction test.

Checks cover separate encoded case keys; only four fields persisted even when input contains extra bytes/declarations/operator; no replacement of existing markers; mismatching case/request digest/source digest/length cannot clear; failed or silently ignored deletion retains marker; quota/read failure or silently ignored set makes rememberPending throw; corrupt JSON/shape/extra fields/digest case/length remains untouched and blocks read/remember/forget; accepted zero and 8 MiB lengths; prior unknown remains locked despite recognized rejection, and INTAKE_INTEGRITY stays locked. Coordinator's original 88 tests, pending tests, typecheck and browser results are separate evidence, not independently rerun here.

## Code-path findings

* `save` records minimal case/requestDigest/sourceSha256/byteLength and verifies readback **before** invoking commit POST. If storage fails or another marker exists, that attempt returns without sending. Storage write success is not mislabeled as server commit success.
* Marker remains on generic/network/receipt-parse/integrity failures. The exact pre-registration allowlist may clear only this attempt's matching marker when no prior uncertainty exists. `forgetPending` rechecks all fields and verifies removal; any failure restores uncertain UI state. A changed marker cannot be cleared by a stale response simply because its case matches.
* Reset/open/effect re-read the current case marker; a corrupt/unavailable entry locks new registration rather than silently discarding it. The marker contains no file bytes, declarations or identity. Case-key isolation prevents a pending case A from directly selecting case B's receipt.
* Recovery is explicit GET only. Receipt must satisfy existing parseReceipt checks (including case/snapshot structure), then match the marker's four fields before removal and accept. Missing/404, malformed or mismatching receipt does not clear the lock or initiate retry. Restored state does not reconstruct body/preview bytes or silently POST.
* `live(version)` plus abort/version increments suppress stale response acceptance after navigation/identity changes; marker clear occurs only inside the live branch. The persisted marker is left for later explicit reconciliation when the original UI request is abandoned. This is code inspection, not an independent browser timing-race execution.
* First-attempt known rejection means this attempt was refused before new registration, not absence of earlier matching evidence. Previous uncertainty is never resolved by a later such rejection. Existing classifier semantics are retained.

## Identity and persistence boundaries

Marker intentionally has no principal. After role/operator change it remains case-scoped; current service permissions must authorize receipt GET. A matching receipt means a receipt for that case/request was verified under current access, **not** that the new operator originally registered it or has cryptographically authenticated identity. Existing role headers are unchanged. The request digest is an identifier, not a credential.

sessionStorage is per browser page session; it generally survives same-tab reload but is not a server lock, cross-tab mutex or durable crash/restart journal. New tabs, browser session policy, manual clearing, script access, eviction or closing can lose/copy/manipulate state. Same-origin code/DevTools can remove it; compare-before-clear is not an atomic cross-agent storage transaction. The UI warning correctly identifies tab-close/storage-loss limits. Digests and case IDs can themselves be sensitive identifiers despite omitting content and declarations.

This review does not prove reload/navigation timing, quota handling or storage blocking in every browser. It does not fix backend commit ambiguity, unsafe cleanup, file ownership or provide server idempotency/identity migration. Storage-deletion failure after a valid response conservatively leaves unresolved state; it must not be interpreted as proof that server save failed.

## Disposition

No new blocker found in the inspected scope and 60 executed assertions. The change provides conservative **same-session recovery metadata and explicit read-only reconciliation**, not durable global duplicate prevention. Full browser recovery/state-transition acceptance remains the coordinator's separate evidence. No claim that session markers establish trusted identity or universal exactly-once registration.
