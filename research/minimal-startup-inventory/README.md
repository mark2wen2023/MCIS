# Minimal startup inventory — BLOCKED, not a runnable package

Base: 6d5069b9d320dcaddab28b95f8ed265bfc567b67 (source-policy candidate).
Not integrated into UI 3edb1a55. No application startup or source copy.
Target: existing health response plus existing case-list projection over one handmade
temporary case. No all-router mounting, reports, analysis, archive or models execution.

## Path-level inventory
- service/mcis_service/__init__.py: code-only version; sole hash-listed input, insufficient for startup.
- main.py:create_app: health nested after DB/schema creation; broad router imports.
  Needs extraction of existing health handler and separate minimal factory.
- cases/router.py:list_cases: desired actual read projection, but shares imports with
  create/update routes and unrelated models. Needs extraction preserving response/context.
- cases/service.py:list_cases: SQLAlchemy CaseRow read; shares vessel/track functions.
  Narrow dependency review required; no fake replacement.
- cases/models.py: exact CaseRow/model registration closure still needs review; not copied.
- db.py:Database.create_all dynamically imports models_registry and initializes all tables
  and triggers. Cannot use unchanged as minimal schema initializer.
- common/context.py: role/operator headers with Investigator default, not trusted production
  identity. No privileged header injection or permission changes proposed.
- config.py: seed_demo defaults True; environment selects DB/data/core paths.
  Needs explicit isolated instance settings with no fallbacks.
- common/contracts.py: PROJECT_ROOT schema glob is not a precise allowlist. Include only
  if required, with reviewed schema/reference closure.
- colreg/seed_annotations.py: known case annotation constants and delayed loader; exclude.
- analysis/router.py, reports/sources.py, reports/public_text.py: exclude entirely from
  this minimal target, even though separate policy candidate can disable reads.
- __main__.py imports broad main and uses Settings defaults; unsuitable minimal launcher.
- seed/, colreg/haili5_seed.py, analysis/data/, repository reports/, service/data/:
  excluded paths; no seed bodies opened and no business modules copied in this task.

Paths above are relative to service/mcis_service unless stated otherwise.
Required modules are NOT approved-copy entries. No complete transitive-closure claim.
Minimal launcher/factory, schema initialization and handler extraction are NOT implemented.

## Dependencies and gates
inventory.json lists preliminary dependency families with unknown versions/artifact hashes.
service/requirements.txt lower bounds are not an artifact lock. No installed dependencies
imported or scanned; stdlib/native/transitive closure remains unpinned.
Before execution: review complete source/contract/runtime sets and artifact provenance,
exclude original checkout/editable/.pth/startup hooks/bytecode/links, establish controlled
temporary directories with no concurrent writers, disable seed and source reads explicitly,
and define a single handmade-input preparation path. No general upload/import/model routes.
Then separately review startup observation and normal read; this document grants no execution.

## Checker and actual limited validation
check_inventory.py imports only stdlib; no MCIS/network/DB/process/copy operations.
Validates manifest before metadata enumeration; reads only an exact listed file set.
CLI ALWAYS exits 2; startup_allowed ALWAYS false, including exact/empty inventories.
No override. This is not a provenance, import-closure, native-I/O or TOCTOU guarantee;
lstat/read separation requires exclusively controlled directories. Do not run on real data
or a checkout. No actual source inventory was executed.

Reviewed and executed ONLY these three new ordinary synthetic nodes, all passed:
python -B -m unittest test_synthetic.SyntheticInventory.test_exact_self_made_files_still_not_runnable
python -B -m unittest test_synthetic.SyntheticInventory.test_incomplete_preparation_remains_blocked
python -B -m unittest test_synthetic.SyntheticInventory.test_empty_inventory_does_not_prove_service

Fixtures are self-created temporary text. No write-refusal, permission, symlink, tamper,
fault, recovery, application, model or paused tests. Checks prove only inventory report
semantics, not startup acceptance. No runnable package produced or published.
