# ECFC archive extension: proposal, NOT an allocated .mcase version

Source checked: PR #42 head 9a8d16a2574430b84ef07778b77b8a9d0df89365, open draft, base 3aba2bf. Local models/router and previous guard investigation inspected; full local-to-remote source comparison not performed. Existing ECFC export guard and explicit save acknowledgement must remain unchanged.

## Proposed preservation unit
A case-scoped envelope contains current document (nullable), complete ascending audit snapshots, historic receipts, evidence-reference inventory, source case identity, and archive profile. A digest protects accidental corruption, not authenticity. Do not allocate a numeric .mcase version until reconciled with W7 and current archive contracts.

History is never truncated to the UI's latest-50 limit. Each audit snapshot must pass the existing document/event validators. Require revisions 1..N without gaps; initial before=null and prevHash=64 zeros; subsequent before equals preceding after and prevHash equals preceding hash. Current must equal final after. Any orphan audit/receipt/current state is rejected, not silently dropped. No rewrite of historical source identities, actors or timestamps.

Each saved request has exactly one matching audit requestId; duplicate IDs rejected. Receipt response document must equal that audit's after snapshot, and actor/role must match the event. Request digests are preserved; they cannot be reconstructed from incomplete historical request bodies. This limit must be explicit rather than claiming cryptographic proof of original requests.

## Restored receipt policy
Historic receipts are immutable archival records, not immediately active idempotency records in a new case. Restore must create a fresh mutation generation and reject old request IDs explicitly. Preserve original request IDs in history with source case identity. Do NOT feed old response documents to new mutation calls. This needs a dedicated generation/tombstone design and independent tests before implementation.

## Evidence references
Collect the union of sources from every historical snapshot, not merely current nodes. Preserve each historic source descriptor and its content hash. Distinguish removed/changed evidence from corruption. Do not resolve a historical descriptor silently to a different same-ID current item. Exact referenced bytes must be included, or the selected archive profile must explicitly reject export. Metadata-only export is a separate intentional profile, not full restore.

## Restore transaction
Authorize access before disclosing existence; parse bounded input with strict members, duplicate-key rejection, finite values and exact integer types; validate all documents, chain, receipts, evidence and profile before any writes. Restore only into a new isolated destination with ID mapping retained separately from immutable original documents. Write case, documents, history, receipts, source blobs and manifest as one publishable unit. Files need staged storage and rollback/recovery design; a SQL transaction alone does not make filesystem writes atomic. No existing data overwrite.

## Required acceptance before removing guard
Round-trip preserving full histories and hashes; >50 revisions; source revisions and removed evidence; audit-only/current-only/receipt-only; missing/extra/duplicate receipt; duplicate keys; bool/float revisions; corrupt chain/hash; unknown schema; traversal and resource limits; rollback after each DB/filesystem stage; request replay across restored generations; role-denial before disclosure; restore/re-export; concurrent save/export consistent snapshot; cancellation/repeated UI actions; actual browser verification. Existing refusal must remain until whole lifecycle passes.

## Isolated prototype scope
The accompanying pure-Python planning validator checks only revision continuity, snapshot adjacency and receipt relationships using supplied validators. It neither parses archives nor validates ECFC semantics, writes a database, restores a case, verifies evidence, invokes LLM/C#, or removes the existing export guard. Synthetic tests exercise this small contract sketch only.
