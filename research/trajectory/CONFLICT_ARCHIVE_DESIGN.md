# Conflict archive: next slice and prerequisites (not enabled)

Base88339848934e4c35523618587ad47b32c96869b4, branch
research/conflict-archive-readiness. Main checked94d5e38. Only synthetic tests and
this proposal; no production code, archive support, permission or parser changes.

## Choosing among the existing six tested states

| Existing state | Why not the first complete-history increment |
|---|---|
| Recommendation | Cause-node IDs lack generation-time source snapshot; draft edits replace content and summarized audit is not a full revision store. |
| Ordinary agent draft | Kind-dependent payload/targets, modified review payload, applied interview/timeline effects; cannot restore as a new approval or active replay. |
| COLREG current / inputs | Must include all run/index/annotation/input dependencies and immutable computation inputs; current alone omits other keys. No actual C# core was run. |
| Persisted simulation command | Operational queue plus audit, no archive-only replay contract. Restoring as live commands is unacceptable; not chosen. |
| Conflict | Two inline observation values and a small status/resolution model are the least cross-module-dependent. Chosen for design, but full historical state is not currently retained. |

Consultation is already separately assessed in NEXT_ARCHIVE_CONSULTATION_DESIGN.md;
its circulated-report binding remains a prerequisite. None of these are made supported
by this report. The existing standalone preflight refusals remain unchanged.

## Actual conflict data and writer behavior

contracts/schemas/conflict.schema.json describes inline observations a/b with sourceLabel,
valueText and optional numeric/time/evidenceId fields. ConflictRow is a mutable
DocMixin row, storing only current doc and created/updated timestamps. No evidence
version hash, source extraction location or immutable historical snapshot is included.
contracts/CONTRACTS.md preserves manual status/resolution; it does not promise a full
revision journal or permit inventing absent historical originals.

POST timeline/router.add_conflict uses put_doc without duplicate-ID refusal; same key
updates current doc. Its audit after contains summary only. PATCH patch_conflict writes
current status/resolution; diff_summary is then truncated by audit.service._summ at
400 characters. No independent full before/after copy exists for conflict changes.

## Ordinary reproducible evidence

Command:
```
service/.venv/bin/pytest -q service/tests/test_conflict_archive_readiness.py
```
**3 passed in0.62s**, synthetic normal HTTP only with temporary SQLite/directories:
1. Create conflict; patch a long explanation then a new explanation. Current row has
   final text, first audit after and second audit before are400 chars; distinctive
   tail of earlier explanation is absent from all temporary DB table contents.
   Audit chain remains valid. Export remains409 with no DB/blob mutation.
2. POST same C-01 twice with different a.valueText. Both return201; one current row,
   two summary audit records, old observation marker absent from database. This
   establishes missing full previous content, not malicious historical mutation.
3. POST observation referencing EV-999 with empty evidence list succeeds. Reference
   is a declared ID, not a validated evidence/version association. Export remains409.

These are existing ordinary writer behaviors, not a security-bypass claim and not
retries of restricted report-history integrity or ECFC tests. Three passing tests
characterize barriers; they do NOT demonstrate successful archive/restore.

## Concrete proposed versioned format (design, no version reservation)

After prerequisite capture is implemented/reviewed, introduce an explicit next profile
(tentatively1.5, pending version allocation review), keeping1.0–1.4 meanings unchanged.
Older readers reject it. Never retrofit new fields into closed1.4 members silently.
A new conflicts/records.v1.json would contain:
- format/version/caseId and bounded exact row envelopes key/createdUtc/updatedUtc/doc;
- immutable revision entries with caseId/conflictId, ordinal, before/after full docs,
  operation, actor declaration, timestamp, matching original audit sequence and hash;
- source bindings per revision and side: exact evidenceId/version/digest plus archived
  source location when known, or explicit unregistered/unverified inline declaration.
  A free sourceLabel must remain a declaration, not become a verified file identity.

Preserve absent vs null fields, original timestamps and units. Do not recompute delta,
change status, auto-accept old resolution, or relabel historical actors authenticated.
Current row must equal final journal postimage. Verify per-case identity, sequence,
operation relationships and closure for every supplied evidence/vessel reference.
Do not replay the journal as live business writes during restore. Insert inert history
and current state in existing transaction/staged publication, retain original audit
and ancestors. Legacy mirror analysis/time-alignment.json must exactly match current
rows, not become a competing authority. Do not whitelist arbitrary tables/payloads.

## Prerequisite implementation order

1. Define source-capture and full conflict-revision contracts for FUTURE ordinary
   creates/updates; persist full before/after and source-version binding atomically
   with current row and audit. Decide duplicate-ID semantics explicitly without
   silently breaking existing clients. No permission change or automatic verdict.
2. Identify a trustworthy capture-start boundary. Existing rows cannot be retrospectively
   labelled complete: capture their present state as an explicitly legacy baseline,
   never fabricate missing prior observation or long explanation. A complete-history
   export mode must refuse unknown earlier history. An incomplete-history archival
   mode would require a separate explicit product contract and honest labeling.
3. Only then implement new-version export preflight, strict parser, transactional
   restore and source-history preservation; retain refusal for recommendations,
   consultations, agent drafts, COLREG, commands, track-history combinations not
   specifically supported. Unknown references/versions/content -> whole refusal.
4. Test ordinary create/update with long Unicode fields; two-source version bindings;
   same-case closure; three-store rows/raw bytes/journal/audit equality; unsupported
   states and unknown legacy history refusal; old-reader rejection and existing
   1.0/1.2/1.4 compatibility; injected rollback without partial published package.

## Why no runtime/archive implementation this turn

Copying present conflict rows plus truncated audit would preserve existing bytes but
would NOT supply the complete history and reliable source association requested.
Restricting to Open rows alone is insufficient: a reused ID can be Open after replacing
an earlier observation, and ordinary evidence references are unverified. Neither row
status nor current timestamps prove an untouched original. Current data cannot safely
satisfy the stronger promise. No partial serializer or broadened whitelist is shipped.

No frontend/browser/core/model/full-suite or independent validation. Existing109 tests
belong to the parent and were not rerun here. Historical information already absent
cannot be recovered by a migration without genuine earlier originals. This plan does
not claim otherwise. No push, merge, deployment or restricted operation.
