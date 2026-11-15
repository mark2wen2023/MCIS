# Legacy archive normalization and metadata revision

Candidate parent a14321d2d3aa17c5a5c23225c8e9ee68e11072bf, itself based on
main 94d5e38. No production code/policy/archive whitelist or old tests changed.

## Contract decision

contracts/W8.4-case-metadata.md lines30–31 explicitly specify missing optional
leadInvestigator/agencyName/summaryNotes become empty strings through legacy
case.json; placeName presence is preserved in case.ext.json. Revision hashes the
current case representation and last metadata-edit audit line, and is explicitly
NOT guaranteed to survive cross-store package normalization. A fresh token must
be read. Therefore the previously reported sparse-field revision difference is
expected compatibility behavior for this contract, not evidence of lost edits or
a reason to stabilize revision by omitting fields from its hash.

package/mcase.py:case_json also emits accidentCode/accidentGrade, seaLevelOffsetM,
and incidentLocation.heightM defaults. This test describes that existing old-format
representation; it does not authenticate those defaults as observed real facts.
Do not generalize the result to arbitrary numeric/time normalization or all unknown
fields, or to the complex seeded case. No wider serialization fix is justified here.

## New ordinary tests (two explicitly synthetic modes)

- Omitted: create a sparse case, then save nonempty summaryNotes/placeName with
  sourceLabel/reason and a named synthetic investigator.
- Cleared: start with synthetic agency/investigator values, clear them via null,
  and preserve nonempty summary/source information in the same edit.

In both modes, assert the original live case and revision do not change on export.
After import, assert exact expected case representation, equal lastChange, and a
different revision. Representative before/after:

| Field | Before export | Restored |
| --- | --- | --- |
| leadInvestigator, agencyName | absent | empty strings |
| accidentCode, accidentGrade | absent | empty strings |
| seaLevelOffsetM, location.heightM | absent | 0.0 (legacy serialization default) |
| summaryNotes | nonempty synthetic text | identical |
| placeName | synthetic place | identical |
| last metadata-edit history | recorded original values/source/reason | original lines retained |
| revision | token for sparse representation | token for normalized representation |

The entire original audit-line prefix is byte-preserved. The clear case also checks
original present=True value and after present=False/null remain in edit history;
restored empty fields do not rewrite past audit truth. Old token PATCH returns409
CASE_METADATA_CONFLICT and leaves all temporary rows/blob content unchanged. The
same proposed edit with freshly read token succeeds and creates a new revision;
audit chain remains valid. Tokens are opaque: no hardcoded hash or equivalence hack.

## Validation and limits

From service:
```
.venv/bin/pytest -q tests/test_archive_supported_boundary.py
```
5 passed in2.43s: previous3 plus new2. Ordinary real HTTP app execution with synthetic
fixtures; no model, browser, real identity or restricted security/ECFC test.
Additional W8.4 regression result recorded below. Original190 not rerun as a whole;
its preceding result was187 passed/3 failed, not superseded by this targeted run.
No production change or claim of expanded archive support. Sparse omission is not
preserved by legacy format; the tested contract explicitly requires clients to
re-read the normalized version. Independent acceptance remains pending.

Additional command:
```
.venv/bin/pytest -q tests/test_archive_supported_boundary.py tests/test_case_metadata_w84.py
```
48 passed,1 failed in18.38s. Failure remains original
`test_case_metadata_w84.py::test_read_update_audit_original_and_roundtrip`, which
parses Investigator's denied full audit as a list. No old assertion or fixture was
changed to hide it. HFACS was not run in this targeted group; its missing dependency
is still open, not a pass or a new skip.
