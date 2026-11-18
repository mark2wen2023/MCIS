# Progress reload-to-render window

Base: 71889d21990b015354ae97b687537a59ad5c7014 (product ancestor 7702e62).
Developer synthetic verification only; pending independent review.

## Reproduction and fix

Actual parent refresh and Detail callbacks were bundled with esbuild; synthetic hook stores
and a counted loader.reload stub deliberately leave parent/Detail unrendered after refresh.
Before fix, save dispatched once (expected zero); adoption changed draft35 to50 (expected35).
This demonstrates callback logic, not React scheduling, a real loader/HTTP response or browser.
Initial command was mistakenly run from repo root and failed MODULE_NOT_FOUND; corrected to web.

Parent refresh now increments a ref epoch before board/audit reload. Detail progress save/adopt
checks its captured epoch synchronously, alongside existing source/readiness/identity/lock checks.
No shared hook or backend changes. No cancellation of submitted requests or automatic retry.
Draft contents and unknown lock remain; valid post-read adoption/save still work.

## Exact allowed commands (web directory)

- `node tests/recommendation-reload-action-window.test.cjs`: 3 scenarios (save/adopt/unknown).
- `node tests/recommendation-progress-snapshot.test.cjs`: 5 scenarios.
- `node tests/recommendation-progress-flight.test.cjs`: 7 scenarios.
- `npm run build`: TypeScript/Vite passed; existing >1500kB chunk warning.

These are separate bounded suites, not total/full coverage. Existing dependencies reused;
no fresh install, HTTP, backend, production identity, real browser or visual acceptance.
No paused, refusal/security, model, HFACS or real-data tests run. No case/seed read.
Unknown lock is not released by refresh; it still requires manual result checking.
A→B→A server changes remain unverified; this is not server revision/CAS protection.
The synthetic stores do not prove concurrent React rendering behavior or all context transitions.
No merge/deployment. No dependency installation.
