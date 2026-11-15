# File publication / database coordination: decision and concrete prerequisite

Basef8649766f0f93f52db74abd04f3a52cbe042d969. Remote main read94d5e38;
independent SQLite candidate remote head unchanged. Read-only source assessment.
No runtime change, fault injection, recovery simulation or security probe this turn.

## Why the existing scaffold is not a recovery implementation

- research/conflict_source_intent/temporary_continuation.py:__init__/__exit__ owns
  TemporaryDirectory and calls cleanup on exit. Source bytes and inactive history
  survive only in that disposable DB. Reopening a durable operation is unsupported.
  This is intentional test lifetime, not evidence of unsafe product cleanup.
- package_intake/router.py:commit_sync publishes case_dir.rename(target) before
  Database.session exits/commits; except BaseException removes target if published,
  finally removes staging. No durable operation identity/state binds those objects
  to a recoverable result. Cannot copy this cleanup into the new candidate and
  claim an exception always proves rollback. Static finding, not a remote exploit
  or reproduction of lost committed data; restricted probes were not rerun.
- db.py:Database.session calls commit then rollback on exception, but does not
  classify commit acknowledgement uncertainty or durably record operation outcome.
- cases/service.py:load_case/list_cases read present rows without publication state.
  package/mcase.py reads CaseRow directly for export; intake receipt lookup also reads
  CaseRow directly. Adding one readiness check to a new handler would not establish
  application-wide isolation of a pending restored case.
- main.py:create_app initializes DB/routes but has no pending-import startup
  reconciliation. A recovery protocol must run before exposing affected cases.

These are missing integration prerequisites, not a claim that ordinary metadata-only
cases require original files or that all current cases are broken. No existing
permissions should be broadened or replaced by the readiness state.

## Proposed protocol (not implemented)

Use one destination SQLite database for operation ledger and business commit marker;
no second state database. Separate marker from active request receipts. Keep raw
input/archive-only receipts immutable and non-authorizing. Never overwrite an existing
case. Define recovery deployment assumptions first (local filesystem fsync/rename
semantics and process exclusion); do not silently assume these for every deployment.

Operation key: server-created ID + target case + source ZIP hash + owned staging ID
+ exact file inventory hashes. Record a durable claim before preparing files. File
manifest binds only the operation; it cannot substitute for DB commit evidence or
human approval. Write source ZIP and members exclusively in owned staging, sync files
and required directories, then verify exact inventory before publication.

A short-lived process lock alone is insufficient to prove ownership on restart.
Claim uniqueness must be enforced in SQLite; publication must not replace a target
owned by any different operation. Existing path checks plus rename are not an assumed
atomic no-replace guarantee. Implementation/platform support must be explicit and
ordinary tests must verify it in the selected environment without weakening safety.

Commit restored rows/history/audit, immutable inactive receipts, imported-prefix
mapping and operation commit marker together. The commit marker binds source hash,
case, expected object manifest, history-prefix digest and operation ID. Keep committed
but not verified-published cases unavailable through every relevant listing/read/write/
export route. Existing policy checks still apply after readiness. Startup and explicit
status inspection reconcile rather than rerun the import.

Publication completion is separate from business-commit acknowledgement; return a
pending/unknown operation response until a fresh DB read and object verification
prove matching committed rows and published files. Never classify a timeout/exception
as rollback merely because the request did not return success. Never blindly re-import
or delete a directory on that basis. Conflicting/missing durable evidence yields HOLD.

## Recovery decision table

| Persisted evidence | Allowed conclusion/action |
| --- | --- |
| Claim exists, no commit marker, staging incomplete | Not successful; retain owned objects, inspect. No automatic retry/delete. |
| No commit marker, complete staging verified | Prepared only; requires explicit eligible continuation after proving no concurrent/uncertain writer. |
| Matching marker, staging exists, published target absent | DB committed/pending publication; block case use. Publish only under proven ownership/exclusion. |
| Matching marker and exact target manifest | Candidate for ready after all row/history/file checks; then persist ready. |
| Target exists but marker absent, conflicting IDs or unverifiable files | Unknown/inconsistent; HOLD, no replacement or cleanup. |
| DB outcome unavailable | Unknown; no success, retry or deletion. |

This is not a distributed transaction or crash guarantee. The current code has no
implementation of these states/gates. A recovery observer must never infer old
history, activate archived receipts, regenerate original audit actors, or equate
registration hash with original authenticity.

## Minimum next implementation, before publication changes

1. Define compatible operation schema and typed pending/unknown result; add a shared
   readiness query and enumerate all CaseRow-facing routes, including direct queries.
   Existing cases without restore operation keep current behavior; only explicitly
   claimed new restore cases are gated. Do not mark all old cases unready.
2. Add startup/explicit reconciliation that reads actual ledger, source manifests and
   DB commit evidence but performs no cleanup/retry. It must work across process
   restarts, not only in-memory flags. Keep product experimental import409/422 blocked.
3. Then integrate owned staging and publication with the existing restored-history
   transaction, followed by isolated real filesystem/SQLite process restart and
   known exception tests. Test no success on unknown acknowledgement, no duplicate
   action and no deletion; all prior unchanged history/inactive receipt tests remain.
4. Only after those checks, independently review editable recovery/old package
   compatibility and application gating. Browser/identity remain separate acceptance.

This turn deliberately implements none of a new parallel simulator, new storage
format or partial product publication route. Existing restored-note SQLite tests do
not prove filesystem recovery. No tests run this turn; previous11/60 results remain
previous developer/limited independent scope, not new recovery evidence. No original
files/credentials accessed, no permission changes, no restricted safety/ECFC tests,
merge or deployment. restore_ready remains false.
