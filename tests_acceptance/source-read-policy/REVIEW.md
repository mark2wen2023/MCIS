# Explicit instance source-read policy — static integration candidate

Base 2a6048f032b262318bd51c9a4e5b9da35b97e850. Not startup acceptance. Startup/archive pause remains; no merge/deployment. No actual case seed or report body was opened, application imported, server started, or requests performed.

## Configuration / behavior contract proposal

Settings adds allow_analysis_seed_reads and allow_public_report_reads, both False by default in all modes, independent of seed_demo population. Trusted application construction may explicitly set each boolean; this increment exposes no environment parser, HTTP parameter, header or route to enable them. create_app copies the booleans into a new immutable SourceReadPolicy in app.state, before DB initialization. It does not reference a mutable global policy or subsequently consult mutable Settings flags. This is configuration separation, not authentication or protection against arbitrary trusted server code changing app.state.

Analysis routes receive Request solely to read app.state policy; disabled/missing policy returns HTTP 503 analysis_seed_disabled before loader access, not an empty case list. load_seed retains positional path/sidecar but requires enabled source_policy keyword for reading; legacy direct calls now raise SourceDisabled. _read_seed is private implementation, not an authorization boundary against direct Python calls. Existing hash verification/fault behavior stays after the gate.

Report create/regenerate/COLREG draft share service.create_report -> build_sections and pass the instance policy. Disabled whatif skips the adapter and yields explicit policy-disabled missing text; enabled default adapter retains fault-as-unavailable text. Custom adapters retain the old (session, case) shape but whatif callbacks are now skipped when disabled, even if a custom adapter would not read repository data. This is intentional conservative compatibility change. Systemic adapters are unchanged; this is NOT a sandbox for arbitrary plugin code.

Public excerpts have a separate gate before importing public_text or invoking excerpts. Disabled adds an appendix missing sentence distinguishing policy from missing material/read failure. Existing excerpt-enabled empty/failure behavior is unchanged, not upgraded into a new reliable failure classification. Notes render only in included template sections; existing COLREG-only postfilter keeps only COLREG citations and thus removes unrelated missing-source notes, but no disabled source callback executes. No stored reports are migrated. Existing report GET/review/export code is unchanged; runtime regression is not established.

Both old demo setups and non-demo setups now default to no repository-source reads; old callers deliberately depending on these sources require explicit trusted configuration and future approval to execute. seed_demo=True still populates seed DB data via existing main behavior, independent of these read flags; this change does not make demo startup safe. No permission checks removed/changed.

## Static paths / remaining scope

main builds policy; analysis router -> load_seed -> read_analysis -> _read_seed. reports service -> build_sections -> guarded whatif/default load_seed and separately guarded public_text import/excerpts. Report route check_access remains before create. Actual MCIS API/type/schema/template response integration was not run. The module-level analysis data cache and SOURCE_ADAPTERS registry remain existing shared state; policy itself is not shared, but this does not prove total multi-app isolation or protect against concurrent plugin mutation. No changes to COLREG explicit Seed annotation loading, other repository reads or arbitrary direct service calls. Full startup/dependency closure, legacy clients, enabled sources and non-default templates require independent review.

## Development checks, limited

Only executed after static inspection:

- python -I -S -B tests_acceptance/source-read-policy/test_synthetic.py
- python -I -S -B tests_acceptance/source-read-policy/check_static.py

Both PASS. Synthetic script loads only the import-free source_policy.py by exact path via stdlib runpy; callbacks, data and failures are wholly invented. It checks the four policy combinations, zero disabled callbacks, independent policy instances, failure distinction and legacy adapter argument shape. This is not a permission/refusal endpoint test or actual filesystem failure injection. Static script parses only listed code files with AST and checks defaults and selected wiring/order; no app/module execution. No actual seed replacement in MCIS. No backend, application, seed, report generation, DB, browser, model, HFACS, paused or write-probe tests ran. Do not claim real HTTP, complete startup, runtime report output or production identity acceptance.

## Settings positional compatibility correction

2b20981 incorrectly inserted policy fields before core_cmd, shifting the prior seven positional arguments. A new isolated construction test reproduced the mismatch before correction. The policy fields now follow data_dir/db_url/seed_demo/core_cmd/core_timeout_s/host/port, preserving all existing positional prefixes. Callers should use named arguments for new policies. The config docstring no longer says all configuration comes from environment variables: the new two policies have no environment parser and require explicit construction configuration.

**seed_demo remains True by default** when MCIS_SEED_DEMO is unset. False read-policy defaults do NOT establish default zero seed reads, safe startup or disabled population. Existing startup/archive hold remains.

Reviewed and executed only test_settings_constructor.py and check_static.py with `python -I -S -B`. The new test reads config source, compiles ONLY its Settings class AST with stdlib dataclass and fabricated environment/root objects; no config module imports, real environment access, app, seed, filesystem data access or database operations. Before fix: positional assertion failed. After fix: full old seven arguments, every positional prefix, named new policies and default/explicit seed selection passed; AST wiring check passed. This is not actual application configuration/startup or HTTP validation. No other tests rerun.

Compatibility changes from the initial candidate remain: direct load_seed callers need enabled source_policy; analysis route functions now require Request for direct Python invocation (HTTP paths unchanged); disabled whatif custom adapters are not called, though their two-argument shape is retained when enabled. Existing report reading is unchanged in code, not newly runtime-verified. New correction awaits independent review; no merge/deployment.
