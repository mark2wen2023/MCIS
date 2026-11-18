# Save feedback accessibility — developer structural check
Parent: 33bf1ccbfb3857657f6f8d6f54837ff036ff9f1e (toast lifetime candidate,
not merged main; does not include case-status branch 9d90fdc).
EvidencePage and RecommendationsPage use useToast for operation results. Previously
ToastProvider emitted only a conditional generic div: no status/alert live-region
semantics. This is a source/structure finding, not a measured screen-reader failure.

Added persistent empty role=status and role=alert regions. Success/error goes only
into its corresponding region; aria-atomic preserves the whole message. Empty
regions have no toast styling; no tabindex/focus change, message/timeout/API change.
No claim of universal assistive-technology support or visual acceptance.

From web, after individually reviewing synthetic test source:
- node tests/toast-accessibility.test.cjs: parent failed `live regions must exist
  before any operation` (0 !== 2); fixed code passed initial/success/error/expiry
  structure checks. Executes actual component with synthetic hooks/JSX/clock.
- node tests/toast-lifetime.test.cjs: existing 5 synthetic scenarios passed.
- npm run build: TypeScript/Vite passed, 766 modules; >1500kB chunk warning retained.
Existing approved dependencies reused, no installation. No service/browser,
network API, model, real data, paused nodes or write-refusal probes executed.
Real browser, screen-reader announcement/timing, focus interaction and visual QA
remain pending; timer cleanup after unmount not covered. No independent acceptance.
