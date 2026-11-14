# Strict historical result validation: local results

- New schema/semantic/import tests:35 cases (two import entry points with no DB/blob writes on rejection; exact declaration roundtrip without local index; malformed/unknown/duplicate/oversized/deep/nonfinite/foreign/mismatched claims).
- Final selected run: `service/.venv/bin/pytest -q service/tests/test_unreviewed_history_schema.py service/tests/test_unreviewed_history_boundary*.py service/tests/test_source_incarnation.py service/tests/test_case_incarnation*.py service/tests/test_package.py service/tests/test_archive_generation_boundary.py` →92 passed, zero skipped,35.20s.
- Existing malformed-marker read protection remains tested. Only synthetic roundtrip fixtures changed to canonical self-reported historical declarations because no product save feature has emitted this reserved format.
- Independent initial findings fixed before publication: inner result/conflict case and optional epoch mismatch; JSONschema accepting mathematically integral floats where strict integer fields are required. Also rejects import diagnostics with Error and reused source registration sequence.
- No result index/save operation, live LLM, actual-core run in this schema suite, browser, CI, merge or deployment. A valid history schema does not authenticate historical execution, identity, source truth or approval.
- Frozen hashes and independent acceptance report are alongside this log.

Independent final rerun:47 passed (35 implementation +12 independent), zero skips,9.36s; final frozen hashes verified before and after tests.
