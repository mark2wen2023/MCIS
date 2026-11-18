# Two-fragment playback serialization — developer synthetic regression

Product base: 25fc8e78b4d877bd060cfa889a9c66a15632ca50, candidate/media-demo-launcher.
This commit changes tests/documentation only. No product fix was needed for this bounded scenario.

Static review: page script is read from audio_review/review.html into node:vm; only Node built-ins
are imported. DOM and player are doubles. Each play call returns a separately controlled Promise.
fetch throws and its call count must remain zero. No audio bytes, Python application imports,
requests, server, model, browser, seed data or new dependencies. No paused/refusal tests selected.

Exact command from repo root:
```
node --test tests_acceptance/audio-playback-serialization/page.test.cjs
```
First execution: 2 passed, 0 failed/skipped. Separate cases for A success and A ordinary failure.
A uses 100–400ms, B uses 600–900ms. Checks:
- A starts once; while pending, B click does not dispatch or change currentTime/stopAt/message.
- After settling A and an additional event-loop turn, there is still one call: no queued B replay.
- Busy releases; explicit new B click creates exactly the second call with B's time range.
- A outcome and subsequent B success show their corresponding messages; both current DOM drafts
  remain intact and fetch count is zero.

This tests actual inline callback logic against synthetic DOM/media behavior, not browser media
scheduling, decoding, listening, audible stopping, native controls or accessibility. Busy silently
ignores the early B click; this existing interaction is recorded, not redesigned. The failure case
retains the existing general error behavior; clearing earlier general messages on later success
is not asserted. No whole-suite/build rerun; standalone test-only addition. No independent review
claimed, no counts added to earlier suites. Application startup/archive tests remain paused.
No merge or deployment.
