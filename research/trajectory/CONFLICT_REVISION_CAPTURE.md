# Forward conflict revision capture candidate

Branch feat/conflict-revision-capture; parent3ee41deaa3574a27c62f50c7198fcb09294b4066,
depending on the existing unmerged bounded archive chain. No push/merge/deployment.
Contract: contracts/conflict-revisions-v1.md; OpenAPI adds revisions GET.

## Concrete behavior

- Preserve full before/after values for creation, same-ID POST overwrite and PATCH,
  including long Unicode explanations. Existing accepted request/response shapes and
  timeline write policy remain; actor/role are explicitly unverified declarations.
- Add conflict_revisions table at normal create_all, no rewriting old rows. SQLite
  triggers forbid update/delete of revisions. Initial old baseline preserves only
  current known before value; unknown-before-capture remains for all later revisions.
- Reserve SQLite writer before policy/source/current reads; full current update,
  existing audit and revision insert commit/rollback together. Same-ID concurrent
  requests serialize and retain every successful value. This is not client optimistic
  concurrency control: stale clients can still win last, but earlier accepted values
  remain in the journal. No automatic retry or fallback on capture failure.
- Each side binds to SAME-CASE current evidence registry digest/custody head at capture.
  Unchanged observation retains old binding across a later evidence registry change.
  Changed observation captures the newer registry version. No original bytes read;
  bytesVerified=false. Missing references remain unresolved, no guessed SHA or zero.
  Legacy beforeSources=null; a later capture does not invent a historical version.
- Full-history endpoint requires timeline AND existing full-content access, then
  existing source gate for referenced old/new observations. Current row/sequence/hash/
  audit link checked before return. Missing/inaccessible referenced originals refuse
  rather than hide a revision. New endpoint and timeline router use existing no-store
  response wrapper. Existing ordinary conflict list schema/permission is unchanged.
- Journal is not accepted by current archive. Conflicts already select the closed-
  world preflight; refusal remains. No claim of complete conflict backup/restore.

## Ordinary developer tests

```
service/.venv/bin/pytest -q service/tests/test_conflict_revisions.py service/tests/test_conflict_archive_readiness.py service/tests/test_standalone_archive_preflight.py service/tests/test_consultation_archive_readiness.py service/tests/test_timeline_only_archive.py service/tests/test_timeline_import_origin.py service/tests/test_bounded_timeline_archive_increment.py service/tests/test_contracts.py service/tests/test_environment_w92.py service/tests/test_working_record_archive.py::test_three_store_roundtrip_and_inactive_receipts
```
Final result: **118 passed in30.02s**, no failures/skips in this selected group. Six new ordinary synthetic tests cover full overwrite/long text,
legacy baseline, registered version change without rebinding unchanged observations,
post-insert injected rollback (database/blob snapshots unchanged), two concurrent
HTTP writes using separate sessions, and history permission/case isolation. Three
prior characterization tests now assert forward preservation without deleting old
summary-truncation or ordinary source-declaration assertions. Existing archive
refusal and supported empty/1.2/1.4 workflow tests included.

Initial targeted run:7 passed/2 failed because assertions searched repr(SQLAlchemy
rows), which truncates long values. Replaced these with exact fields from revisions
API; this also corrects the weakness of the prior research's repr absence checks.
Code inspection still establishes the old overwrite/truncated-audit behavior, but
repr alone is not complete evidence of absence and must not be used as such.
Initial expanded run:117 passed/1 failed because new GET had not yet been declared
in OpenAPI; declaration added before final rerun. No runtime compatibility failure
was bypassed, no tests skipped or assertion removed to obtain a pass.

## Limits and pending acceptance

Synthetic database fixtures for registered evidence, no real file/model output.
No previous restricted historical-report integrity or ECFC probes performed. Ordinary
journal consistency checks exist but adversarial/admin-modification security review
not performed; hashes are not signatures. No authenticated SSO identity, true reviewer
approval, filesystem byte snapshot or guarantee of future raw-file availability.

Concurrent test is same-process HTTP with separate SQLite sessions, not multi-process
or production load/revocation testing. Lock waits use existing database behavior;
unknown commit/connection failures must not be auto-retried. History reads reserve a
writer and return full journal; pagination, growth/latency/memory/load not measured.
No process-crash/restore proof; all journal/current/audit mutations are one SQL txn,
with no added filesystem writes. Non-SQLite capture returns503, not a weaker path.

No UI/front-end integration or browser validation; new history API only. No full
suite/HFACS/core/model run, independent review or production acceptance. Old missing
history stays unknown and may block a future complete archive contract. Source-read
failures can block history for unresolved/deleted references; no partial success is
presented. Do not deploy before independent review of these semantics.
