# W20.2 implementation-side rendered verification

2026-11-12. Source frozen separately in w20ui-impl-hashes-frozen.txt. This is implementation-side evidence, not independent acceptance.

Flow: current case InterviewPage -> explicit people_ops extraction -> source-linked PendingReview -> individual semantic review checkbox -> explicit confirm or reject -> server state and existing W5 statement grid refresh.

CUA cloud tab failed to reach execution localhost (`ERR_CONNECTION_REFUSED`). Engineering fallback was explicitly coordinated with the parent task. Used already installed Playwright and headless Chromium, with FastAPI, Vite and a controlled OpenAI-compatible fake model in one execution session. All listeners 127.0.0.1; fresh synthetic cases/records only; no keys, real case documents, deployment or external requests. Browser launch needed the environment's approved unrestricted execution to open local sockets. No software installed.

The model ID was `controlled-http-fixture-not-real-LLM`. This is real browser + real HTTP protocol/service testing, **not real LLM inference or quality validation**.

## Passed checks

- Registry says configured / connection and capability unverified, not healthy.
- Generation creates a pending draft while original statements remain empty.
- Confirm is disabled until each candidate's meaning and quote is checked; explicit confirm appends one statement and refreshes the existing W5 count/grid.
- Reject needs a reason; rejection does not append statements.
- Invalid quote and model HTTP failure produce visible errors and no new draft.
- Double-click creates one outbound request; late completion after role switch does not show draft contents to ExternalExpert.
- A dropped extraction response after actual service creation causes unknown-result lock, not fake success; explicit read/reconciliation unlocks without automatic resend.
- Late completion after switching to a different case does not populate that case.
- No page runtime errors or Vite error overlay in the exercised flow.
- 1440x1000 desktop and 390x844 mobile screenshots inspected. New panel remains within viewport; candidate/quote columns stack and controls wrap. Existing W5 comparison interface is cramped at 390px; no whole-page mobile conformance claim.

Screenshots retained outside publication: draft desktop, mobile, unknown-result state. Independent acceptance owns repeatable committed browser/HTTP tests and any defect findings. Initial test harness invocation errors (Node executing esbuild binary / CJS top-level-await / browser executable selection) were setup errors corrected before successful tests; no implementation results were inferred from those failed commands.
