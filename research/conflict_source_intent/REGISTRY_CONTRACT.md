# Registry-only source observation: isolated executable contract

Baseaad6f7e. New research-only RegistryReceipts, no product imports/routes/migrations
or writes. This is NOT a deployed fix; original652ef41 behavior still reproduced.

The candidate uses actual existing source(s,case,role,id) full-content policy plus
timeline read on issue / write on comparison. It checks all sources before returning
any registry version. This is deliberately stricter than existing editable permission,
not proven equivalent. Consequently it MUST NOT replace/extend product endpoints.
Role labels remain self-reported; they do not authenticate a person or receipt holder.

Meaning: server constructed a registry observation. Not original bytes, human reading,
receipt delivery or judgment approval. bytesVerified/humanReadVerified/identityVerified
stay false. Values include derived current digest, registry doc hash, custody head
seq/hash; custody changes including A→B→A reject412. Any one changed source rejects
whole comparison; no source metadata in failure messages. No caller-supplied digest
can replace the stored observation. Returned object copies cannot mutate stored data.
Unknown/malformed registry version409, missing source uses existing gate403. No old
history backfill. Missing receipt428 indicates old source-changing clients require
upgrade; unknown/expired/wrong source set/wrong role409. Current permission checked
before receipt applicability/version information. Cross-case source lookup denies.

Receipt lifecycle is explicitly temporary: random UUID in process memory,10min
absolute monotonic expiry, max64 live receipts, max8 sources, no restart restore,
no archive/export. Clock reversal clears all receipts. Process-local/single-thread
research only; no production concurrent issuance or durable consumption claim.
compare performs NO judgment save, receipt consumption or audit append. It can be
repeated inside the validity window but grants no write authorization. Product
integration needs atomic receipt link/current/revision/audit commit and lifecycle
policy; this candidate does not implement it or claim rollback of product writes.
Unchanged observations and legacy missing history remain untouched in product.

Developer tests (temporary SQLite, synthetic registration/custody, no original files):
From service:
PYTHONPATH=.. .venv/bin/pytest -q tests/test_registry_receipt_contract.py tests/test_conflict_source_intent_gap.py tests/test_conflict_revisions.py::test_source_version_kept_when_only_resolution_changes tests/test_conflict_revisions.py::test_legacy_baseline_is_unknown_not_invented
12 passed in1.26s, includes9 new contract cases plus3 prior behavior checks.
Initial9 passed in0.87s. These counts overlap; not21 independent tests.
Coverage includes same two sources, A→B/A→B→A, missing/unknown receipts, exact
expiry and restart, unknown legacy digest unchanged, denied existing roles,
source subset and cross-case rejection. Existing product gap remains a passing
reproduction, not evidence it is fixed. No restricted security/ECFC tests, real
model, browser, production or independent acceptance. No merge/deploy.
