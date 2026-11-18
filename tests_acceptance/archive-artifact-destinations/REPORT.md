# Synthetic normal artifact destinations

Developer-only test, 2026-11-18. Parent `553da2a59bbfa71b29c32f6d4fcbabcc7d64dc80`, research/restore-normal-case-registration. No product changes or additional restoration support.

Existing test_working_record_archive.py::test_three_store_roundtrip_and_inactive_receipts checks retained ZIP contents but mixes normal flow and historical-operation refusal checks. It was read, NOT executed. This new standalone normal node directly checks restored artifact files, database artifact size/digest, import-history association and lineage across two restores of 1.2 packages generated after a synthetic 1.0 intake. It uses three fresh tmp_path databases/directories, seed_demo=False, in-process FastAPI TestClient and the existing self-reported LeadInvestigator fixture. It is not authenticated production identity or browser acceptance.

Static review of the new node: only normal commit/export requests, synthetic bytes generated in memory, no denial assertions, file mutations, fault injection, paused nodes or write-refusal probes. No HFACS members/records are supplied; hfacs_drafts/archive.py build returns None for empty current/events/receipts before validation/core invocation. No mock core or model execution.

Exact command from service/ (existing dependencies, no installation):
```
/workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q tests/test_archive_artifact_destinations_normal.py::test_historical_artifact_files_rows_and_lineage_survive_two_restores
```
First execution: 1 failed because the newly constructed case omitted required legacy base fields, producing PACKAGE_INTAKE_INVALID/422. This was an unintended fixture error, not a refusal probe or product defect. Added the required empty string/numeric base fields, retaining fictional marking; second execution: **1 passed in 0.81s**. No other test nodes were run. Preliminary sed/rg reads in the first command used an incorrect service/ prefix from service cwd and failed; corrected reads then confirmed the empty-HFACS early return and no autouse fixtures in conftest.

Assertions cover exact retained source.mcase bytes, outer version 1.2, absence of HFACS member, exact restored artifact set and bytes, size/hash, package-intake index and parent relation, and original artifact bytes in the final re-export. They do not cover 1.1/1.3, complex case state, concurrent writers, crashes, uncertain commit, universal readiness gates, original authenticity, media restoration or production directories. All generated ZIPs/files/SQLite data stay in pytest temporary storage and are not committed. Existing unsupported-state protections remain unchanged. No merge/deployment; independent review pending.

## Third-generation extension (2026-11-18)

Parent `7e6fbea78946d5c961a57bc5e83d002930642e30`. Prior single-node independent pass was reported by the coordinator; the extension below is developer-tested only. Reviewed working_records_archive/service.py current-receipt-to-artifact assembly: it retains existing nodes and uses current graph tips as parents. Reviewed hfacs_drafts/archive.py empty-record early return again; this fixture introduces no HFACS state.

The same exact node/command above now checks all three artifact descriptors, exact ZIP artifact member set and original bytes, all three import-history bindings, and complete lineage `sha0:[]`, `sha1:[sha0]`, `sha2:[sha1]`. A fourth fresh temporary store imports the final 1.2 package and verifies all three restored files, sizes/digests, DB rows and lineage. Node name is retained for continuity, but coverage now includes a third 1.2 restore after the initial 1.0 intake. Only this node ran: **1 passed in 1.04s**. No denied requests, fault injection, HFACS core, paused nodes or write-refusal probes. No production behavior changed; this does not validate complex-case restoration, crashes, simultaneous writers or production identity. Previous test count is not added to this rerun.
