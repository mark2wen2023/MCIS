# Behavior-preserving isolated audio assembly consolidation

Exact parent: de207b3544abc1fc097b098eff3085d647ca7b3e. Work continues on candidate/audio-generation-assembly; no new feature branch.

## Changes
Shared research/media_archive/_inventory.py holds existing scan and association logic; preflight.scan fixes profile=legacy and generation_inventory.scan fixes profile=generation. Only generation profile performs generation/observation validation before recognizing their tables. There is no unknown-table ignore callback or caller-supplied table list.

Shared service/mcis_service/audio_review/_assembly.py holds receipt caching, base members, bounds, source consistency and v2 history construction. archive_candidate and generation_assembly retain their public build_candidate signatures and per-module load_receipt dependency, selecting only fixed respective profiles. Permission/session gates remain before inventory. The private core rejects profiles other than those two. Legacy returns original v1 structure; generation returns original v2 structure. No HTTP/product factory, runtime, permission or product whitelist change.

Historical freeze manifests remain evidence of their exact commits and are not rewritten. Their source hashes for the four refactored modules no longer describe HEAD; logs/audio-assembly-refactor-impl-hashes-frozen.txt is the new freeze. Old evidence must always be read at its recorded commit.

## New developer ordinary compatibility validation
5 explicitly reviewed new nodes passed in 1.89s. Tests load committed implementation source (not test modules) using git show at the exact parent, bind that parent's scanner, and compare complete return values including every member byte and native inventory. One fixture deliberately suppresses generation registration/observation to construct pre-generation synthetic task shape; it is not a migration or real old database test. No deletion/backfill of actual records. Remaining fixtures use generated PCM, stub recognizer, temporary SQLite and normal APIs.

Covered: new output with human revision equals parent; legacy rejects new tables; legacy-shaped output equals parent while generation rejects unknown history; unsupported recommendation remains rejected; two runs retain four observations and one cached registered-source read, exact parent output. No old test nodes/full files, paused tests, write-refusal/security/browser probes or real models executed.

Command from repo root (requires git and exact parent object locally):
```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider service/tests/test_audio_assembly_refactor_compat.py::test_generation_output_is_identical_to_parent_with_human_history service/tests/test_audio_assembly_refactor_compat.py::test_legacy_entry_still_rejects_new_tables_like_parent service/tests/test_audio_assembly_refactor_compat.py::test_legacy_shaped_task_output_matches_parent service/tests/test_audio_assembly_refactor_compat.py::test_unsupported_business_state_still_refused_by_generation_entry service/tests/test_audio_assembly_refactor_compat.py::test_generation_two_tasks_still_read_one_registered_source --tb=short
```

## Remaining limits
Independent review pending. No whole-suite, actual mixed image/audio app, browser, concurrency, actual crash or production identity verification. Existing unfinished states, log/HOME preservation, writer closure, publication and complete recovery remain blocked. Export/restore/execution remain false. This consolidation removes duplicate maintenance paths; it does not increase archive support or prove full behavioral equivalence outside the selected ordinary scenarios.
