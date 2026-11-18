# Synthetic evidence normal multi-generation archive

Base: 5c9bd9db19238d1c4b40134c39bc2eb2215c538c, research/restore-normal-case-registration.
Only one new normal test and this report. No production behavior or permission changes.
Developer verification only, pending independent review.

## Static execution review

- tests/test_archive_artifact_destinations_normal.py supplies initial_package/store/intake/export;
  conftest.make_settings overrides data_dir and db_url to tmp_path, seed=False. No default app/client
  fixture is requested. H uses the existing LeadInvestigator fixture, not production authentication.
- main.create_app creates directories, ORM tables and existing triggers, including HFACS tables;
  seed_demo=False bypasses seed functions. No external listener or model task is started.
- package_intake/router.py commit -> authorize/read_body -> commit_sync -> parse_package ->
  import_case runs existing policies and normal integrity validation. It creates a staging directory,
  writes imported files plus source.mcase, creates IntakeReceipt and import audit, flushes/renames
  the case directory then commits. Temporary staging cleanup is existing behavior. Failure handling,
  partial publication and unknown commit safety are not tested or endorsed here.
- package/mcase.py import_case restores EvidenceRow and CustodyEventRow; only the explicit synthetic
  raw text and archive artifacts are written. Working-record restore writes historical artifacts and
  history rows; absent timeline member yields no timeline-origin entries. No active evidence-intake
  receipt is manufactured: the fixture uses a plain Register event with empty detail.
- export route keeps its existing role check and transaction. working_records_archive.build runs
  full_access and closed-world preflight unchanged, reads only the temporary case files, records the
  original package as historical artifact, validates the output and appends package.export audit.
- hfacs_drafts/archive.py build returns None for absent current/events/receipts before core validation;
  parser calls HFACS validation only for its member, which is absent in this fixture and every export.
  No HFACS core or model is called. Track/timeline history are absent. No paused or adjacent test selected.

## Coverage and execution

The fixture builds UTF-8 synthetic text, one EV-900001 registration and one Register chain line,
using the existing initial 1.0 package builder. Three fresh stores import/export sequentially;
exports use the existing supported 1.2 format. Each store checks settings, exact registration doc,
Register row/line, file bytes and SHA256. Each exported ZIP checks registration, original bytes,
digest, custody JSONL exact bytes and absent HFACS namespace. Intake helper also checks retained
source.mcase bytes. No deletion, tampering, fault injection, permission-denial or refusal probe.

Executed from service with existing dependencies:
```
/workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q tests/test_archive_evidence_generations_normal.py::test_synthetic_evidence_bytes_registration_and_custody_across_three_stores
```
Preparation initially used a wrong relative file path; that invocation collected no tests.
The first actual run failed 422 CONTRACT_VIOLATION because EV-SYNTHETIC-GENERATIONS did not match
existing ^EV-[0-9]{3,}$ schema. Only the fixture ID was corrected to EV-900001; schema/policies stayed
unchanged. Rerun: **1 passed in 1.23s**. This was not an intentional rejection test.

All generated ZIPs/text files/databases remain under pytest temporary directories, not committed.
No real case/seed content was read, no credentials, new dependency installation, browser or live HTTP.
TestClient invokes real normal route code in process. This does not cover evidence upload API,
post-restore evidence edits, full lineage assertions, complex archives, crashes, concurrent writers,
unknown commits, trusted production identity or main/PR104 acceptance. No merge/deployment.
