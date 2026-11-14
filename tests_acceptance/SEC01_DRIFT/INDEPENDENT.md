# SEC01 offline drift gate: independent review

## Verified result

Added 11 independent tests in `repo/service/tests/test_route_drift_independent.py`. Final local combined run: **48 passed**, 1.91 seconds, exit 0 (existing 37 plus independent 11). Command from repo/service:

```
../../../line-dataset-1615/repo/service/.venv/bin/python -m pytest -q tests/test_route_drift.py tests/test_route_drift_independent.py tests/test_route_classification*.py
```

No blocking defect found within the documented offline observed-surface drift scope. No implementation edits, deployment, push, secret use or live identity/model calls.

Independent coverage: same-name compiled dependency callable replacement, external override provider, Python minor mismatch, route ordering, nonfinite middleware option refusal, WebSocket callable replacement and override provider refusal, selected-source missing/changed detection, relocation stability, and explicitly unverified globals/defaults. Tests confirm success flags never claim authentication, authorization or revocation correctness.

Two initial test fixtures created functions via exec without a module name. They caused TypeError in endpoint_name (fail closed, not a false pass). The fixtures were corrected with an explicit __name__ to represent normal module-defined functions; production implementation was not modified. Unsupported nameless dynamic functions still need review/clearer diagnostic if support is desired.

## Reliability / compatibility

- Python major/minor is captured and mismatch fails. No cross-version matrix or Python patch-version portability was run. Bytecode/co_consts/exception-table shape depends on interpreter/compiler; version upgrades require an intentional baseline review, not automatic regeneration.
- Filename and first-line relocation do not change callable shape, verified independently. However selected source files are byte-hashed: comments, formatting and newline changes intentionally trigger review even if behavior is unchanged.
- CI uses Python 3.12 but requirements contain lower bounds rather than a reproducible full dependency lock. External framework docs handlers are included in runtime shape, so a new FastAPI/Starlette version may change the result without an MCIS source change. Prefer a reviewed pinned gate environment and explicit dependency-upgrade baseline review before treating failures as source regressions.
- Route order changes are observed and can require review even without a route-set change; order can affect shadowing, so this conservatism is appropriate.
- The 36 selected source files are not a complete repository or transitive dependency integrity manifest. External middleware implementations and helper modules remain outside the verified source subset.

## False-green boundaries retained

Independent test proves mutable globals and function default values can change behavior without changing callable_shape. Closures are also expressly unverified. Compiled ASGI wrappers, runtime mutations after snapshot, helper modules, external middleware behavior, real IdP/session state, resource permissions and external revocation cannot be certified by this gate. Dependency overrides present at inspection are rejected, but later overrides/mutations remain outside this offline snapshot. A matching hash does not establish that the baseline implementation is safe.

This is a review-triggering build-time gate, not runtime identity/authorization enforcement. Existing undeployed prototypes and main authentication gaps remain unchanged. Passing does not permit public exposure, prove source classification, or solve final-check/revocation races.

## Workflow inspection

Workflow includes both classification and drift test globs with contents:read and no deployment or secret steps. It was inspected locally only. No GitHub CI run or required-check activation was observed or performed. Local success must not be reported as remote CI success.

Reviewed implementation SHA256: `40887059c83727537e5bb7f59b01d27dba462e6d53bb4e778d60d8102d76da5b`.
Reviewed baseline SHA256: `d57ab97d504adf9691822b776c6c39fdd3052e1a782adfe53bac2ba98bc17b1c`.
