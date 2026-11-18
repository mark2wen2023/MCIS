# COLREG version navigation: retain case work (developer verification)

Base: `0b53fcee0b012ec94b4931ebedf307c67d1362d4`; main observed unchanged at `94d5e38c926fda232bb987b60fa9145e4bcf01a7`.

Confirmed with the actual page bundled into a synthetic hook/router/deferred API harness: generating a synthetic draft then selecting RUN-B cleared the draft on the base. No HTTP, model, core, private data or browser was used. An initial harness used insufficient promise flushing; after using a full event-loop turn, the base reached and failed the specific retention assertion.

The case-keyed workspace now retains draft, draftNotice and comparison state while the version/check-keyed session still resets fetched results. A visible note distinguishes retained work from the currently viewed version. Case changes reset the workspace. Refresh/navigation away still loses in-memory state. This does not verify historical evidence or make the retained draft describe the selected version.

Commands (web directory, existing dependencies):

```
node tests/colreg-retained-work.test.cjs
node tests/colreg-version-transition.test.cjs
node tests/colreg-report-link.test.cjs
npm run build
```

All passed after the change. New ordinary synthetic lifecycle coverage: draft generated, draft generation error, comparison, version switch retention, active alias retention, case reset. Existing transition 5 assertions and link 9 scenarios/12 assertions passed. Harnesses now model the nested keyed component state; old assertions retained. Build passed with existing large chunk warning. No paused/refusal/security tests were selected. No actual backend mutation was executed; API post/get results were local constructed objects.

Not independent acceptance, real React/browser/visual/assistive technology testing, production identity, full HTTP, or full CI. No new guarantee about in-flight evaluation/activation or concurrent draft requests. A retained draft can be temporarily hidden while a version is loading/unavailable, but is not cleared by switching versions.

Related Analysis candidate `010b0eaaa60c0b998950f3638479902c19f591c6` assessed read-only: missing-scenario alert hides its local case selector/source table, but provides an explicit exit-to-baseline callback; AnalysisPage clears the scenario and retains case, after which normal content/selector returns. Global Layout is not replaced. No inescapable navigation defect established; direct selector availability and real clicks remain unverified. No change to that branch.
