# Explicit public-page local OCR task candidate

Parent:2ba9bf36e14ebd2e36fa81a3d9fd212c76b7b42b. Same isolated branch; default app,
existing evidence policies, original bytes, PR69/97/104 and archive whitelist unchanged.
No new software installation, external OCR, model download or restricted/browser test retry.

## Actual implementation
Optional host-only LocalRuntime configuration mounts task routes in the existing isolated
factory. UI explicit consent + task ID -> POST -> actual fixed Python worker -> raw result
and metadata -> ppocr adapter -> atomic task success + new review Record. Existing renderer,
PNG view and manual edits consume that Record. Task raw/candidate downloads recheck source
access and record audit; original PDF/image use existing intake download. No automatic fact
confirmation or silent overwrite. Missing runtime503; duplicate ID409; bounded task count.
Only pinned authorized public PDF6/page PNG accepted. No client executable/path/model input.

Task start/audit persist before worker dispatch; job directories never overwritten or deleted.
GET status does not expose artifact bodies and refresh is not cancellation. Running and
interrupted-unknown tasks block further execution. On worker/adapter failure BEFORE final
commit, status failed; final authorization/commit failure stays unknown rather than asserting
safe retry. Timeout waits/kills/reaps direct subprocess via subprocess.run, but this is NOT
proof all descendants terminated. No arbitrary process kill or server sandbox change.
Crash/startup recovery/unknown commit resolution deliberately not implemented; operator must
inspect retained state. Existing self-reported role headers remain non-production identity.

## Developer runs (not independent / not browser)
Initial task selection:6 passed in27.31s, one actual public CPU run plus5 simulated task tests.
After final runtime source/limit checks:
```
MCIS_RUN_REAL_PUBLIC_OCR=1 MCIS_PUBLIC_OCR_FIXTURE=/workspace/mcis-paddleocr-handoff \
 PYTHONPATH=service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python \
 -m pytest -q service/tests/test_image_ocr_tasks.py service/tests/test_image_review_candidate.py \
 service/tests/test_image_review_ppocr.py -s -rs
```
25 passed in30.37s, no skips. Explicit opt-in real local OCR test; no fake OCR in that case.
Other task tests replace execute with constructed output/errors (clearly simulated).
After adding explicit task-case archive409/no-ZIP assertion, selected simulated success
workflow rerun passed1; overlaps the25, do not add. Runtime unchanged by that test addition.

Final real task: PaddlePaddle3.2.0/PaddleOCR3.3.2/PaddleX3.3.13, PP-OCRv5 mobile det/rec,
CPU4 threads, CUDAfalse, MKLDNNfalse. Init11.2481s / prediction12.8818s;44 lines.
Raw SHA256:42eb9d75f10fa980bd598f7a3789fc8d65bbff6afa89be951d12aedce3825435.
Raw embeds job-specific input_path, so byte hash differs from earlier command-line run even
without a recognition-quality change. No aggregate quality/production performance claim.
Installed runner uses local hash-checked model archives and extracted files. Library normal
hoster connectivity check warns unavailable and uses specified local models; no bypass flag
or network retry. Python audit guard during prediction is not OS egress certification.

Real test exercised POST dispatch, real child process, output conversion, GET review,
raw artifact download/hash and simulated manual revision through TestClient+temporary SQLite.
It did NOT click the UI or use a real browser. Source is same existing public PDF6/printed4
manifest and PNG hash e097321c40047e305beb50f2676370f89a452ba49a11dc962ec4add9b6a70aff.
No new PDF render/page mapping certification. Page relation remains declared.

Simulated tests cover persistence/restart, duplicate no dispatch, worker failure no retry,
post-insert finalization fault with explicit reached marker and rollback, timeout unknown
blocking another task, missing runtime no task write, review history and archive refusal.
They are not real crash/unknown SQLite commit/permission revocation tests. Restricted previous
security/ECFC suites were not selected.

Frontend: `node --test service/tests/js/image-review-preview.test.cjs`:10 passed (synthetic
canvas tests, unchanged scope); extracted inline script `node --check` passed. UI task controls
are wired but full interactive behavior remains unverified. Browser remains paused.

## Enable ONLY in a disposable local candidate app
```
from pathlib import Path
from mcis_service.image_review.tasks import LocalRuntime
runtime=LocalRuntime(Path('/workspace/mcis-paddleocr-trial/venv/bin/python'),
                     Path('/workspace/mcis-paddleocr-trial/models'),
                     Path('/workspace/mcis-paddleocr-trial/cache'))
app=create_image_review_app(disposable_settings, ocr_runtime=runtime)
```
Bind server only127.0.0.1. Register public PDF+PNG via existing intake; enter digests in the
candidate page, generate task ID, explicitly confirm, start; query by ID if result unknown.
Success exposes runId; click Read for line review, do not classify content as confirmed facts.
This launch/browser walkthrough is not claimed executed. Exact actual service route test
command above is reproducible only where official installed dependencies/public fixture exist.

## Remaining / delivery
No production switch, merge or deployment. Archive recovery, general images, PDF navigation,
identity authentication, cancellation/recovery, cross-process concurrency, independent review
and browser interaction remain pending. Unknown task currently blocks new jobs conservatively;
no automatic repair/cleanup. Failed attempt files stay on disk; no cross-filesystem atomicity.
Only code/contracts/tests and sanitized evidence committed; no PDF/image/model/DB/raw OCR.

Final small follow-up added same-case task-ID/status listing (no artifact content) and a UI
button for refresh recovery. The five simulated task tests were rerun after this addition:
5 passed,1 real test deselected. This overlaps previous runs; no claim of a second final
real OCR run after the listing-only addition. Inline JS syntax rechecked successfully.
