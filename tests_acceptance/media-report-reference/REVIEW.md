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

## Exact-reader increment (base 3fd311265fc080d6428022f11901e9b6072f846c)

Executed only `python3 -I -S -B tests_acceptance/media-report-reference/check_reader.py`
after reviewing the new script. Two groups passed, one per media type. It loads
the new pure reader AST with its one local pure import resolved explicitly to the
projector, never importing the reports package. Query expressions, Session,
scalars/all, ORM row fields and no_autoflush context are handmade test doubles;
SQLAlchemy and actual sessions are not imported. Fixture helper alone is extracted
from the previous synthetic script; that prior test suite is not rerun.

Assertions cover three equality predicates, queries only for zero/exact human
revision, source-ID-only reads, old exact version despite a newer/other-case row,
missing version without latest or source reads, cross-case before querying, wrong
returned row identity, stable digest despite dict order, changed body under the
same identifiers yielding a different digest, rejection of old expected digest,
missing digest-bound content, unchanged input rows and absence of available write
methods in the fake session. These establish simulated call shape and pure
semantics only. They do not prove real query execution, absence of custom ORM
hooks, transaction isolation, actual authorization, real database read-only mode,
HTTP, original-source verification, or persistent report linkage.

The real rows()/records() helpers currently enumerate a run's revisions; this
adapter reuses their model/session query form with an exact revision predicate
instead. Evidence read callback remains an unwired trusted per-ID interface. No
new storage, endpoints, configuration, report display or persistence is introduced.
Startup/archive and all prior paused tests remain paused; independent review pending.
