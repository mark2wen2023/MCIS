# Server idempotency study — restricted metadata-only candidate

Basefe3fb05 (frontend recovery line); no production route/schema/config added. This branch does not inherit the separate cb04aa6→... safe file-read/rollback security chain. Existing file registration is not repaired here.

## Current state

Legacy evidence registration has no client request key or immutable response ledger. Evidence Intake derives a request digest from original bytes/declarations/role/operator and finds receipt through Evidence + Register custody detail, then rereads file. Current role/operator headers are caller-supplied, not a verified principal. A role/name/content change changes that binding. Integrity409 may refer to an earlier committed registration; a missing receipt alone cannot prove no commit. Main db.session commits on successful context exit, and its rollback after a commit exception cannot undo an already committed transaction. Evidence Intake also performs filesystem creation/cleanup outside SQLite atomicity.

Therefore adding a request-ID column around the existing file path would not establish durable cross-resource commit semantics. A safe production byte path needs a separately reviewed immutable object transaction/publication/reconciliation design. No automatic retry or compensation deletion is introduced.

## Restricted executable candidate

Metadata/SHA-only: accepts exact metadata fields and explicit lowercase SHA, rejects body bytes/path/client role. It does not assert SHA corresponds to possessed original bytes or authentic source. `contentStored:false` in result. Uses existing EvidenceRow, next_id and append_custody (including actual Audit row), but only in synthetic temp SQLite. Explicit install_schema creates research receipt table with unique(scope,request_id) and no UPDATE/DELETE triggers. No existing app imports this module. Production startup has no new schema or registration route.

Scope: server-managed store_epoch + verifier issuer/subject + case ID + authoritative generation + request UUID. Binding: versioned operation + exact scope + all validated metadata. Role is assigned by current authorizer, never caller metadata; its policy is rechecked before both registration and replay. A changed request body conflicts409; no overwrite. Request IDs scope operations, not authority. Different keys intentionally create distinct registrations, so this is not content deduplication.

Expected case generation must come from a prior authoritative context/preview and is checked against the authorizer's current server generation. Old expected generation rejects409 after case recreation. Store epoch must be server-configured, durable and restore-aware; tests use synthetic constants, not a production authority. Backups/imports may not activate foreign request receipts. Current product lacks this identity/epoch infrastructure: a release blocker.

Verifier and CaseAuthorizer are dependency interfaces only. Verifier must validate genuine credentials, issuer/audience/signature/expiry/revocation; the candidate only validates returned Actor shape/expiry. There is NO built-in/default provider or fake JWT. Missing provider/store epoch503; invalid actor401; missing/mismatched grant403; changed case generation409. Test doubles are explicit synthetic V/A. They use trusted fixture grant rows inside the supplied session. Do not expose fixtures as SSO. Authorizers must not commit/rollback or mutate transaction boundaries; this is trusted server code, not a sandbox.

## Transaction / revocation

Acquire existing process WRITE_LOCK first, then BEGIN IMMEDIATE on SQLite connection precedes case grant lookup, case policy, ID allocation and receipt lookup. Evidence, custody, audit and response receipt commit on that connection together. The lock order matches existing domain writers (WRITE_LOCK before SQLite reservation), avoiding an inverted wait with append_custody. Threads also serialize through that process lock; real separate processes rely on SQLite reservation, not a shared Python lock. Replays preserve original response and append no registration/audit.

A local revocation that commits before reservation is observed. Revocation attempted while registration holds the writer waits; already-authorized registration may commit first, then future replay/recovery denies. This defines local DB ordering, not remote/instantaneous IdP revocation. Remote authorizer state cannot magically join SQLite transaction. Full writer holds remain; no throughput claims.

Precommit injected failures roll back all four record types; existing receipt absence still returns unresolved with automaticRetry=false/automaticDelete=false. Actual postcommit acknowledgement loss is reconciled with exact request/binding. Commit/connection errors propagate, never assumed safe-to-retry and never translated by this study into guaranteed not-committed. No service auto retry. Recovery itself reserves writer to avoid stale in-flight absence observations.

Receipt recovery compares current Evidence projection and Register digest/absence of Change. It is a conservative integrity check; mutable note changes can block replay although the original historical transaction committed. It does not claim complete tamper-proof DB or audit-chain validation. Ordinary triggers can be disabled by a DB owner. Existing generic export/restore has no awareness of this ledger: never enable this candidate or declare archives complete without versioned receipt/history handling.

## Failure and acceptance boundaries

Tests use real temporary SQLite, actual domain/audit functions, independent connections and real child processes; fault hooks explicitly simulate stage failures/ack loss. Process os._exit tests are not power failure, fsync durability or stale backup recovery. Cross-process tests share one local SQLite file, not a distributed database.

No original bytes stored/read/exported, no filesystem cleanup, no model calls or internal network. Full file registration transactionality, actual trusted identity/authorization provision, epoch/backup lifecycle, audit-provenance integration, schema migrations, resource limits and production performance remain blockers. SHA-only prototype proves a database-level transaction pattern, not full evidence authenticity or production-grade idempotency.
