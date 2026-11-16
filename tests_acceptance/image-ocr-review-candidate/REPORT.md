# Image OCR review candidate — developer checks only

Base main read from GitHub during work: 94d5e38c926fda232bb987b60fa9145e4bcf01a7.
Independent local worktree /workspace/mcis-image-ocr-review, branch candidate/image-ocr-review.
Default app, production routes, permissions, schemas, archive whitelist and PR104 unchanged.
No PR69/97 EvidencePage/intake files touched. Shared REQUESTS/ROADMAP appendices need
preservation during eventual integration; not a combined PR69/97 runtime acceptance.
Current thread-tree query showed only this running line; cannot establish other independent
threads' activity. No extra agents spawned. No push/merge/deployment.

## Actual implementation
Explicit candidate app mounts new real SQLite-backed routes and a standalone HTML page.
Four already registered W4.2 blobs (PDF, page image, raw OCR JSON, normalized candidate)
are linked by case and immutable receipt digest; actual loaded byte hashes must match.
Source bytes are not written or overwritten by this module. Existing authorization/download
path reused. Text line originals, page/box/model metadata and all manual corrections retained.
Append-only records and existing audit commit together; revision CAS rejects stale updates.
User can list saved run IDs, read after restarting app, download registered source files,
review/correct each line, and reopen complete revision history. There is no automatic retry,
fact confirmation, localStorage, automatic OCR or remote model. Page only requests same origin.

PDF page and render linkage remain explicitly operator-declared, not checked against PDF
page count or image dimensions; no inline PDF/image viewing or PDF jump is implemented.
Raw OCR bytes are bound, but no automatic proof normalized lines came from that recognizer.
The factory does not mount into the default app. Use only temporary cases: new records cause
existing closed-world package export to reject; no backup/restore support is added.
No production identity/authentication claim. No prior security/ECFC test suites run.

## Exact developer command
From this worktree:
```
MCIS_PUBLIC_OCR_FIXTURE=/workspace/mcis-paddleocr-handoff PYTHONPATH=service \
/workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q \
service/tests/test_image_review_candidate.py -rs
```
Existing Python dependencies reused, no install. Final result recorded below.
Tests use FastAPI TestClient (in-process HTTP), real SQLite and temporary blob directories.
One opt-in test uses actual existing public artifacts, imports OCR output, simulates a reviewer,
checks source downloads byte-for-byte, then reopens the app/DB. It does NOT rerun PaddleOCR,
independently verify recognition quality, or exercise a browser/real production identity.
The other tests are constructed fixtures, including opaque synthetic file bytes; these are
not valid-PDF/image decoder tests. New parser rejects unsupported table review, invalid
line/bounds/flags, supports blank lines; workflow covers two editors, stale refusal, explicit
post-insert fault marker+rollback, original retention, audit count, archive409 and default-app
absence. Import input version mismatch is a fresh ordinary validation test, not a previously
restricted historical-integrity/security test selection.

Initial run:10 pass/1 fail because a test assumed every FastAPI route exposes .path;
changed that assertion to a real default-app GET404 and table absence. Second11 pass.
Expanded final selection: `15 passed in 3.23s` (no skips/deselections with public fixture configured); do not add overlapping counts.
JS syntax: extract the page's inline script into /tmp/mcis-image-review-script.js,
then `node --check /tmp/mcis-image-review-script.js` (passed). Static HTML caveat assertions
are included; neither syntax nor TestClient page delivery is real browser acceptance.

## Public artifact provenance — nothing copied into Git
Official landing URL: https://www.sh.msa.gov.cn/sgdc/104170.jhtml
Historical PDF URL: https://www.sh.msa.gov.cn/dbfile.svl?n=/u/cms/www/202505/191445221747637122775.pdf
Local existing PDF SHA256:
99084b8e672da6e2f8d9809bea25a92fe5fcf31c318554832e14339610015d7f
PDF physical page6 / printed page4, from existing explicit manifest. Local page PNG,
raw/ocr-page-6.json and candidates/ocr-page-6.candidate.json were reused, not uploaded.
Historical recognizer metadata: PaddlePaddle3.2.0/PaddleOCR3.3.2/PaddleX3.3.13,
PP-OCRv5 mobile detector/recognizer CPU. This round imported those outputs only.
Test acquisition timestamp is an explicit synthetic fixture declaration, not a historical
PDF extraction/accident timestamp. No private records, credentials, DBs, PDFs or images in commit.

## Launch only in an isolated temporary workspace
Existing environment only, no dependencies installed:
```
PYTHONPATH=service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python - <<'PY'
from pathlib import Path
import uvicorn
from mcis_service.config import Settings
from mcis_service.image_review.app import create_image_review_app
root = Path('/tmp/mcis-image-review-manual-lab')
settings = Settings(data_dir=root, db_url=f'sqlite:///{root}/lab.db', seed_demo=False)
uvicorn.run(create_image_review_app(settings), host='127.0.0.1', port=8766)
PY
```
Open /image-review-lab. Use the existing API/workbench to create a disposable case and
register four files with honest acquisition metadata; use their receipt digests in the lab.
The launch/browser workflow above is documented, NOT claimed as executed this round.

## Remaining
Real browser behavior/layout, existing workbench identity/case-switch integration, independent
permissions/concurrency acceptance, TCP service tests, full suite/CI, production SSO,
archive/restore, crash/unknown-commit resolution and original authenticity remain unverified.
SQLite tests inject an exception, not OS crash. A lost import response requires list/read
and human checking; no idempotent automatic retry. Existing intake/file implementation
and its previously recorded limitations are not repaired or revalidated here.
Per-case20-run / per-run1000-revision budgets are candidate bounds, not measured performance.
Current reads hold existing writer transaction while loading sources; no low-memory/low-lock
performance claim. Browser may suppress unload warnings; drafts remain in page memory.
