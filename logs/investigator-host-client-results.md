# Runnable host client final validation

Base fd9152b42151f98cc7a692451380aee7ccb8ca32; native implementation/reviewer.
New primary3, independent20. Final affected suite400/400 zero skips104.03s;
MCIS_PREFLIGHT_REAL_CORE=/tmp/mcis-preflight-core.sh enables four actual W2 paths
(new executable client plus prior catalog roundtrip/HTTP save/internal save).
Independent+primary23/23 zero skips13.37s overlaps; earlier380 superseded.

Independent actual failure: closing while a completed select response was delayed
allowed phase resurrection. Added closed flag, set before awaited shutdown, post-await
checks and guarded exception state updates; pending select/save/read closing tests
pass, already committed server result not falsely rolled back. Product hashes frozen
in independent report. No product edits after these final runs.

Service expectedSelection check compares selected case/source/parent versions inside
initial authenticated transaction before compute/replay/write. DTO wrong types422,
object mismatch409. Existing unpinned callers remain compatible; client always pins.
No permissions from preconditions. Client class uses real isolated ASGI transport;
no network URL/config, token output, legacy mount, browser storage or frontend login.

Reproduce prefix PYTHONPATH=service python -m pytest -q, all prior catalog/read/
authority/storage/protected-route regressions plus test_investigator_client.py and
 test_investigator_client_independent.py. Fixture setup/provisioning remains trusted
host + legacy setup, not full authenticated intake/workbench/IdP/browser/LLM.
No deployment/merge/full-system/production-capacity claim.
