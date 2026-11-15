# Conflict stale-screen compare-and-write

Branch feat/conflict-expected-version, parent207e3a652dc5d5016683840bfec80cc7473ac480.
Dependent on unmerged conflict capture/archive stack. No push/merge/deployment.

## Implementation and compatibility

New GET conflicts:editable pairs current conflict and token in one SQLite transaction,
under existing timeline permission; original GET shape is unchanged. Token binds case,
ID, complete current doc and latest journal SHA. Existing-ID writes require a matching
expectedVersion; missing428/stale412/bad-format422. New-ID creates stay compatible.
Same-ID POST cannot bypass PATCH protection. No new authorization rule or archive
support. Old write clients must upgrade; silent legacy overwrite is deliberately not
retained. Legacy rows obtain tokens without fake history or database backfill.

Frontend uses this pair, captures edit-start version for a note and sends it unchanged.
A background/manual list refresh cannot silently rebase that note. Status changes use
the displayed row version. On412/428 local note remains with a persistent refresh/
compare message and explicit refresh button; no auto-retry. A subsequent user selection
loads that selected row's text/version, so users are told to preserve their draft first.
Existing last-write behavior in parent capture contract is superseded by mandatory CAS.

## Developer verification

```
service/.venv/bin/pytest -q service/tests/test_conflict_expected_version.py service/tests/test_conflict_revisions.py service/tests/test_conflict_archive_readiness.py service/tests/test_conflict_revision_wording.py service/tests/test_standalone_archive_preflight.py service/tests/test_consultation_archive_readiness.py service/tests/test_timeline_only_archive.py service/tests/test_timeline_import_origin.py service/tests/test_bounded_timeline_archive_increment.py service/tests/test_contracts.py service/tests/test_environment_w92.py service/tests/test_working_record_archive.py::test_three_store_roundtrip_and_inactive_receipts
```
125 passed in34.50s. Includes two same-user logical sessions on new and legacy rows,
stale save refusal with database/blob snapshots unchanged, explicit re-read/reviewed
save, missing-token old clients, same-ID POST bypass refusal, malformed token, ABA,
and simultaneous same-token writes (one200/one412, one successful revision).
Existing rollback/history/source and archive compatibility/refusal tests retained.
The earlier concurrency test is updated to assert stale rejection rather than allowing
both requests to overwrite. Non-concurrency journal tests use a clearly named helper
that retrieves fresh tokens; the stale-client tests do NOT use that helper.

Existing ordinary test adapted to supply token (audit assertions preserved):
`service/.venv/bin/pytest -q service/tests/test_cases_timeline.py::test_conflicts_patch_audited`
1 passed in0.46s. No full cases/core suite or restricted operations run.

From web:
```
./node_modules/.bin/esbuild tests/conflict-version.test.ts --bundle --platform=node --format=cjs --outfile=/tmp/mcis-conflict-version.cjs --log-level=warning
node /tmp/mcis-conflict-version.cjs
npm run build
```
8 constructed model/body assertions passed: refreshed row token differs but original
edit token remains in write body; missing/bad tokens refuse; warning text includes
unsaved draft/manual refresh/no retry. Final TypeScript/Vite build passed; existing
>1500kB bundle warning remains. An initial root-relative edit/test command was launched
from web and failed path lookup; corrected cwd before actual tests and final build.

## Not claimed

No real browser interactions, screenshots, mobile layout or independent precise-build
acceptance. No browser dependency installation or sandbox bypass. Previous environment
lacked Playwright; no new browser launch in this turn. No production/multi-process load,
SSO, original byte verification or crash/retry guarantee. Source binding still records
registry version only, bytesVerified=false. Same-token races tested with separate
SQLite sessions in one process. Users with unresolved history/source prerequisites
remain subject to existing gates; tokens do not override those errors. No full suite,
HFACS/LLM/ECFC/restricted historical-security tests. Development verification only.
