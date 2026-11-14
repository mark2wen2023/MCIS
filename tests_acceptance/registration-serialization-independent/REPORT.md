# Independent registration serialization review

Target: `/workspace/mcis-registration-serialization`, base `a38d748`. Only candidate product delta reviewed is `evidence/router.py` registration scope: `with WRITE_LOCK, ctx.db.session()` plus existing `reports.access.begin(s)` before case/policy reads and ID allocation. No reviewer product edits, commit, push, merge or deployment. Synthetic bytes/cases and role headers; no authenticated-identity or production-performance claim.

## Actual verification

Final command:

```sh
PYTHONPATH=service service/.venv/bin/pytest -q \
 tests_acceptance/registration-serialization-independent/test_independent.py \
 service/tests/test_registration_serialization.py \
 service/tests/test_legacy_evidence_base64.py \
 service/tests/test_legacy_evidence_checksum.py \
 service/tests/test_content_visibility.py \
 service/tests/test_policy_write_busy.py
sha256sum -c logs/registration-serialization-impl-hashes-frozen.txt
```

**86 passed in 15.41 seconds**, recorded in `results-final.txt`; product frozen hash **OK** (`d8aedca9f31a20370b9453f7ae824a21f84b83daf1bc6a4c55629d1a3f438ffe`). This selection contains eight independently authored cases (including four invalid-input parameters) and 78 existing implementation/regression cases. Earlier smaller selection: nine passed in 5.93 seconds (`results.txt`); these runs overlap and must not be added together as unique coverage. No broad/full-suite claim or .NET execution.

Independent cases:

* Two real loopback Uvicorn server processes, shared temporary SQLite/blob directory, eight concurrent HTTP POSTs divided between the servers. Separate process-local RLocks cannot serialize across these servers; each server deliberately delays 120 ms after next_id to expose overlap. All eight return 201 with unique IDs. Exactly eight evidence/custody/audit rows and eight files; response digest, stored source/path and original binary bytes match each request; custody and audit chains verify. Servers terminate in finally cleanup. The delay is test instrumentation, not a production behavior or performance measurement.
* A separate raw SQLite connection reserves the writer, changes Investigator evidence_meta to Deny, then commits after registration reaches BEGIN IMMEDIATE. The waiting registration returns 403 with zero file/evidence/custody/audit writes. This independently confirms the policy read follows writer reservation and sees an earlier committed revoke.
* Noncanonical base64, invalid base64, mismatching expected digest and invalid digest each return 422 without files/rows/audit. An immediate independent SQLite BEGIN IMMEDIATE after each rejection succeeds, establishing reservation cleanup; a following valid empty-file registration returns 201 with the exact empty file. Valid non-UTF8 bytes and uppercase matching expected SHA are exercised in concurrent registrations.
* Two registrations requesting the same explicit path produce exactly one 201 and one 409; file bytes and sole metadata belong to the winning request, with one custody and one audit event. Existing-content conflict handling survives serialization.
* Public role with malformed base64 returns 403 before the strict content validation response and writes nothing. This is the existing role-header policy, not proof of authentication.

Existing focused tests rerun additionally cover the reverse revoke order: a registration already holding reservation blocks the policy writer, whose initial reservation timeout returns 503/not_committed; after registration commits, a successful revoke makes the next registration 403. Existing strict input, checksum, GET visibility, unknown-commit and policy-lock timeout tests all pass in the selection.

## Code-level conclusion

`db.py` session context commits before leaving the outer RLock; exceptions roll back and close the session. `begin(s)` reserves SQLite's writer before load_case, require, next_id, decoding, file creation and custody/audit append. The RLock is reentrant, so nested append_custody/audit locking is compatible. BEGIN IMMEDIATE serializes cooperating SQLite writers across processes, including processes whose Python RLock instances differ. Each next_id therefore sees the previous committed registration in the tested SQLite environment; policy update cannot commit between the authorization read and this registration's transaction commit.

The change preserves the strict base64/checksum branches and all GET code. It does not catch commit exceptions or manufacture a new not_committed status. Registration reservation timeout is not the policy PUT-specific 503 contract; this patch introduces no new timeout classification or automatic retry. Context managers retain the lock until session commit/rollback completes. An uncertain commit remains uncertain.

## Boundaries / remaining work

* This is **not an aggregate memory/admission fix**. FastAPI may already buffer/parse the request before entering the handler. Decoding now occurs under the registration lock; queued parsed requests, other routes, response/transport buffers and worker population remain separately unbounded by this patch. No size cap was changed.
* This is **not filesystem/database crash atomicity**. File writing precedes metadata validation/DB commit; a subsequent failure or process crash can leave an orphan file. No transactional filesystem staging, cleanup journal or complete fault-injection campaign is provided. External local filesystem mutation is outside SQLite's protection.
* Cross-process guarantee demonstrated here is SQLite-specific, on one local shared database and filesystem. `begin` does not reserve writers for other DB dialects; distributed/multi-database configurations, noncooperating filesystem writers, all possible legacy writers and network filesystems are not certified.
* The two-server test is one bounded local synthetic execution per run, with deterministic delay to increase overlap. It is not exhaustive scheduling proof or production stress certification. No claim that all cancellation, I/O failure or disk-full paths are fixed.
* Policy headers remain unauthenticated in this development system. Authorization consistency is tested, not identity provenance.

Disposition: **focused registration ID/metadata race repair passes this independent review in the tested SQLite environment**, with the above limits. No new blocker found within this candidate's stated scope. Aggregate resource and FS–DB crash-atomicity gaps remain explicitly open.
