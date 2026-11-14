# SEC01 independent route-manifest review

## Result

Added `repo/service/tests/test_route_classification_independent.py` with 10 independent tests. **24/24 local tests passed (14 primary + 10 independent), 0.13 seconds**, exit 0. No blocking defect found within the stated structural build-time inventory scope.

Run from `repo/service`:
```
../../../line-dataset-1615/repo/service/.venv/bin/python -m pytest -q tests/test_route_classification.py tests/test_route_classification_independent.py
```

Independent cases verify multiple nested router prefixes, mounted application hidden HTTP plus WebSocket routes, newly added children beneath an existing mount, omitted mounted child classification, duplicate manifest entries, actual removal of the get_ctx dependency, inherited include dependencies failing for review, unsupported route kinds, cyclic trees, and empty-manifest mismatch. An additional test explicitly demonstrates that dependency overrides are not authenticated or certified by structural inventory: result still reports authenticationVerified=false/enforcementPerformed=false.

Baseline current-app primary test verified 161 method entries and 149 declared-context entries locally. Parent supplied the main `3aba2bf` snapshot identity; this report does not assert a remote git state or deployment.

## Claim boundaries

- Route presence, exact endpoint module/qualified name and a get_ctx dependency flag are topology checks, not authentication or authorization.
- Handler code changes retaining the same name, middleware changes, dependency overrides and mount internals are not proven safe. Opaque mounts are recorded as a boundary, not recursively certified if no route list is available.
- Scope/operation/rationale are explicit human classifications, not automatically proven business semantics. Changing both manifest and unsafe routes can make a structural test pass; review and real positive/negative authorization tests remain necessary.
- Duplicate protocol/path/method detects exact overlap, not all equivalent regular-expression routes or priority/shadowing semantics.
- Existing dev header-based get_ctx remains unauthenticated. A passing inventory does not repair it or authorize public exposure.
- No product runtime/default startup code changed in this review. No deployment, push, model call or live authentication test was performed.

## CI review

Read `.github/workflows/route-classification.yml`: it declares read-only contents permission, Python 3.12, service dependency installation and `tests/test_route_classification*.py`, with no secrets/listener/deploy steps. This is workflow configuration inspection only. GitHub CI has NOT been observed running, and this reviewer has not enabled a required branch-protection check. Those must not be reported as completed.

## Reviewed hashes

- routes.py: `84f980f93302325b540a708a0f8808e0154d0210020058a8eaf4f5998b0d8148`
- manifest: `bec55a530462cd14509d11dcf7903e09c81f05656b099f8f59abf8288a54a3cf`
