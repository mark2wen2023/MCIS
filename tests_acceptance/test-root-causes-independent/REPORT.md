# W9.2 fixture policy alignment — independent acceptance

Target `/workspace/mcis-test-root-causes`, branch `fix/test-fixture-policy-alignment`; HEAD/pinned parent `f2eff95` (merge PR72 route-classification baseline). Read AGENTS/handoff. Scope is one test module, no product permissions changed. No reviewer implementation edits, push, merge or deployment.

## Actual evidence

* Candidate: `PYTHONPATH=service service/.venv/bin/python -m pytest -q service/tests/test_environment_w92.py` → **70 passed in 15.71 seconds** (`results.txt`).
* Parent module from `git show f2eff95:service/tests/test_environment_w92.py`, run against unchanged parent product implementation with the same venv → **12 failed, 57 passed, one dependency warning in 26.31 seconds** (`parent-results.txt`). This is a relocated parent-module run, not a separate complete worktree/full-suite run. Harness only replaces `.conftest` import with `tests.conftest` and registers that existing fixture plugin; original test bodies are unchanged.
* `sha256sum -c logs/test-root-causes-impl-hashes-frozen.txt` → **OK**, stored in `hash-check.txt`. Frozen module hash `fd1876c4f68c37f45655df6d5e590999f9caa761a5a03c66b875405c17b02f2e`.
* `git diff --exit-code f2eff95 -- service/mcis_service contracts web tools` → empty/success. Product, permissions, contracts and client tools unchanged.

Parent snapshot was executed as `tests_acceptance/test-root-causes-independent/test_parent_snapshot.py` with `--import-mode=importlib`; after execution it was renamed **parent_snapshot.py.source** so ordinary future pytest discovery does not introduce 69 duplicate historical tests. To reproduce, copy the retained source to a temporary explicitly selected `.py` module and run it with `PYTHONPATH=service`, then remove that temporary module. Original logs preserve the executed node names.

## Root cause and coverage assessment

Parent default fixture seeds unrelated demo evidence/recommendation/consultation content. Export returns **403 FORBIDDEN JSON**, with message “完整安全建议或征求意见内容不可访问”. Old tests feed response.content straight into ZIP parsing without checking HTTP status; all 12 failures arise through this path. They therefore do not establish environment-observation serialization failures. This is fixture/permission coupling, not justification to weaken export permissions or skip tests.

Candidate defines module-local unseeded app/client fixtures, creates an explicitly synthetic environment-only case through the real API, and uses the unchanged default test identity. It does not grant broader role permissions or monkeypatch authorization. `export_package` now requires **HTTP 200 before ZIP parsing**, improving failure localization.

AST comparison (`ast-comparison.json`) confirms **no removed function**. Added functions: app/client fixtures, export helper and seeded denial regression. Only existing `package` helper and `test_empty_create_unknown_roundtrip` change, replacing unchecked export content reads with the status-checked helper. Parameterizations and original permission, no-write, invalid-body, finite-number, duplicate/concurrency, audit rollback, case isolation/restart, malformed/unlisted package, missing legacy extension, case-insensitive extension and long-case-ID assertions remain intact.

The new seeded regression independently runs a seed=True app and still requires **403 FORBIDDEN JSON** for Investigator full export. Therefore unrelated restricted demo content stays denied rather than silently becoming exportable. Synthetic environment-only export/import succeeds, letting malformed-package cases reach their intended environment validation assertions.

## Disposition / limits

**Accept this narrow test-fixture correction.** It removes an independently reproduced test setup mismatch while retaining the original access denial as explicit regression coverage. No product authorization change and no discarded failing test/parameter.

This does not resolve the remaining full-suite failures/errors or environment issues. Previous 180 failed/104 errors belong to a different complete-suite baseline investigation; this 70-case module run cannot be presented as the whole suite passing. No .NET test/build, browser test or full service suite was independently run in this acceptance. Synthetic fixture identities remain development role headers, not production authentication.
