# Development-only pure projection check

Base 76d6c22; independent candidate, no UI/PR104/health-policy branches merged.
Static source review used only image_review/app.py, image_review/contract.py,
image_review/tasks.py, audio_review/app.py, audio_review/tasks.py,
evidence/service.py and report source/citation code. No seed/case bodies read.
The new contract is contracts/media-report-reference-projection.md.

Executed exactly:

    python3 -I -S -B tests_acceptance/media-report-reference/check.py

Three output groups passed (audio, image, role/secondary-source cases). Fixtures
are handmade storage-shaped projections containing only fields consumed here,
not full machine-document schema validation. The exact new module alone is loaded
by stdlib runpy, avoiding reports package initialization/main/ORM/seed imports.
It imports only copy. Tests perform no network, media reads, database, requests,
model, permission/refusal probes, fault injection or paused test collection.

Covered: exact older revision with a newer row present; no human row; missing,
invalid and contradictory revision; cross-case same evidence ID; wrong run or
selected evidence; duplicate revisions; changed/unknown current digest; malformed
required saved fields; both PDF/image hashes; explicit image role; audio saved
revision digest/segment; empty unintelligible text; output detachment/input
preservation. No test counts from other versions are added.

No app call site, route, persistence/schema change or report display is enabled.
Pure structural checks do not authenticate input objects. A trusted authorized
storage adapter and source/task verification remain required. Actual generation,
DB/HTTP, report export/reopen, archived restoration, browser and production
identity have not been validated. Startup/archive holds remain; independent
review pending, no merge/deployment.
