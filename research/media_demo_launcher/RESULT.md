# Isolated media demo launcher — developer evidence

Parent27a16445b43c5a2b374d7886f8c41f61ffb7b50a. New tools/media_review_demo/launch.py
accepts explicit root plus complete preparation manifest. Bounded duplicate-key-free
manifest checks status, exact declared scope, directory/database, source digests and
known origin variants. Root must match resolved mcis-media-demo-* directory; existing
demo.db only. SQLite mode=ro transaction checks sole synthetic case, initial image/audio
run associations, receipt mapping and registered source version metadata. No originals
read by preflight. This is NOT cryptographic proof the preparer authored the manifest,
file byte verification, OS isolation, concurrent path protection or production identity.
Use only operator-owned disposable preparation directories, no untrusted modifications.

Default CLI checks and prints IDs/pages only; --serve explicitly constructs the isolated
factory then calls uvicorn at127.0.0.1:8766, workers1/reloadFalse. No configurable host,
role headers, model enablement, automatic retry or default database fallback. Seed false,
explicit DB/data path. Fixed core command/timeout avoids ambient core command selection;
no core is executed here. App creation reuses normal initialization and may write schema
metadata: --serve is not claimed read-only. Preflight and app opening are not one atomic
operation; concurrent replacement/changes and crashes remain unverified. Model state
slots must be None. No launcher or server was started in this task.

From repo root using existing dependencies (instructions only, NOT executed):
PYTHONPATH=.:service python tools/media_review_demo/launch.py --root /absolute/mcis-media-demo-... --manifest /absolute/mcis-media-demo-.../demo-manifest.json
Add --serve only when explicit local service use is intended. Invalid/incomplete data
stops with error; never retries/cleans up or substitutes another DB. Output says existing
results only, browser authorization unverified. Pages still use existing permissions;
no injected LeadInvestigator header or bypass, no claim UI will be authorized. Task
runtime remains unconfigured503. Formal archive/restore remains unsupported.

Three new ordinary synthetic nodes read before execution. First run1failed/2passed:
test enumerated FastAPI _IncludedRouter.path directly. Adjusted getattr in test only;
final3passed in1.45s. command.txt lists exact nodes. Tests use prepare's synthetic
schematic/tone/fabricated drafts with in-process TestClient, plus app construction,
not listening HTTP servers, browsers, models, real samples or production DB. Incomplete
manifest test is a normal preparation-state fixture; no write-refusal/security probes.
No paused tests or broad suites. No independent acceptance, actual socket/server start,
client authorization, playback, UI rendering, concurrency/crash or deployment tested.
