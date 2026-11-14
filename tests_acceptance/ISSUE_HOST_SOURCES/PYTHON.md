# Python host source discovery implementation and tests

Implemented `sources` action in `service/mcis_service/investigation/host_bridge.py`. Existing `save`/`read` preserved. Requests require fixed profile/context/case/request ID, reject any supplied issueId/operationId/expectedRevision/entry (including null). Uses only existing protected ASGI current-source catalog, with generation/epoch/auth checks before and after await.

Minimal response body: profile `trial-issue-sources-v1`, caseId, items with evidenceId/sourceSha256/mediaKind/byteLength/registeredUtc; scope `current-local-supported-candidates-only`, selectionSnapshotPinned=false, observationApproval=not_assessed. No raw source bytes, paths, actor IDs, registration receipts or credentials are projected. Response catalog profile/scope/case/generation/epoch, unique IDs, bounded list, hash/media/strict integer bytes/aware timestamp are checked. Discovery does not pin a source at selection time; journal save independently revalidates current sources.

Final tests: **47 passed, zero skipped, 28.18 seconds** (22 new source tests plus existing 7 main and 18 independent bridge tests), known deprecation warning only.

Command: `PYTHONPATH=issue-journal/service mcis-work/service/.venv/bin/pytest -q issue-journal/service/tests/test_issue_host_sources.py issue-journal/service/tests/test_issue_host_bridge.py issue-journal/service/tests/test_issue_host_bridge_independent.py --disable-warnings`.

Additional actual fixture subprocess call returned EV-001 and EV-002, both synthetic CSV sources, each36bytes, with dynamically generated registration times. No fixture changes necessary; existing trusted prepare function creates them without calling legacy HTTP.

Product SHA256: `f10c52e6a31434c7c5eb16f0d0f1f34cbeb7b35978d94d8a2d68ac33493ce044`.

This report describes implementer tests, not an independent review of this newly written slice. Parent/another reviewer should independently inspect implementation before publishing. No push/merge/deploy performed. Not production browser identity, actual network IPC or evidence approval.
