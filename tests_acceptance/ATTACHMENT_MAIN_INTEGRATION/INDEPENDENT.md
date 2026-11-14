# Independent main-only attachment integration acceptance — 2026-11-14

Separate native review of `/workspace/mcis-attachment-integration-20261114`; no implementation changes, branch changes, commits or remote writes. The candidate is based on main `3aba2bf03e393909c611489ae573a887087637ac`, extracting only the PR64 and PR61 parent-to-head changes.

**Result:14 independent tests passed, zero skips. Candidate freeze10/10 matches. No blocking defect found within the narrow combined scope.** One pre-existing dependency warning concerns Starlette/httpx deprecation; it is not a failed assertion.

Command:

```sh
PYTHONPATH=service:. service/.venv/bin/pytest --import-mode=importlib -q tests_acceptance/ATTACHMENT_MAIN_INTEGRATION/test_independent.py
```

## Exact extraction evidence

- Six production files compare byte-for-byte with their source commit: PR64 attachment_access.py and evidence/router.py; PR61 filename.py, historical router.py, web history.ts and EvidenceIntakePanel.tsx.
- The candidate evidence_intake/router.py is independently reconstructed from pristine main by adding exactly four lines in the download transaction: import/call begin, and import/call protect_container. The full file intentionally differs from source64. No source-incarnation allocation or descriptor-safe read helper is imported.
- Git ancestry check confirms254167e (PR56 lineage) is not an ancestor of candidate HEAD; merge-base with declared main is exactly3aba2bf. This is extraction, not merging the97 ancestor commits.
- All10 entries in logs/attachment-main-integration-impl-hashes-frozen.txt match. Source freeze files describe their original baselines; only the candidate freeze defines this integration.

## Additional behavioral checks

- Both live routes deliver exact opaque ZIP bytes to an Investigator with all categories explicitly ReadOnly and no field rule; revoking audit access immediately rejects403/no-store with no content-disposition, original bytes or added Access audit.
- On both live routes, an injected failure after the real Access row has been appended rolls that row back and returns generic500/no-store without filename or original bytes. This tests transaction rollback, not only failure before append.
- A real synthetic ZIP is explicitly registered, exported in a real case package and imported into a new temporary database. Historical download under the full read-only policy retains exact bytes/hash and Unicode/emoji/percent filename. A failure after real historical Access append rolls back; subsequent policy revocation denies without filename or Access event.

The coordinator separately executed the new two-restore PDF/DOCX report-ZIP chains, source tests, frontend tests/build and broader regressions. Those counts are not represented as independently rerun here. The documented HFACS_CORE_UNAVAILABLE failure was reproduced by the coordinator on clean main; the independent14 tests above contain no skips or HFACS dependency.

## Remaining limits

Main's pre-existing intake registration/parent-path read behavior remains; this candidate does not provide PR56 descriptor-safe parent traversal, source-incarnation allocation or intake-commit reservation guarantees. Download-time reservation/gating is preserved. Roles/operators remain caller-declared headers, not production authenticated identity. ZIP detection is conservative and includes DOCX/arbitrary ZIPs but is not general DLP or source authenticity. Intake's8MiB limit remains.

No browser engine was launched by this reviewer. The coordinator's sandbox-enabled Chromium startup failure remains a browser acceptance blocker; transport/header tests do not prove native filesystem download, all platform filenames, visuals or production session security. No sandbox bypass, public listener, model call, deployment or merge claim.
