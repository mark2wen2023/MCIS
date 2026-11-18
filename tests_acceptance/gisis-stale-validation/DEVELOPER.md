# GISIS result invalidation after edits
Base main 94d5e38c926fda232bb987b60fa9145e4bcf01a7. GisisPanel stores field edits locally, while ReportPage retains the previous validation prop. Before change, synthetic editing reproduced both stale pass and stale error details. Both assertions were observed failing before implementation.

Change: on text/select edit, mark the current validation object stale; retain input, suppress that result and display a revalidate notice. New validation object can display normally. Uses existing parent result lifecycle: API JSON parsing yields a new object. This is not server-side version/request binding. Same object reused remains conservatively stale. No automatic request, changes to payload, server rules/export, permissions, or consultation reload protection.

Developer commands from web (existing dependencies):
- `node tests/gisis-stale-validation.test.cjs`: 4 synthetic flows / 40 assertions passed. Text/select × previous pass/fail; edit retention, fresh submitted value, busy disabled control and fresh result. Evaluates actual private GisisPanel, exported only in the in-memory test bundle, with synthetic hooks/props. No production export added.
- `npm run build`: passed with existing large chunk warning.

Not real React DOM/browser/visual/accessibility, HTTP, independent or full CI verification. No real data, model, paused/refusal tests or service. Full parent async ordering, edits before busy renders, global export-success notices and backend version binding are outside this slice; do not infer these are fixed. No guarantee across refresh; local edits remain ephemeral.

Independent main-based branch, not integrated with PR104 or 0a6d0bd (same ReportView.tsx file); normal integration review required. No safety/authorization changes. Source file/test hashes frozen separately.
