# Case transition follow-up — developer synthetic check
Parent a268e054983479b57c3e22b8440c64aa1262c57e.
`node tests/layout-case-transition.test.cjs` (from web) executes actual Layout with
synthetic React hooks, router and deferred API promises. No HTTP or identities
are exercised. Before fix: assertion `B must not show A failure before effects`
failed (false !== null). After fix: 6 lifecycle assertions passed, including
failure-to-new-case, success-to-new-case and ignored late previous-case failure.
Load results are now bound to caseId. Existing requests/cancellation unchanged.
Old freeze file remains historical; new freeze is case-load-transition-impl-hashes-frozen.txt.

Also reran existing case-load-status SSR via the commands in DEVELOPER.md:
5 scenarios / 27 assertions passed. `npm run build` passed, 767 modules;
>1500kB bundle warning retained. No new dependencies installed.
Synthetic effect scheduling is not real React/browser or visual acceptance;
no whole-app/identity-change race coverage claimed. No models, real cases,
paused tests or write-refusal probes. Await independent review.
