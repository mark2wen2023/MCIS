# Most recent timeline import origin (candidate)

GET timeline adds `eventOrigins`, keyed only by returned event IDs. Every value is
`{status:"unavailable"}` unless the server has a locally created import index bound
to this case, current IntakeReceipt sourceSha256, and the exact persisted event row
(key, createdUtc, updatedUtc, doc; canonical sorted UTF8 JSON SHA256).
A match returns `{status:"restored-history", sourcePackageSha256, rowSha256}`.
This proves local restoration membership, not historical truth, trusted identity,
current review, or an authenticated originator. confirmed/presumptive remain the
original declarations. No API currently supplies proof of a new timeline review.
Unknown must not be called local/new/approved. No timestamps or labels infer origin.

The index is derived only inside the validated1.4 package intake transaction. It is
not accepted from a package, client, audit line or request. It contains no extra
business state: all indexed data are in the exact saved original package and receipt.
Before export, every index row must match that source, or export fails closed. A
missing index (old database) stays unavailable, with no automatic backfill. Current
row changes produce unavailable; source index still preserves the original binding.

No new archive version or member:1.4 row schema and original package/history bytes
are unchanged. On second restore a fresh index binds to the second package; the first
package and receipts remain in the existing historical artifacts/lineage. This is
most-recent-import provenance, not a displayed full lineage. Old1.4 packages without
an index are supported because exact source rows already exist; legacy formats
without authoritative timeline rows yield unavailable. Existing old readers ignore
the additive API field; database index is an internal rebuildable cache, validated
before exclusion from export. No silent whitelist-only exception.

Read follows the existing timeline authorization; it exposes only hashes of the
already returned row and source package, not receipt content, audit, or original
archive bytes. Original file access remains under its stronger existing checks.
Existing local filesystem, self-reported identity, crash-atomicity and long-lock
limitations remain. No historical-security or ECFC verification is authorized here.
