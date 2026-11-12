# W5 case-context independent acceptance

Date: 2026-11-12 UTC. Implementer and independent reviewer were separate sessions. Baseline: main `0a29f28eeabae8087978de000caf47e5fe2aff30`; implementation materialized with content-SHA checks by coordinator. Reviewer did not change implementation. The 9 files in `logs/w5-context-impl-hashes-frozen.txt` matched at final verification (`logs/w5-context-independent-freeze.log`); implementation code also matched at initial inspection. The implementer separately corrected the test-only conftest import and refreshed the freeze before acceptance completed.

## Result

**Targeted case-context isolation slice passes. No new in-scope defect found.**

- Real TCP HTTP independent tests: **10 passed**, 0 failed, 0 skipped. `logs/w5-context-independent-http.log`.
- Chromium against the real Vite frontend and real service: **19 scenario groups passed**, 0 failed; no browser uncaught page errors. `logs/w5-context-independent-browser.log` and `tests_acceptance/W5_CONTEXT/artifacts/results.json`.
- Screenshot inspection: `new-case-empty.png` and `active-case-loaded.png` at 1440×1000 inspected visually. Current case is clear, empty case shows no invented interview, non-fictional labels do not assert public-report provenance, controls are readable within the page. Screenshots contain synthetic test material only.

## Coverage and findings

1. Create a non-fictional case in the real lobby form, enter its evidence center, click sidebar Interview, and observe the same case ID and an explicit empty roster. No Lily/Mary/public-report/fictional-person assertions and no action form. Verified the corresponding empty roster through HTTP.
2. Direct legacy `/interview` still chooses the demo's IR-03. A non-demo case with IR-01/02/03 chooses its first actual record instead. Sidebar evidence/interview navigation retains the active case.
3. Four real UI actions (confirm, reject, revise, recheck) send one POST each to the active case/record/statement and produce the expected persisted state. Independently seeded peer cases use identical record and statement identifiers and remain byte-for-byte unchanged. HTTP checks separately cover all four action types and unchanged peer audit length.
4. Delayed record response: previous transcript/action form disappears while loading; switching onward does not display the late record; same-named statement form values reset.
5. Delayed case roster and delayed detail, tested separately: switching to another case excludes old data; Back and Forward resolve to the correct case again.
6. Delayed protected detail after switching to Public never reappears. Same-role operator changes reset the active form. Real ExternalExpert data is redacted, and write attempts are denied by the server without changing the document.
7. Double synchronous `.click()` while a mutation is pending emits only one request. Late success and late error after navigating to another case do not issue old-context toasts or disable the new case. Successful old-case write is correctly retained in its original case; no claim is made that unmount cancels an already-sent write.
8. Wrong-case roster, wrong-case detail, wrong top-level record ID and wrong nested record ID responses are rejected with visible errors, no transcript/action form. Missing real case shows an error rather than falling back to demo.
9. Real statement identifier `S &?#汉字` is correctly URL-encoded and confirmed via the service. Current schema restricts case IDs to `[A-Za-z0-9._-]+` and record IDs to `IR-[0-9]{2,}`, so invalid punctuation in these IDs is not represented as a successful end-to-end service scenario; source review verifies their explicit encoding.
10. Provenance review: W5 service labels only the dedicated fictional demo as Lily/Mary. Other fictional cases get a generic fictional disclaimer; non-fictional cases are not inferred to be public reports. No response field or contract changed.

## Review reasoning

Keyed component boundaries cover case + role/operator and record. Their unmounts invalidate `useLoad` request continuations and clear record/row/form state. Separate current-response ID guards prevent mismatched response bodies from being rendered. Mutation paths close over the scoped record path, encode identifiers, synchronously acquire the pending ref before starting the POST, and suppress completion effects after unmount. Empty rosters never request a detail or expose an action.

## Limits (not newly closed)

This is not full W5 acceptance or production security certification. Existing role headers are not production authentication. No new interview creation/import UI, real LLM, Unity behavior, or shared app settings were implemented/tested here. W5 date/chart formatting remains its existing UTC+8 convention, as explicitly scoped in REQUESTS; this does not certify arbitrary-case timezone display. Responsive/mobile redesign and exhaustive visual regression were not performed. The HTTP tests use temporary synthetic data; no actual protected user testimony was accessed. The four mutation/role scenarios exercise existing contracts, not every legacy state transition. Full repository regression is owned by the implementation coordinator and is not claimed by this independent report. No deployment, commit, or merge was performed by the reviewer.
