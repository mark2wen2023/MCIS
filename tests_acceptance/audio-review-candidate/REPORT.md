# Developer report — not independent acceptance

Base: `94d5e38c926fda232bb987b60fa9145e4bcf01a7`; branch `candidate/audio-review`. Independent from image candidate `91962113`. No shared frontend page or product runtime file changed.

Commands from complete candidate root:

```sh
PYTHONPATH=.:service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q service/tests/test_audio_review_candidate.py --tb=short
node --test tests_acceptance/audio-review-candidate/page.test.cjs
```

Final result: 13 service tests passed; 4 Node synthetic-DOM tests passed. No skips. These are separate selected suites, not full-system regression. Existing installed service environment reused; no dependency installation, download or model invocation. Initial DOM fixture incorrectly omitted immutable source metadata and failed one test; fixture corrected, submission response validation strengthened, final four passed.

Service uses actual FastAPI routes and temporary SQLite/files, generated 1-second 440Hz PCM tone (NOT speech), and explicitly labelled synthetic v2 machine fixture. Covers original byte binding/download equality, imported artifact unchanged, human history, unknown timing, unintelligible blank text, stale revision, invalid ranges, missing parent history rejection, format rejection, restart read, audit-insert failure rollback, default-app isolation and archive409/no ZIP. Failure is injected after observing row count 2, not a real process crash or uncertain SQLite commit.

Node tests execute the actual page script with fake DOM/fetch: unknown timing refuses seek; switched case refuses old editor save; long text survives412 without retry; one saved segment retains other draft; unrelated response cannot show success. This is NOT Chromium, audio playback, browser refresh/leave handling or end-to-end browser acceptance.

No prior restricted security, ECFC or browser test was invoked. No production permission change. No real ASR, original speech, transcription accuracy, real identity, multi-process load, full repository regression or archival restore verified. Source byte digest equality does not establish authenticity or human listening. Draft history is append-only at this API/table level, not cryptographic tamper proof. Only page-memory drafts. Explicit standalone candidate factory only; default product not enabled. No push/merge/deploy in this turn.
