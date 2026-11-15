# Supported archive workflow versus complex-seed refusal

Base: fresh main 94d5e38c926fda232bb987b60fa9145e4bcf01a7.
This independent candidate adds one test file only, plus documentation/progress.
It does not include baec448's partial reader corrections, alter any old test,
change production policy/serializers/allowlists, or remove existing case records.

## Three ordinary tests

1. Create a separate explicitly synthetic, unseeded case with complete legacy
   archive fields. As Investigator, edit case summary with a declared synthetic
   source label and add a vessel with estimated length/source. As LeadInvestigator,
   export into fresh storage B, restore and compare full metadata/revision and
   vessel/source fields; export again, compare all members except manifest/audit
   (expected new export/import history), preserve original audit-line prefix and
   check import/export events. Restore second archive into fresh storage C and
   check metadata/vessel equality and audit chain again. No private evidence,
   actual ship observations, model or OCR results used.
2–3. Keep the ENTIRE existing Lily/Mary synthetic demo. Make an ordinary case-text
   edit or vessel addition, then assert Investigator403 and LeadInvestigator409
   ARCHIVE_RESTORE_UNSUPPORTED. Response is JSON, not a ZIP/download; compare all
   temporary database rows and blob content hashes before/after both denials,
   including audit rows. No successful-export audit or partial archive response.
   This does not claim no transient in-memory assembly or crash guarantees.

## Test evolution / important limitation

First targeted run: 1 failed, 2 passed. The initial fixture omitted optional case
fields. Existing case_json fills defaults (e.g. accidentCode/grade, agency, location
height and sea level); import therefore produces a different case/revision from
that sparse original. No product change was made. The successful fixture now
explicitly supplies the supported legacy fields and numeric representation before
creation. This scopes the test to supported exact roundtrip, NOT a fix or acceptance
of omission-preserving roundtrip. The sparse-case normalization issue remains.

Second targeted run: 3 passed in 1.47s. Command from service:
```
.venv/bin/pytest -q tests/test_archive_supported_boundary.py
```

Original190 + new3 command:
```
.venv/bin/pytest -q tests/test_archive_supported_boundary.py tests/test_contracts.py tests/test_case_metadata_w84.py tests/test_environment_w92.py tests/test_track_history.py tests/test_vessel_entry_w91.py
```
See final result below. Original tests are unchanged and remain separate; these
three passing tests do not replace or repair their known failures. Full complex
case serialization/recovery, ECFC, HFACS core, real identity, browser, crash and
concurrency security acceptance are NOT covered. No restricted security or ECFC
operation was attempted. Header roles are test fixtures, not production SSO.

Final combined result: 190 passed, 3 failed, 0 skipped (193 total, 60.45s).
Original190 remain 187 passed/3 failed:
- test_case_metadata_w84.py::test_read_update_audit_original_and_roundtrip
  (original Investigator audit parsing TypeError)
- test_vessel_entry_w91.py::test_create_reopen_export_and_audit
  (original Investigator audit parsing KeyError)
- test_track_history.py::test_real_hfacs_and_report_optional_extension_three_generations
  (HFACS_CORE_UNAVAILABLE; no configured SDK/DLL)
No source changes to those tests, new skips, mocks of HFACS or permission changes.
These are developer self-tests; independent acceptance is pending.
