# Offline inactive receipt history v2: developer results

Base4e5863ae4d68bdded6bad683a90c567a74d0a512. New research parser derives from
exact a812d38 working_records_archive/conflicts.py; imports local validation utilities
and existing schema registry, selecting unchanged frozen v1 schema or standalone v2.
No production module, runtime schema or archive allowlist changed. No database writes
inside parser and no active authorization function or restore entry point added.

Command from service/:

    PYTHONPATH=.. .venv/bin/pytest -q tests/test_conflict_archive_receipts_v2.py tests/test_conflict_restore_current_compatibility.py

Final22 passed in4.20s (21new +1existing compatibility diagnostic). Earlier19-test run
passed before adding legacy-unknown and complete issuance coverage. Synthetic evidence
registry uses ordinary SHA-only registration (no original file) and actual existing
conflict/receipt/save routes, then supplies captured rows/raw audit/custody to parser.
Unchanged v1 creation-history input and v2 consumed+unused receipts both accepted;
JSON reserialization returns exact original values and history digests. Constructed
pre-capture legacy records stay unknown with empty history. The earlier old-schema
rejection remains true. This is member compatibility, not full old ZIP roundtrip.

Negative synthetic cases: missing/extra/duplicate receipt, active label, wrong
case/conflict/revision/edit-version/observations/source/custody/registry/actor/expiry,
missing verification flag, orphan consumed receipt, unknown version, omission of
unused issued receipt, and attempted v2->v1 downgrade. No production mutation or
formerly restricted security/ECFC operation executed. Candidate inputs are disposable
synthetic copies; original stored histories are not stripped or rehashed.

Known limits: validation proves consistency of supplied declarations, not trustworthy
identity/history provenance. Unused proposal content unavailable, only original digest
retained. No original verification or current permissions established by offline parse.
Existing v1 unresolved-source variants remain refused. No outer-envelope v2, product
file-layout recovery, archived receipt DB mapping, imported-prefix map, active receipt
replay prevention in an importer (there is no importer), crash/unknown commit tests,
product roundtrip, browser or independent acceptance. Product rejection remains.
