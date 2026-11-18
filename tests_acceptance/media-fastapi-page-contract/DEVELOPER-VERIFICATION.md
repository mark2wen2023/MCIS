# Actual ASGI API and page JavaScript contract (developer)

Runtime head: ac4254ef39165eb79da74a428676efb004ae81f5. This delivery adds tests/evidence only, no product change.

Two individually statically reviewed ordinary nodes and their complete helper chain: default synthetic prepare, explicit manifest/root, disabled media factory, page JavaScript in Node VM with DOM doubles, requests relayed unchanged over local pipes to actual FastAPI TestClient. Responses are actual API/temporary SQLite results, not mocked successful payloads. No role header or dependency override. Preparation operator is a synthetic label, not trusted identity. No sockets/listening server, browser, models, real media, permission-denial or paused/write-refusal tests.

Each node: fresh generated PDF/PNG/tone/fabricated drafts -> prepared manifest -> actual served HTML -> read existing run -> create a different run -> two pending synthetic corrections with immediate reread -> application reconstruction and exact stored document comparison -> audit-chain and two edit-event checks. Original machine draft remains unchanged; audio time remains null and factVerified=false. Six page API requests per node, all 200/201. No OCR/ASR/human listening claimed. Media/database files stay in pytest temporary directories, never Git.

Command from repository root:
```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:service "$MCIS_DEMO_PY" -m pytest -q -p no:cacheprovider  tests_acceptance/media-fastapi-page-contract/test_contract.py::test_image_prepare_create_edit_twice_and_reopen  tests_acceptance/media-fastapi-page-contract/test_contract.py::test_audio_prepare_create_edit_twice_and_reopen --tb=short
```
Existing approved interpreter used: /workspace/mcis-pr104-supported-archive/service/.venv/bin/python. Python 3.12.14; FastAPI 0.162.7, httpx 0.28.1, SQLAlchemy 2.1.8. Default system Python lacked SQLAlchemy; no installation performed. Result: **2 passed, 1 warning in 3.36s**. Warning: existing Starlette httpx deprecation; no dependency changes.

Not independent acceptance; not real TCP or browser end-to-end, rendering/playback, delayed network races, production authentication, process-crash recovery, complete file-byte verification, archive/restore or full suite. No confirmed product defect was found, so runtime code unchanged. Follow-up static concerns (cached summaries, late error presentation, task result invalidation, malformed nested responses) are not covered by these two normal-path tests.
