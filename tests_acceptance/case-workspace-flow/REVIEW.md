# Case workspace flow — P0 candidate

Base: integration/ui-review-series 749eaff1af3f0cf1ddc12c0f84ff6ca2c916b451.
Candidate: candidate/case-workspace-flow. No media/backend branch merged.

Layout adds a small semantic nav above its unchanged Outlet. Stages: 接报(case),
取证(evidence, also current ships/env/track), 询问(interview), 分析(colreg, also
analysis/whatif/hf/systemic), 报告(report), 建议(recs), 沉淀(future only).
Primary targets are existing sidebar routes supporting case context; no API or
form changes. sim/ecfc have no declared case binding and are not linked. No
knowledge link receives a case ID. The next stage is advisory; earlier links
remain usable, with no prerequisite/completion gating or automatic writes.

New flow uses only the current location's single explicit, nonblank case query.
It does not use CASE_ID, loaded case metadata, prior identity or stored navigation
history. Repeated/empty case values and global/unsupported pages show only a lobby
prompt. No case name is shown because the existing Layout metadata request is not
identity-scoped; reusing that data here would imply trust not established by this
slice. Same URL under another identity displays that URL's case ID only, not cached
case data. No new visible resource is added beyond existing navigation; all
resource access still depends on existing page/server checks. Not an authorization
boundary or confirmation that the URL case exists. Existing Layout metadata/header
behavior is unchanged; this candidate does not fix all older context assumptions.

Use: on an existing supported page with ?case=<explicit encoded synthetic ID>,
read the current stage and choose a phase or optional next link. Switching phase
carries only case, never old report/run/record query parameters. Without an explicit
case select via the lobby. Links are normal Router links with aria-current="step";
visible focus outline, wrapping stages and breakable IDs are supplied by a separate
stylesheet. No fixed overlay or forced navigation. Completion always says 未评估.

Developer validation, existing dependencies reused, no install:

- From web: node tests/run-case-workspace-flow.cjs — passed actual React static
  rendering of the production component in MemoryRouter plus pure mapping checks.
  13 supported page mappings; global/unsupported and missing/duplicate case inputs;
  synthetic special-character ID encoding; back/next links; target case replacing
  prior case; no false completion; no knowledge routing. fetch throws if attempted.
- ./node_modules/.bin/tsc -b --force — passed.
- ./node_modules/.bin/vite build — passed; existing >1500 kB chunk warning remains.

The first test-file creation command had the wrong directory prefix and wrote no
files; corrected before execution. No product regression tests or backend were
started by that error. Tests load only the component/model/routes/caseContext and
React SSR; no application root, API module, seed, case material or model imported.
CSS is omitted from SSR and checked statically, not rendered visually. Not actual
browser navigation, keyboard/assistive-tech, responsive layout or React lifecycle
acceptance. No full UI suite, backend, real identity/permissions, paused tests,
refusal probes, true case data or models executed. Existing startup/archive pause
remains. No new PR, merge or deployment. Independent review pending.
