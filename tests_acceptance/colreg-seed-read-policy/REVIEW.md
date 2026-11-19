# COLREG request-time seed annotation gate — candidate, startup still paused

Base: 6d5069b9d320dcaddab28b95f8ed265bfc567b67 (source-read policy).
This branch does not include the separate health-only factory/install records.

Static chain: COLREG current/list/detail/activate/compare/evaluate/review/history
routes -> `_runs_session` -> `runs.ensure` (directly or through get_run,
list_runs, activate, add_engine_run) -> first existing current with all Seed
checks -> annotation loader. Previously this branch called seed_band_evidence
regardless of whether the application was non-demo.

The trusted application constructor now captures `settings.seed_demo is True`
once, before initialization, in an instance-local boolean. `_runs_session` puts
that boolean in the new session's info dictionary. `ensure` requires literal
True before calling a lazy wrapper which imports seed_annotations and calls the
existing helper. No request/header/body opt-in, global flag, new Settings field,
role change, gateway change, archive change or HFACS change. Existing default
seed_demo=True is unchanged: this is NOT default zero seed access.

With seed_demo=False (or a missing application/session flag), first Seed-current
adoption preserves the stored analysis and uses the existing empty band evidence
representation. The existing version note explicitly says repository annotations
were not added by policy and does not assert verification. Stored versions and
annotations are not migrated/removed; a later enabled instance does not backfill
an already adopted version. Initial/RuleEngine/empty/external-current flows keep
their previous behavior. This gate is separate from the analysis/public-report
flags: enabling those does not enable COLREG annotations in a non-demo instance.

Compatibility: ordinary direct Python callers still have the same signatures,
but a direct `ensure` chain using a session without the explicit info flag no
longer auto-adds repository Seed annotations. Trusted internal callers wanting
legacy demo annotations must arrange the flag deliberately; arbitrary trusted
Python can mutate app.state or session.info, so this is not an authorization or
sandbox boundary. No actual enabled seed contents or mapping semantics tested.

Only command executed after reviewing its fixed source inputs:

    python3 -I -S -B tests_acceptance/colreg-seed-read-policy/check.py

Four development output groups passed: synthetic enabled/disabled/missing-policy
adoption and stable existing version; ordinary/empty/external-current; actual
extracted session contextmanager with fabricated instances; static lazy-import,
constructor snapshot and route wiring checks. AST extraction executes only the
listed non-seed functions. Storage, version creation, sessions and loader are
handmade in-memory callbacks. No main/router/ORM/application import; no HTTP,
real DB, model, seed content, core, permission/refusal probe, fault injection or
paused test. This does not prove actual _create persistence, response/schema
integration, concurrent applications or full import closure.

All role/require/case checks and route signatures are unchanged in the diff.
No defaults or contracts were expanded. Startup, archive and production holds
remain. Await independent review; not merged or deployed.
