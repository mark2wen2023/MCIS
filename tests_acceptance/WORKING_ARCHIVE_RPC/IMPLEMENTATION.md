# Working-history supplemental archive trusted RPC

This slice connects the existing supplemental archive service to a fixed-scope trusted Python host and an explicitly fictional seeded stdio demonstration. It does not mount a legacy HTTP route, accept credentials or paths from the client, perform production login, deploy, or demonstrate real model inference.

## Contract

`agents.working_archive_rpc.WorkingArchiveRPC(db, settings, session_token, case_id)` takes trusted constructor values only. Public scope is profile `mcis-working-history-archive-trial-v1`, random contextId, fixed caseId and productionLogin=false. Target case incarnation and epoch are captured and rechecked, not silently rebound. Methods:

- export: no extra fields; returns standard base64 canonical JSON supplemental package, SHA and completeBackup=false.
- import: only bundleBase64; same package digest is the durable idempotence key.
- list: no extra fields; authorized inert import summaries.
- read: only sha256; authorized inert historical payload.

Each request includes profile/contextId/caseId/requestId/action. No original source path, file name, token, provider, supplied model result, author override or legacy role header is accepted. Every requestId is pinned to its whole payload, at most 64 per host. No successful content response is cached across authorization changes. Import and read use separate current ArchiveGrant permissions; read does not require missing historical original sources or a live WorkingGrant. Export rechecks live binding via the underlying service and again after the worker result. Closing or cancellation does not revoke previously committed writes. Once an import worker starts, a failed response is unconfirmed, not proof that nothing was saved; retry exactly the same package.

## Bounds and transfer

Request shape and individual string limits are checked before JSON serialization/deep copy. Raw packages are limited to 8 MiB, canonical standard base64 length to 4*ceil(8MiB/3), outer UTF-8 JSON request/response to 12 MiB. Base64 is strictly decoded and re-encoded for canonical equality. Archive schema/digest validation is delegated to the existing strict service. stdin lines and output enforce the outer budget; 64 requests, 30-second idle reads and 300-second read deadline. These are not a hard total wall-clock or SIGKILL cleanup guarantee.

`python -m mcis_service.agents.working_archive_fixture` accepts no CLI args, seeds synthetic interview/proposals/review, provisions an internal temporary SQLite session/grants, and deletes its temporary directory on normal exit. It does accept explicit archive bytes over its protocol; users should use synthetic packages only. It cannot technically prove imported text is fictional. Same-process list/read can recover imports; the temporary fixture does not retain them across process exits.

## Verification

`test_working_archive_rpc.py`: **14 passed, 0 skipped**, 13.25 seconds. Real SQLite scope/grants, export/import/read/list, same request replay, altered request reuse, forbidden fields, malformed/noncanonical base64, separate import/read permissions, closed/cross-case requests, and actual stdio child-process full roundtrip with two fictional proposals and one working-review revision. One pre-existing Starlette/httpx deprecation warning.

This package contains proposals, citations, working review revisions and historical source declarations only. SHA is integrity checking, not signing or historical-authenticity verification. No complete original interview/evidence backup, disaster recovery, production browser IPC, verified factual findings or real LLM quality is claimed.

Candidate product hashes:
- working_archive_rpc.py: 93d3b3e472c0d44a88b349e0d0175708e625b7a5bcde1c4fa36c26f92bdd41dd
- working_archive_fixture.py: 227f3bcc6544f7bcffee90047eac11bff0e53f6e0f492854ee0c36918e4c3186

Independent review is reported separately. No push/merge/deployment performed by this implementation worker.

Independent review found a real final-projection race: changing the live interview during response serialization could return the previously checked bundle. Fixed by re-exporting/revalidating all live bindings and comparing exact bytes **after** response materialization and terminal permission checks. No further content projection follows that final guard. Corrected candidate is under combined regression.

Final combined rerun: `test_working_archive_rpc.py` + independent `test_archive_rpc_catalog_review.py`: **41 passed, 0 skipped**, 39.23 seconds, including the fixed final-projection source-change regression. Candidate hashes above are frozen. The first combined invocation used a nonexistent independent test filename and collected no tests; corrected invocation produced this result.
