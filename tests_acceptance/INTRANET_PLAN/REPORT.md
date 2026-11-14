# Intranet planning implementation verification — 2026-11-14

Base: 254167e3e957784fd9d2d136a275731f33314d9b. Independent branch;
no changes to main, PR56 branch, semantic_support, shared app config or routes.
No .agents/skills present in repository or /workspace/.agents.

Implemented strict offline metadata registry and case query-intent generator in the
existing Python service package. CLI accepts JSON, returns safe JSON; user-controlled
files can hold only validated non-secret metadata/reference identifiers. No application
DB persistence, live settings UI, endpoint resolver or API/MCP connector was added.
Four categories and both transport types preserved; missing case/vessel/time values
explicitly pending, configured references never imply connectivity. No actual intranet
endpoints/accounts available, no probing, data collection or model calls performed.

## Actual tests

- `cd service && .venv/bin/pytest -q -p no:cacheprovider tests/test_intranet_plan.py ../tests_acceptance/INTRANET_PLAN/test_independent.py`
  **67 passed, zero skips, 0.36s** (32 implementation +35 independent).
- Independent reviewer separately ran35/35; see INDEPENDENT.md.
- `tests/test_contracts.py`: 3 passed,1 failed. Failure: existing
  POST `/api/v1/cases/{}/timeline/registered-align-preview` absent from OpenAPI.
  Reproduced same3/1 on detached pristine baseline at /tmp/mcis-intranet-baseline,
  using the same service virtualenv. No contract-route regression introduced here.
- A broad service-suite exploratory run was interrupted (exit130 at ~4% after
  failures/skips); it did NOT complete and is NOT claimed green. No full-suite,
  browser, C#, CI, real intranet, actual model or deployment acceptance claim.

All new tests use synthetic fixtures. Socket/DNS failure traps verify the pure path;
CLI tests execute real local subprocesses only. Secret canaries are synthetic.
Future integration must authorize case access and explicitly map existing vessel IDs;
references need separately authorized runtime resolution and credential management.
No permissions rejected or bypassed; no merge/deployment.

## Try the unconfigured skeleton

From service:
`.venv/bin/python -m mcis_service.intranet_plan < ../samples/intranet-plan/unconfigured.json`

This returns four pending intents and explicit missing fields. It neither creates a
case nor saves/query-fetches anything. Output may be inspected or explicitly saved
as local metadata; never paste credential values into identifier fields.
