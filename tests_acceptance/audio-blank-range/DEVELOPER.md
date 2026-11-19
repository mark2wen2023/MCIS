# Audio whitespace-only playback range

Base: 76d6c22c474172a28f7b2da9ae45021e8d573b82 from candidate/media-demo-launcher, original mark2wen2023/MCIS. Independent candidate/audio-blank-range; no other candidate or mcis-3d changes.

Confirmed defect: the text start input permits spaces. Existing Number(' ') or Number('\t') becomes zero, so an explicit playback click with that start and end=500 seeks to zero and invokes play. This is not an unknown-time interpretation and should not silently locate a segment.

Only playback now rejects whitespace-only start/end before numeric conversion. Empty pairs remain unknown, explicit numeric 0 remains usable. Playback precondition failures explain the reason beside the player, rather than retaining a prior playback status. The message says this action did not locate or initiate playback, and does not claim an earlier playback was stopped. Existing busy/generation/context guards, source download verification, time bounds and save/revision behavior are unchanged. Numeric times remain input declarations, not human verification.

Safety review: the new Node test reads only review.html, executes its inline JS in a synthetic DOM, injects a hand-built state and object URL, forbids fetch, and controls play Promise settlement. No audio bytes, real request, Python import, app, browser, model, permission/refusal probe or paused test. It does not prove media authenticity, native playback or browser event ordering.

Command from repository root:

    node --test tests_acceptance/audio-blank-range/page.test.cjs tests_acceptance/audio-playback-waiting/page.test.cjs

Old head/new test: 1 passed / 10 failed. Two whitespace cases fail on unexpected play count 1; other failures concern the newly required local explanation (not new seek defects). New head: 11 new and 8 existing waiting/context cases passed in one selected run. Cases include whitespace, unknown, partial/reversed/out-of-range times, explicit zero, unloaded/not-ready media, case/run change, and pending success/failure after case/run/clear. No retry or queue introduced; input and dirty remain.

During development a trim-based check exposed the existing DOM double's numeric value assignment (real input values are strings). Final whitespace regex accepts the double's equivalent numeric value without weakening whitespace rejection; adjacent tests unchanged and passing.

This standalone HTML change needs no React/Vite compilation; inline JS parsed/executed by Node. Real browser, actual audio/seek accuracy, download/source checks, saved source changes, HTTP/backend and independent review remain unverified this round. Startup/archive pauses remain. This fixes one confirmed issue, not the complete audio review-to-report chain.

## Shared times() follow-up (base 00a0ce7a8e69e2aa1cbe9737442dc1a7f252795e)

The first patch guarded playback only; shared times() still converted whitespace-only start to zero before a save. Pure extraction of the actual single-line times() body reproduced this: 5 whitespace groups failed the expected exception, 10 existing semantic controls passed. No Save callback or network request was invoked.

Move exactly the existing whitespace guard into times(), removing the duplicate from playback. This deliberately changes frontend pre-save input validation too, while leaving request shape, receipts and backend untouched. Two empty strings remain unknown; explicit 0, padded numeric input and valid endpoint remain accepted; partial, reversed, negative, out-of-duration and fractional ranges retain rejection. Units remain relative milliseconds, not seconds.

Selected command:

    node --test tests_acceptance/audio-blank-range/times.test.cjs tests_acceptance/audio-blank-range/page.test.cjs tests_acceptance/audio-playback-waiting/page.test.cjs

Development result: 34 selected tests passed (15 pure parser, 11 range DOM, 8 waiting DOM). Not an accumulation across historical runs or full coverage. Parser test reads only this HTML file, extracts exactly one times() definition, and executes it with handmade start/end/audio metadata in Node VM; no page initialization or Save. Existing playback tests use controlled DOM/Promise and forbid fetch. No browser, actual audio, service/model, raw materials, paused tests or backend. Actual save/HTTP and independent review remain unverified. Updated freeze: logs/audio-shared-times-frozen.txt.
