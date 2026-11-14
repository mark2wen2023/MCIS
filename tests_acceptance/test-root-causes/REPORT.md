# Full-suite failure investigation / first bounded repair

## Exact bases and scope

Local branch `fix/test-fixture-policy-alignment`, direct starting commit and fetched origin/main `f2eff95dfb1bbf6afd92036ec589a1513f0b8840`. Its first parent is `3aba2bf03e393909c611489ae573a887087637ac`. The merge adds only route inventory/CI/contracts/documentation/tests (11 files); it does not modify the existing business routes. No production source, global fixture, authentication, permission or archive-format change is part of this repair. No push, merge or deployment.

The reported 180 failures / 104 errors are from the earlier metadata-idempotency investigation, not a fresh full run on f2eff95. Full parent fe3fb05515898cbde380af9bf819afcb344a28eb: 180 failed, 1563 passed, 11 skipped, 104 errors (522.01s). Candidate ead5acfdd87bc1a425c6d9f9abc930bfb3198139 plus independent tests: 180 failed, 1585 passed, 11 skipped, 104 errors (524.45s). All 284 failing/error nodes and classifications match, zero added nodes; machine comparison copied as prior-comparison.json. The source logs/report are in that candidate under tests_acceptance/server-idempotency-independent/baseline and tests_acceptance/server-idempotency/full-review-tests.txt. This shows inherited failures in that comparison, not universal absence of regressions or a passing latest-main suite.

## Common causes and evidence

* Fixture/policy mismatch: on actual f2eff95 the environment archive module gives 12 failed / 57 passed (26.12s). Export returns 403 FORBIDDEN for full restricted safety-recommendation/consultation content in the seeded demonstration; tests blindly feed JSON error bytes into read_zip. Environment observations themselves are not the forbidden content. This is an outdated cross-module fixture assumption exposed by stricter export policy, not evidence that ZIP decoding is broken.
* Independent current-main agents setup probe returns 403 at interview creation using default Investigator. The full historical suite has 31 setup errors in this module. Its full-content authorization assumptions need separate review; simply granting all permissions would conceal the safety gate.
* Two current-main HFACS taxonomy setup probes fail with 503 HFACS_CORE_UNAVAILABLE. These modules account for historical 50 + 23 setup errors. No dotnet executable is on PATH here; the historical log also explicitly records missing tools/mcis-core/out/mcis-core.dll. Core readiness is an environmental prerequisite, not something this patch masks with skips or mocks. These representative probes do not establish every downstream test would pass with a built core.
* Remaining failure concentrations: reports_w16_direct 47, reports_w16 41, consultation_input_w73 15, interview_compare_w5 11, reports_w161_snapshot 11, bowtie_preview 9, human_factors_preview 6. These include policy assertions, CLI prerequisites and response-shape exceptions. They have NOT all been independently root-caused; existing code/contract defects may remain. Neither all180 failures nor all104 errors should be labeled environmental. No causal claim is made about when older behavior first regressed without a bisect.

## Minimal repair and verification

Module-local seed=False app/client create a schema-valid explicitly fictional environment-only case through the real HTTP route. Global fixtures remain unchanged. Both archive producers assert HTTP200 before parsing ZIP. All existing malformed-package, permissions, rollback, concurrent duplicate and roundtrip tests remain. A new separate seeded-app regression asserts Investigator export403 and JSON content, so denial is retained rather than bypassed.

Commands from repository root with existing service/.venv:

```sh
PYTHONPATH=service service/.venv/bin/python -m pytest -q service/tests/test_environment_w92.py
PYTHONPATH=service service/.venv/bin/python -m pytest -q service/tests/test_route_classification.py service/tests/test_route_classification_independent.py service/tests/test_archive_export_safety.py service/tests/test_package_zip_boundary.py
```

Actual after: 70 passed /16.94s (69 original +1 denial regression). Adjacent: 74 passed /5.24s. Three diagnostic setup probes: 3 errors /2.43s, intentionally retained as evidence, not counted as passes. Logs live alongside this report. Independent review is recorded separately; no claim of the entire latest-main suite passing. No browser, SSO, real identity, model, production performance or deployment validation. Existing role-header trust, long locks, memory limits and unrelated baseline defects remain out of scope.

Stored console logs normalize trailing whitespace only; assertion text and result counts are unchanged. Python 3.12.14, existing service virtual environment.
