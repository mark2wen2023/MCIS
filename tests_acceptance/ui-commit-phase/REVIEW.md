# Commit-phase refs candidate — not real React/browser acceptance

Base integration/ui-review-series 49fc5b06ebedd2229b028c12f810180c8aef4649 (product combination 661d73f). Three product files only; no backend/permissions/routes or network behavior changes.

ReportPage derives initialSelection without modifying the selection ref. A layout effect publishes the active context and clears a mismatched selection only after commit; cleanup invalidates its active key. Event-stage refresh still records selection and increments revision. Before an initial commit the active key is null; discarded renders cannot reset the previously committed selection or publish another active key. Identity getter checks remain. Before another context commits, the previously committed UI remains the active one; this is not cancellation of an already dispatched request.

Recommendations Detail publishes latestProgress in a layout effect rather than render. Existing boardActionEpoch synchronous invalidation on refresh and readCurrent/session gates remain unchanged, as do drafts and unknown locks. useBoardLoad no longer writes a loader ref during render: its committed effect captures loader directly; loader-only render changes do not trigger new requests, retaining reload/tick semantics. No new A→B→A generation solution or server concurrency/version guarantee.

## Development validation

Reviewed check.cjs: esbuild reads only these frontend sources, vm require allowlists provide synthetic APIs/hooks/JSX, no real network/API/data. New test calls actual parent ReportPage and extracted actual Detail function plus actual useLoad with hand-built commit/discard hooks; it is not React reconciliation or real concurrent rendering. Covers report initial/committed activity, retained selection across abandoned context, committed switch/old callback and identity/unmount invalidation; Detail committed source vs discarded next source, draft preservation and readCurrent invalidation; abandoned loader not used by later committed reload. No backend or permission/refusal tests. First test attempt failed because the synthetic format module omitted toLocal; fixture corrected before PASS, not a product failure.

Commands actually run:
- From repository root: node tests_acceptance/ui-commit-phase/check.cjs — PASS, three bounded synthetic groups.
- From web: node tests/recommendation-read-lifecycle.test.cjs — PASS, existing six ordinary synthetic lifecycle cases (success/error/retained/initial-error/identity/unmount).
- From web: ./node_modules/.bin/tsc -b --force — PASS.
- From web: ./node_modules/.bin/vite build — PASS, existing >1500 kB chunk warning (JS 1869.90 kB).

Existing node_modules copied from the UI candidate worktree; no installation, browser, service, model or app startup. No real cases/seeds or media opened. No full suite, paused tests or write-rejection probes. Older synthetic tests that model layout effects as mount-only are not proof for this change and were not silently counted as rerun. No full report save/reload chain or unknown-lock sequence newly verified by this test; preservation there is static and requires follow-up review.

## Remaining limits

No actual React concurrent interruption/aborted work, StrictMode scheduling, child-layout-effect ordering, event replay, browser/visual/accessibility, HTTP/backend or multi-user acceptance. No claim that all render/ref or state risks are solved; ReportPage still reads refs to derive initial selection and existing Detail render-phase conditional setState is unchanged. Server progress versions and ABA protection remain unresolved. Startup/archive holds and seed risks remain; these frontend tests do not lift them. The old integration handoff describes its pinned old product head; this separate candidate has not been merged into it. Independent review pending. Do not merge or deploy.
