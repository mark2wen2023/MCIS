# Seed startup import isolation — static candidate only

Parent: 12fe626a057d5f91e7dde7490330308e82079028 on the archive research chain.
No application import/start, tests, requests, compileall or database execution in this change.
This does not authorize resuming archive tests or establish a clean runtime import trace.

## Changes

main.py imports now occur inside its existing seed_demo branch, in the original import order
haili5 -> lily_mary -> yangze22. The original single session and invocation order
lily_mary -> haili5 -> yangze22 remain. Import failures now occur later (after database setup),
so this is not a claim of identical failure timing or tested enabled-seed behavior.

reports/service.py uses common/demo_case_ids.py, which contains identifiers only, with no imports
or case body. HAILI identifier was obtained from existing test_reports_w16_direct.py,
test_reports_w16.py and test_colreg_w61.py declarations; YANGZE identifier was already present
in reports/service.py. The original seed source files were not opened to extract or compare IDs.
Cross-check with seed exports remains an independent-review prerequisite, not an executed test.

colreg/seed_annotations.py imports the real haili5 BAND_EVIDENCE only when seed_band_evidence
is called for the matching case. No empty replacement or mock module is used. Return still
constructs a new dict and copies every list. Existing fictional annotations remain unchanged.
The module-level BAND_EVIDENCE mapping no longer eagerly contains the real-case entry;
static service searches found only seed_band_evidence consumed by colreg/runs.py. External
consumers of module globals are not proven absent and need review.

## Static import paths checked

- __main__ -> main: direct seed imports now conditional.
- main -> reports.router / report_output.router -> reports.service: identifier-only dependency.
- main -> colreg.router -> runs -> seed_annotations: no top-level haili5 import.
- models_registry and relevant package initializers reviewed in the preceding static analysis.
- Search for imports of the three modules outside their source files finds only the conditional
  main imports and function-local annotation import. This is a bounded source review, not a
  complete proof against dynamic imports, dependency startup hooks or bytecode/cache behavior.

No role, route, permission, archive preflight or model/core configuration changes.
seed_demo=False still creates ORM tables/triggers and does not prohibit request-time data reads:
Seed run annotation can load haili5, and analysis.load_seed / report sources can read analysis
JSON when called. Existing fictional annotation literals also remain in seed_annotations.
The candidate does NOT guarantee zero case-related constants anywhere in the process.

## Validation and pending review

Only static diff/import-site inspection and git diff --check performed. No tests passed in this
round because none ran. Fresh-process import-event/bytecode monitoring, normal disabled-seed
startup, enabled-seed behavior and annotation copy independence remain unverified. Any dynamic
verification needs explicit review before execution; no module replacement or bypass is proposed.
Previous archive-test statements that no seed modules were loaded were inaccurate: top-level
imports loaded them even with seed_demo=False. This candidate does not retroactively fix those
runs. No seed body or case data included in this commit; only identifier constants and code/docs.
No merge/deployment.

## Explicit module-global API changes (static review follow-up)

1. HAILI5_BAND_EVIDENCE alias is no longer exported by seed_annotations.
2. BAND_EVIDENCE no longer eagerly contains the real-case key.
3. Overriding that mapping key no longer controls the real-case function result, which loads
   the actual seed mapping on demand. This is not externally compatible with the old globals.

Tracked-code symbol search (1104 files, excluded seed bodies) found only colreg/runs.py
importing seed_band_evidence; no known tool/test direct mapping consumers were found.
Dynamic references and external consumers remain unknown. Treating globals as internal is a
proposed API boundary, not an approved compatibility guarantee. No lazy mapping implemented.
