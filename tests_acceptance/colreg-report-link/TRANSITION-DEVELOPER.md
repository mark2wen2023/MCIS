# Manual version transition and active alias — developer follow-up
Parent c269e70272193d38d28f3e43831cf69b482c87f9. Static independent feedback
was reproduced with actual ColregPage and actual useLoad bundled together, using
synthetic hooks/effect scheduling/router and deferred API results, no HTTP.
Parent failed: `waiting B must not judge stale A as mismatched B`.

Manual version selection now updates case/run query and clears check by explicit
selection, triggering the existing keyed session boundary instead of retaining
old useLoad data/error. Pending B has no A view or false mismatch message.
run=active is normalized to current selection; router.py:get_colreg_run explicitly
documents active as an alias, not the stored runId. Notice states current semantics.
No backend/permission changes. Existing evaluate/activate callbacks unchanged;
their asynchronous lifecycle and other manual interactions are not covered here.

From web:
node tests/colreg-version-transition.test.cjs  # 5 lifecycle assertions passed
node tests/colreg-report-link.test.cjs        # 9 evaluations /12 assertions passed
npm run build                               # passed766modules, large chunk warning
One intermediate harness assertion expected null instead of undefined for absent
view; changed to assert no view, without relaxing the stale-content requirement.
No dependencies installed; approved environment reused. No browser/visual or
independent acceptance, actual React scheduling, historical-integrity claim,
model/core, paused nodes, refusal probes or real data. Old freeze kept as history;
new hashes are colreg-version-transition-impl-hashes-frozen.txt.
